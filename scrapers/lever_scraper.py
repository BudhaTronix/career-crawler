from urllib.parse import quote_plus

from scrapers.base import BaseScraper


class LeverScraper(BaseScraper):
    source = "lever"

    def build_search_url(self, search_terms: str) -> str:
        return f"https://jobs.lever.co/search?query={quote_plus(search_terms)}"
