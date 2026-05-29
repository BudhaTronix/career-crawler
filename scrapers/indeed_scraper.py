from urllib.parse import quote_plus

from scrapers.base import BaseScraper


class IndeedScraper(BaseScraper):
    source = "indeed"

    def build_search_url(self, search_terms: str) -> str:
        return f"https://www.indeed.com/jobs?q={quote_plus(search_terms)}"
