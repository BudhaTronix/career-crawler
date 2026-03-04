from urllib.parse import quote_plus

from scrapers.base import BaseScraper


class GreenhouseScraper(BaseScraper):
    source = "greenhouse"

    def build_search_url(self, search_terms: str) -> str:
        return f"https://boards.greenhouse.io/?search={quote_plus(search_terms)}"
