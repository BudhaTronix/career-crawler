from __future__ import annotations

import time
from datetime import datetime, timezone

import pandas as pd

from automation.scheduler import PipelineScheduler
from backend.models import JobRecord
from reports.csv_exporter import CSVExporter, REQUIRED_COLUMNS


def test_scheduler_registers_job():
    scheduler = PipelineScheduler()
    hit = {"count": 0}

    def callback():
        hit["count"] += 1

    scheduler.register("*/10 * * * *", callback)
    jobs = scheduler.scheduler.get_jobs()
    assert jobs
    assert jobs[0].id == PipelineScheduler.JOB_ID


def test_csv_export_columns(test_config):
    exporter = CSVExporter(test_config.REPORTS_DIR)
    now = datetime.now(timezone.utc)
    jobs = [
        JobRecord(
            title="ML Engineer",
            company="Acme",
            location="Remote",
            salary_estimate=120000,
            skills_required=["Python"],
            job_url="https://example.com/1",
            date_posted=now,
            job_description="desc",
            source="linkedin",
            is_remote=True,
            normalized_title="Ml Engineer",
            url_hash="h1",
            match_score=8.2,
        )
    ]

    files = exporter.export_jobs(jobs)
    df = pd.read_csv(files["jobs_today"])
    assert list(df.columns) == REQUIRED_COLUMNS
