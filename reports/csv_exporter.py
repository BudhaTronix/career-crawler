from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.models import JobRecord

REQUIRED_COLUMNS = ["company", "role", "location", "salary", "job_url", "match_score", "date_posted"]


class CSVExporter:
    def __init__(self, reports_dir: str) -> None:
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def export_jobs(self, jobs: list[JobRecord]) -> dict[str, str]:
        rows = [
            {
                "company": job.company,
                "role": job.title,
                "location": job.location,
                "salary": job.salary_estimate,
                "job_url": job.job_url,
                "match_score": job.match_score,
                "date_posted": job.date_posted.isoformat(),
            }
            for job in jobs
        ]
        df = pd.DataFrame(rows, columns=REQUIRED_COLUMNS)

        jobs_today_path = self.reports_dir / "jobs_today.csv"
        top_jobs_path = self.reports_dir / "top_jobs.csv"

        df.to_csv(jobs_today_path, index=False)
        df.sort_values("match_score", ascending=False).head(50).to_csv(top_jobs_path, index=False)

        return {"jobs_today": str(jobs_today_path), "top_jobs": str(top_jobs_path)}
