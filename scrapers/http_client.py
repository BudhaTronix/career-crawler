from __future__ import annotations

import random
import time

import requests


class RequestsFallbackClient:
    USER_AGENTS = [
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    ]

    def __init__(self) -> None:
        self.session = requests.Session()

    def get(self, url: str, retries: int = 3, production_mode: bool = False) -> str:
        backoff = 1.0
        for attempt in range(1, retries + 1):
            headers = {"User-Agent": random.choice(self.USER_AGENTS)}
            if production_mode:
                time.sleep(random.uniform(2.0, 6.0))

            response = self.session.get(url, headers=headers, timeout=20)
            if response.status_code < 400:
                return response.text

            if attempt == retries:
                response.raise_for_status()
            time.sleep(backoff)
            backoff *= 2

        return ""
