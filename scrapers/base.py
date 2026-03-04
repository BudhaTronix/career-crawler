from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from backend.models import JobRecord
from backend.safety import SafeModeGuard
from backend.utils import hash_url, is_within_last_24_hours, normalize_job_title, parse_date_posted, unique_preserve_order
from config.config_loader import AppConfig, ROOT_DIR
from scrapers.http_client import RequestsFallbackClient
from scrapers.playwright_controller import PlaywrightController


class DomainRateLimiter:
    def __init__(self, min_interval_seconds: float = 3.0) -> None:
        self.min_interval_seconds = min_interval_seconds
        self._last_request_time: dict[str, float] = defaultdict(float)

    def wait(self, url: str) -> None:
        domain = urlparse(url).netloc.lower()
        now = time.time()
        delta = now - self._last_request_time[domain]
        if delta < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - delta)
        self._last_request_time[domain] = time.time()


class BaseScraper:
    source: str = "base"

    def __init__(self, config: AppConfig, guard: SafeModeGuard, playwright: PlaywrightController, limiter: DomainRateLimiter) -> None:
        self.config = config
        self.guard = guard
        self.playwright = playwright
        self.limiter = limiter

    @property
    def mock_file(self) -> Path:
        return ROOT_DIR / self.config.MOCK_PAGES_DIR / f"{self.source}_jobs.html"

    def scrape(self, search_terms: str = "machine learning engineer") -> list[JobRecord]:
        if self.config.is_development() or not self.config.ENABLE_EXTERNAL_SCRAPING:
            return self.scrape_from_mock()
        self.guard.assert_external_scraping_enabled()
        return self.scrape_external(search_terms)

    def scrape_from_mock(self) -> list[JobRecord]:
        html = self.mock_file.read_text(encoding="utf-8")
        return self._parse_html(html)

    def scrape_external(self, search_terms: str) -> list[JobRecord]:
        url = self.build_search_url(search_terms)
        self.guard.assert_can_access_url(url)
        self.limiter.wait(url)
        html = self.playwright.fetch_page(url, production_mode=self.config.MODE == "production")
        return self._parse_html(html)

    def build_search_url(self, search_terms: str) -> str:
        raise NotImplementedError

    def _parse_html(self, html: str) -> list[JobRecord]:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".job-card")
        jobs: list[JobRecord] = []

        for card in cards:
            title = _node_text(card.select_one(".job-title"))
            company = _node_text(card.select_one(".company"))
            location = _node_text(card.select_one(".location"))
            salary_raw = _node_text(card.select_one(".salary"))
            skills_raw = _node_text(card.select_one(".skills"))
            link_el = card.select_one("a.job-link")
            date_raw = _node_text(card.select_one(".date-posted"))
            description = _node_text(card.select_one(".description"))
            remote_text = _node_text(card.select_one(".remote")).lower()

            if not all([title, company, location, link_el, date_raw]):
                continue

            date_posted = parse_date_posted(date_raw)
            if not is_within_last_24_hours(date_posted):
                continue

            job_url = link_el.get("href", "").strip()
            if not job_url:
                continue

            salary = _extract_salary(salary_raw)
            skills = _parse_skills(skills_raw)
            normalized_title = normalize_job_title(title)
            url_hash = hash_url(job_url)

            jobs.append(
                JobRecord(
                    title=title,
                    company=company,
                    location=location,
                    salary_estimate=salary,
                    skills_required=skills,
                    job_url=job_url,
                    date_posted=date_posted,
                    job_description=description,
                    source=self.source,
                    is_remote="remote" in remote_text or "remote" in location.lower(),
                    normalized_title=normalized_title,
                    url_hash=url_hash,
                )
            )

        deduped: dict[str, JobRecord] = {}
        for job in jobs:
            deduped[job.url_hash] = job
        return list(deduped.values())



def _extract_salary(salary_text: str) -> float | None:
    digits = "".join(ch for ch in salary_text if ch.isdigit() or ch in {".", ","})
    if not digits:
        return None
    try:
        return float(digits.replace(",", ""))
    except ValueError:
        return None



def _parse_skills(skills_text: str) -> list[str]:
    raw = [part.strip() for part in skills_text.replace("|", ",").split(",")]
    return unique_preserve_order([item for item in raw if item])


def _node_text(node: object) -> str:
    return node.get_text(strip=True) if node is not None else ""



def merge_jobs(job_lists: Iterable[list[JobRecord]]) -> list[JobRecord]:
    unique: dict[str, JobRecord] = {}
    for job_list in job_lists:
        for job in job_list:
            unique[job.url_hash] = job
    return sorted(unique.values(), key=lambda j: j.date_posted, reverse=True)
