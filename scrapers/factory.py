from __future__ import annotations

from config.config_loader import AppConfig
from backend.safety import SafeModeGuard
from scrapers.base import BaseScraper, DomainRateLimiter
from scrapers.greenhouse_scraper import GreenhouseScraper
from scrapers.http_client import RequestsFallbackClient
from scrapers.indeed_scraper import IndeedScraper
from scrapers.lever_scraper import LeverScraper
from scrapers.linkedin_scraper import LinkedInScraper
from scrapers.playwright_controller import PlaywrightController


def build_scrapers(config: AppConfig) -> dict[str, BaseScraper]:
    guard = SafeModeGuard(config)
    limiter = DomainRateLimiter(min_interval_seconds=3.0)
    playwright = PlaywrightController(fallback_client=RequestsFallbackClient())
    return {
        "linkedin": LinkedInScraper(config, guard, playwright, limiter),
        "indeed": IndeedScraper(config, guard, playwright, limiter),
        "greenhouse": GreenhouseScraper(config, guard, playwright, limiter),
        "lever": LeverScraper(config, guard, playwright, limiter),
    }
