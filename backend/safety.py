from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from backend.errors import ExternalAccessBlockedError
from config.config_loader import AppConfig


BLOCKED_JOB_DOMAINS = {
    "linkedin.com",
    "www.linkedin.com",
    "indeed.com",
    "www.indeed.com",
    "wellfound.com",
    "www.wellfound.com",
    "boards.greenhouse.io",
    "greenhouse.io",
    "jobs.lever.co",
    "lever.co",
}


@dataclass(frozen=True)
class SafeModeGuard:
    config: AppConfig

    def assert_external_scraping_enabled(self) -> None:
        if not self.config.can_scrape_externally():
            raise ExternalAccessBlockedError(
                "External scraping is disabled. Set MODE=production and ENABLE_EXTERNAL_SCRAPING=true to enable."
            )

    def assert_can_access_url(self, url: str) -> None:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain in BLOCKED_JOB_DOMAINS and not self.config.can_scrape_externally():
            raise ExternalAccessBlockedError(
                f"Access to external job domain '{domain}' is blocked in current mode."
            )
