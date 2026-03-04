from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.models import JobRecord
from config.config_loader import AppConfig


@pytest.fixture
def test_config(tmp_path: Path) -> AppConfig:
    reports_dir = tmp_path / "reports"
    db_path = tmp_path / "career_test.db"
    return AppConfig(
        MODE="development",
        ENABLE_EXTERNAL_SCRAPING=False,
        AUTO_APPLY=False,
        LEARNING_RESOURCES_PER_SKILL=2,
        LLM_PROVIDER="none",
        SCHEDULER_CRON="0 3 * * *",
        DATABASE_URL=f"sqlite:///{db_path}",
        REPORTS_DIR=str(reports_dir),
        MOCK_PAGES_DIR="tests/mock_pages",
    )


@pytest.fixture
def sample_jobs() -> list[JobRecord]:
    now = datetime.now(timezone.utc)
    return [
        JobRecord(
            title="Senior Machine Learning Engineer",
            company="Acme AI",
            location="Remote",
            salary_estimate=180000,
            skills_required=["Python", "Kubernetes", "Docker"],
            job_url="https://example.com/jobs/1",
            date_posted=now,
            job_description="Build production ML systems with LLM orchestration.",
            source="linkedin",
            is_remote=True,
            normalized_title="Machine Learning Engineer",
            url_hash="hash1",
        ),
        JobRecord(
            title="Data Engineer",
            company="Orbit Labs",
            location="Seattle, WA",
            salary_estimate=160000,
            skills_required=["Python", "SQL", "Airflow"],
            job_url="https://example.com/jobs/2",
            date_posted=now,
            job_description="Data platform development.",
            source="greenhouse",
            is_remote=False,
            normalized_title="Data Engineer",
            url_hash="hash2",
        ),
    ]
