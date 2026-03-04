from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd

from backend.models import JobRecord, MarketInsights


class MarketAnalyzer:
    def analyze(self, jobs: list[JobRecord]) -> MarketInsights:
        if not jobs:
            return MarketInsights()

        df = pd.DataFrame([job.model_dump() for job in jobs])
        df["date_posted"] = pd.to_datetime(df["date_posted"], utc=True)

        skills_counter: Counter[str] = Counter()
        for skills in df["skills_required"].tolist():
            for skill in skills:
                skills_counter[skill.lower()] += 1

        top_skills = [
            {"skill": skill.title(), "count": count}
            for skill, count in skills_counter.most_common(20)
        ]

        salary_series = pd.to_numeric(df["salary_estimate"], errors="coerce").dropna()
        salary_ranges = {
            "min": float(salary_series.min()) if not salary_series.empty else None,
            "max": float(salary_series.max()) if not salary_series.empty else None,
            "avg": float(salary_series.mean()) if not salary_series.empty else None,
            "median": float(salary_series.median()) if not salary_series.empty else None,
        }

        company_counts = df["company"].value_counts().head(10)
        top_companies = [
            {"company": company, "count": int(count)}
            for company, count in company_counts.items()
        ]

        tech_terms = [
            item for item in skills_counter.items() if item[0] not in {"communication", "teamwork"}
        ]
        trending_tech = [
            {"technology": term.title(), "count": count}
            for term, count in sorted(tech_terms, key=lambda x: x[1], reverse=True)[:15]
        ]

        location_counts = df["location"].value_counts().head(15)
        geo_dist = [{"location": loc, "count": int(count)} for loc, count in location_counts.items()]

        trend_df = (
            df.assign(date_bucket=df["date_posted"].dt.floor("6h"))
            .explode("skills_required")
            .groupby(["date_bucket", "skills_required"], dropna=False)
            .size()
            .reset_index(name="count")
        )
        trend_df = trend_df.sort_values("count", ascending=False).head(50)
        skill_trend = [
            {
                "date": row["date_bucket"].isoformat(),
                "skill": (row["skills_required"] or "Unknown").title(),
                "count": int(row["count"]),
            }
            for _, row in trend_df.iterrows()
        ]

        timeline = (
            df.assign(date_bucket=df["date_posted"].dt.floor("6h"))
            .groupby("date_bucket")
            .size()
            .reset_index(name="count")
            .sort_values("date_bucket")
        )
        hiring_timeline = [
            {"date": row["date_bucket"].isoformat(), "count": int(row["count"])}
            for _, row in timeline.iterrows()
        ]

        # Numpy-based smoothing to avoid highly volatile trend presentation.
        if len(hiring_timeline) >= 3:
            counts = np.array([item["count"] for item in hiring_timeline], dtype=float)
            smoothed = np.convolve(counts, np.ones(3) / 3, mode="same")
            for idx, value in enumerate(smoothed.tolist()):
                hiring_timeline[idx]["smoothed_count"] = round(float(value), 2)

        return MarketInsights(
            top_demanded_skills=top_skills,
            salary_ranges=salary_ranges,
            top_hiring_companies=top_companies,
            trending_technologies=trending_tech,
            geographic_distribution=geo_dist,
            skill_trend_over_time=skill_trend,
            hiring_activity_timeline=hiring_timeline,
        )
