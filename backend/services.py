from __future__ import annotations

import json
import os
import re
from pathlib import Path
from statistics import mean
from typing import Any

from analysis.career_score import CareerScoreCalculator
from analysis.job_ranker import JobRanker
from analysis.market_analysis import MarketAnalyzer
from analysis.skill_gap_analyzer import SkillGapAnalyzer
from automation.auto_apply import AutoApplyEngine
from backend.models import OnboardingRequest, PipelineRequest, UserProfile
from config.config_loader import AppConfig, ROOT_DIR
from database.db_manager import DatabaseManager
from learning.youtube_recommender import YouTubeRecommender
from llm_provider.kimi_provider import KimiProvider
from llm_provider.openai_provider import OpenAIProvider
from reports.csv_exporter import CSVExporter
from scrapers.factory import build_scrapers
from scrapers.http_client import RequestsFallbackClient
from scrapers.playwright_controller import PlaywrightController
from scrapers.base import merge_jobs
from visualization.market_dashboard import MarketDashboardBuilder


class CareerCrawlerService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.db = DatabaseManager(config.DATABASE_URL)
        self.db.init_db()

        self.scrapers = build_scrapers(config)
        self.market_analyzer = MarketAnalyzer()
        self.ranker = JobRanker()
        self.skill_gap_analyzer = SkillGapAnalyzer()
        self.score_calculator = CareerScoreCalculator()
        self.recommender = YouTubeRecommender(config.LEARNING_RESOURCES_PER_SKILL)
        self.csv_exporter = CSVExporter(config.REPORTS_DIR)
        self.dashboard_builder = MarketDashboardBuilder(config.REPORTS_DIR)

        self.auto_apply_engine = AutoApplyEngine(
            config=config,
            playwright=PlaywrightController(fallback_client=RequestsFallbackClient()),
        )

    def get_config_snapshot(self) -> dict[str, Any]:
        current_provider = self.db.get_setting("llm_provider") or self.config.LLM_PROVIDER
        onboarding_complete = self.db.get_setting("onboarding_complete") == "true"
        return {
            **self.config.model_dump(),
            "LLM_PROVIDER": current_provider,
            "ONBOARDING_COMPLETE": onboarding_complete,
        }

    def scrape_jobs(self, domains: list[str] | None = None) -> list[dict[str, Any]]:
        domains = domains or ["linkedin", "indeed", "greenhouse", "lever"]
        selected = [d.lower().strip() for d in domains if d.lower().strip() in self.scrapers]
        if not selected:
            selected = ["linkedin", "indeed", "greenhouse", "lever"]

        job_lists = [self.scrapers[source].scrape() for source in selected]
        jobs = merge_jobs(job_lists)

        profile = self.db.get_user_profile()
        ranked_jobs = self.ranker.rank_jobs(jobs, profile)
        inserted = self.db.upsert_jobs(ranked_jobs)

        return {
            "inserted": inserted,
            "total_scraped": len(jobs),
            "jobs": [job.model_dump(mode="json") for job in ranked_jobs],
        }

    def list_jobs(self, limit: int = 200) -> list[dict[str, Any]]:
        return [job.model_dump(mode="json") for job in self.db.list_jobs(limit=limit)]

    def run_market_analysis(self) -> dict[str, Any]:
        jobs = self.db.list_jobs(limit=1000)
        insights = self.market_analyzer.analyze(jobs)
        self.db.save_market_analysis(insights)
        self.dashboard_builder.build(insights)
        return insights.model_dump(mode="json")

    def latest_market_analysis(self) -> dict[str, Any]:
        insights = self.db.latest_market_analysis()
        if insights is None:
            insights = self.market_analyzer.analyze(self.db.list_jobs(limit=1000))
            self.db.save_market_analysis(insights)
        return insights.model_dump(mode="json")

    def save_user_cv(self, cv_path: str) -> dict[str, Any]:
        cv_text = self.skill_gap_analyzer.extract_text_from_cv(cv_path)
        extracted_skills = self.skill_gap_analyzer.extract_skills_from_text(cv_text)

        years = self._infer_years_experience(cv_text)
        profile = self.db.get_user_profile()
        updated = UserProfile(
            cv_text=cv_text,
            linkedin_url=profile.linkedin_url,
            skills=extracted_skills,
            years_experience=max(profile.years_experience, years),
            preferred_domains=profile.preferred_domains,
        )
        self.db.save_user_profile(updated)
        return updated.model_dump(mode="json")

    def save_linkedin_url(self, linkedin_url: str) -> dict[str, Any]:
        profile = self.db.get_user_profile()
        updated = UserProfile(
            cv_text=profile.cv_text,
            linkedin_url=linkedin_url,
            skills=profile.skills,
            years_experience=profile.years_experience,
            preferred_domains=profile.preferred_domains,
        )
        self.db.save_user_profile(updated)
        return updated.model_dump(mode="json")

    def compute_skill_gap(self) -> dict[str, Any]:
        profile = self.db.get_user_profile()
        insights = self.db.latest_market_analysis() or self.market_analyzer.analyze(self.db.list_jobs(limit=1000))

        market_skills = [item["skill"] for item in insights.top_demanded_skills[:20]]
        report = self.skill_gap_analyzer.analyze(profile.skills, market_skills)
        self.db.save_skill_gap(report)
        return report.model_dump(mode="json")

    def recommend_learning_resources(self) -> list[dict[str, Any]]:
        gap = self.compute_skill_gap()
        missing = gap["missing_skills"]
        resources = self.recommender.recommend(missing)
        self.db.save_learning_resources(resources)
        return [resource.model_dump(mode="json") for resource in resources]

    def calculate_career_readiness(self) -> dict[str, Any]:
        jobs = self.db.list_jobs(limit=1000)
        profile = self.db.get_user_profile()

        gap_report = self.compute_skill_gap()
        market_count = len(gap_report["market_skills"])
        matched_count = len(gap_report["matched_skills"])
        missing_count = len(gap_report["missing_skills"])

        avg_match_score = mean([job.match_score for job in jobs]) if jobs else 0.0

        report = self.score_calculator.calculate(
            avg_job_match_score=avg_match_score,
            matched_skills=matched_count,
            missing_skills=missing_count,
            total_market_skills=market_count,
            years_experience=profile.years_experience,
        )
        self.db.save_career_score(report)
        return report.model_dump(mode="json")

    def export_reports(self) -> dict[str, str]:
        jobs = self.db.list_jobs(limit=2000)
        return self.csv_exporter.export_jobs(jobs)

    def run_auto_apply(self, resume_path: str | None, limit: int = 5) -> list[dict[str, str]]:
        jobs = self.db.list_jobs(limit=200)
        ranked = sorted(jobs, key=lambda j: j.match_score, reverse=True)
        return self.auto_apply_engine.run(ranked, resume_path=resume_path, limit=limit)

    def run_pipeline(self, payload: PipelineRequest) -> dict[str, Any]:
        profile = self.db.get_user_profile()
        if payload.linkedin_url:
            profile = UserProfile(
                cv_text=profile.cv_text,
                linkedin_url=payload.linkedin_url,
                skills=profile.skills,
                years_experience=profile.years_experience,
                preferred_domains=payload.preferred_domains or profile.preferred_domains,
            )
            self.db.save_user_profile(profile)
        elif payload.preferred_domains:
            profile = UserProfile(
                cv_text=profile.cv_text,
                linkedin_url=profile.linkedin_url,
                skills=profile.skills,
                years_experience=profile.years_experience,
                preferred_domains=payload.preferred_domains,
            )
            self.db.save_user_profile(profile)

        scrape_result = self.scrape_jobs(payload.domains)
        market = self.run_market_analysis()
        gap = self.compute_skill_gap()
        resources = self.recommend_learning_resources()
        readiness = self.calculate_career_readiness()
        reports = self.export_reports()
        auto_apply = self.run_auto_apply(resume_path=None, limit=5) if self.config.AUTO_APPLY else []

        return {
            "scrape": scrape_result,
            "market_analysis": market,
            "skill_gap": gap,
            "learning_resources": resources,
            "career_readiness": readiness,
            "reports": reports,
            "auto_apply": auto_apply,
        }

    def submit_onboarding(self, payload: OnboardingRequest) -> dict[str, Any]:
        provider = "none"
        status = "local_mode"

        if payload.has_provider:
            provider = payload.provider.lower().strip()
            if provider == "openai":
                if not payload.api_key:
                    return {"status": "error", "message": "OPENAI_API_KEY is required."}
                client = OpenAIProvider(api_key=payload.api_key, base_url=payload.base_url)
                if not client.validate_credentials(payload.api_key, payload.base_url):
                    return {"status": "error", "message": "Invalid OpenAI credentials."}
                self._upsert_env("OPENAI_API_KEY", payload.api_key)
                if payload.base_url:
                    self._upsert_env("OPENAI_BASE_URL", payload.base_url)
                status = "configured"
            elif provider == "nvidia kimi":
                if not payload.api_key:
                    return {"status": "error", "message": "Kimi API key is required."}
                client = KimiProvider(api_key=payload.api_key, base_url=payload.base_url)
                if not client.validate_credentials(payload.api_key, payload.base_url):
                    return {"status": "error", "message": "Invalid Kimi credentials."}
                self._upsert_env("KIMI_API_KEY", payload.api_key)
                if payload.base_url:
                    self._upsert_env("KIMI_BASE_URL", payload.base_url)
                status = "configured"
            else:
                if not payload.api_key:
                    return {"status": "error", "message": "API key is required for custom provider."}
                if not payload.base_url:
                    return {"status": "error", "message": "Base URL is required for custom provider."}
                client = OpenAIProvider(api_key=payload.api_key, base_url=payload.base_url)
                if not client.validate_credentials(payload.api_key, payload.base_url):
                    return {"status": "error", "message": "Invalid custom provider credentials."}
                self._upsert_env("OPENAI_COMPATIBLE_API_KEY", payload.api_key)
                self._upsert_env("OPENAI_COMPATIBLE_BASE_URL", payload.base_url)
                status = "configured"
        else:
            provider = "none"
            status = "local_mode"

        self.db.set_setting("llm_provider", provider)
        self.db.set_setting("onboarding_complete", "true")

        return {
            "status": status,
            "provider": provider,
            "message": "Onboarding saved successfully.",
        }

    def get_latest_skill_gap(self) -> dict[str, Any]:
        report = self.db.latest_skill_gap()
        if report is None:
            return self.compute_skill_gap()
        return report.model_dump(mode="json")

    def get_learning_resources(self) -> list[dict[str, Any]]:
        resources = self.db.latest_learning_resources(limit=100)
        if not resources:
            return self.recommend_learning_resources()
        return [item.model_dump(mode="json") for item in resources]

    def get_latest_career_score(self) -> dict[str, Any]:
        score = self.db.latest_career_score()
        if score is None:
            return self.calculate_career_readiness()
        return score.model_dump(mode="json")

    def _upsert_env(self, key: str, value: str) -> None:
        env_path = ROOT_DIR / ".env"
        existing = {}
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    existing[k.strip()] = v.strip()

        existing[key] = value

        content = "\n".join(f"{k}={v}" for k, v in sorted(existing.items())) + "\n"
        env_path.write_text(content, encoding="utf-8")

    def _infer_years_experience(self, text: str) -> int:
        patterns = [
            r"(\d+)\+?\s+years?\s+of\s+experience",
            r"experience\s*:\s*(\d+)\+?\s+years?",
        ]
        values: list[int] = []
        for pattern in patterns:
            for value in re.findall(pattern, text.lower()):
                try:
                    values.append(int(value))
                except ValueError:
                    continue
        return max(values) if values else 0
