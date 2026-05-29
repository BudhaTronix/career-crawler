from __future__ import annotations

from backend.models import CareerScoreReport


class CareerScoreCalculator:
    def calculate(
        self,
        avg_job_match_score: float,
        matched_skills: int,
        missing_skills: int,
        total_market_skills: int,
        years_experience: int,
    ) -> CareerScoreReport:
        total_market_skills = max(total_market_skills, 1)
        skill_match_ratio = matched_skills / total_market_skills
        experience_factor = min(years_experience / 10.0, 1.0)
        missing_penalty = min(missing_skills / total_market_skills, 1.0)

        score = (
            avg_job_match_score * 6.0
            + skill_match_ratio * 30.0
            + experience_factor * 20.0
            + (1.0 - missing_penalty) * 10.0
        )
        final_score = int(round(max(min(score, 100), 0)))

        if final_score < 40:
            band = "Early stage"
        elif final_score < 70:
            band = "Developing profile"
        elif final_score < 90:
            band = "Strong candidate"
        else:
            band = "Highly competitive"

        improvement_impact = {
            "Kubernetes": 8,
            "Docker": 5,
            "Vector Databases": 6,
            "LLM Orchestration": 7,
            "System Design": 5,
        }

        return CareerScoreReport(
            score=final_score,
            band=band,
            top_skills_to_improve=list(improvement_impact.keys())[:3],
            estimated_improvement_impact=improvement_impact,
        )
