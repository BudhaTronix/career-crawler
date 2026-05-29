from __future__ import annotations

from dataclasses import dataclass

from backend.models import JobRecord, UserProfile


@dataclass(frozen=True)
class RankingWeights:
    skill_match: float = 0.35
    domain_relevance: float = 0.25
    salary: float = 0.20
    remote: float = 0.10
    company_reputation: float = 0.10


class JobRanker:
    def __init__(self, weights: RankingWeights | None = None) -> None:
        self.weights = weights or RankingWeights()

    def rank_jobs(self, jobs: list[JobRecord], profile: UserProfile) -> list[JobRecord]:
        ranked = []
        for job in jobs:
            score = self.compute_match_score(job, profile)
            ranked.append(job.model_copy(update={"match_score": round(score, 2)}))
        return sorted(ranked, key=lambda job: job.match_score, reverse=True)

    def compute_match_score(self, job: JobRecord, profile: UserProfile) -> float:
        skill_score = self._skill_match_score(job.skills_required, profile.skills)
        domain_score = self._domain_relevance_score(job, profile.preferred_domains)
        salary_score = self._salary_score(job.salary_estimate)
        remote_score = 1.0 if job.is_remote else 0.4
        company_score = 0.65

        total = (
            skill_score * self.weights.skill_match
            + domain_score * self.weights.domain_relevance
            + salary_score * self.weights.salary
            + remote_score * self.weights.remote
            + company_score * self.weights.company_reputation
        )
        return min(max(total * 10, 0.0), 10.0)

    def _skill_match_score(self, required: list[str], user_skills: list[str]) -> float:
        if not required:
            return 0.5
        req = {skill.lower() for skill in required}
        have = {skill.lower() for skill in user_skills}
        overlap = len(req & have)
        return overlap / len(req)

    def _domain_relevance_score(self, job: JobRecord, preferred_domains: list[str]) -> float:
        if not preferred_domains:
            return 0.6
        title = job.normalized_title.lower() or job.title.lower()
        desc = job.job_description.lower()
        hits = 0
        for domain in preferred_domains:
            d = domain.lower().strip()
            if not d:
                continue
            if d in title or d in desc:
                hits += 1
        if not preferred_domains:
            return 0.6
        return min(hits / max(len(preferred_domains), 1), 1.0)

    def _salary_score(self, salary: float | None) -> float:
        if salary is None:
            return 0.5
        if salary <= 40000:
            return 0.2
        if salary >= 250000:
            return 1.0
        return (salary - 40000) / (250000 - 40000)
