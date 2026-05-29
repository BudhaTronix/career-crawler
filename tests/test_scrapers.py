from __future__ import annotations

from backend.errors import ExternalAccessBlockedError
from backend.safety import SafeModeGuard
from backend.utils import hash_url, is_within_last_24_hours
from scrapers.factory import build_scrapers
from scrapers.base import merge_jobs


def test_mock_scrapers_parse_recent_jobs_only(test_config):
    scrapers = build_scrapers(test_config)
    linkedin_jobs = scrapers["linkedin"].scrape()
    indeed_jobs = scrapers["indeed"].scrape()

    assert linkedin_jobs
    assert indeed_jobs
    assert all(is_within_last_24_hours(job.date_posted) for job in linkedin_jobs + indeed_jobs)


def test_dedupe_uses_url_hash(test_config):
    scrapers = build_scrapers(test_config)
    linkedin_jobs = scrapers["linkedin"].scrape()
    greenhouse_jobs = scrapers["greenhouse"].scrape()

    merged = merge_jobs([linkedin_jobs, greenhouse_jobs])
    hashes = [job.url_hash for job in merged]

    assert len(hashes) == len(set(hashes))
    assert hash_url("https://www.linkedin.com/jobs/view/11111?ref=greenhouse") == hash_url(
        "https://www.linkedin.com/jobs/view/11111"
    )


def test_safe_mode_blocks_real_external_access(test_config):
    guard = SafeModeGuard(test_config)
    try:
        guard.assert_can_access_url("https://www.linkedin.com/jobs/search/")
    except ExternalAccessBlockedError:
        pass
    else:
        raise AssertionError("Expected external access to be blocked in development mode")
