from urllib.parse import quote_plus

from scrapers.base import BaseScraper


class LinkedInScraper(BaseScraper):
    source = "linkedin"

    def build_search_url(self, search_terms: str) -> str:
        return f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(search_terms)}"
