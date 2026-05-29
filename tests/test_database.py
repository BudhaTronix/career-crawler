from __future__ import annotations

from sqlalchemy import inspect

from database.db_manager import DatabaseManager


REQUIRED_TABLES = {
    "jobs",
    "companies",
    "applications",
    "user_profile",
    "market_analysis",
    "learning_resources",
    "career_scores",
    "app_settings",
}


def test_database_initialization_creates_tables(test_config):
    db = DatabaseManager(test_config.DATABASE_URL)
    db.init_db()

    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())

    assert REQUIRED_TABLES.issubset(tables)


def test_job_upsert_deduplicates_by_url_hash(test_config, sample_jobs):
    db = DatabaseManager(test_config.DATABASE_URL)
    db.init_db()

    first_insert = db.upsert_jobs(sample_jobs)
    second_insert = db.upsert_jobs(sample_jobs)

    assert first_insert == len(sample_jobs)
    assert second_insert == 0
    assert db.count_jobs() == len(sample_jobs)
