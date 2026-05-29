from __future__ import annotations

import requests

from llm_provider.base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, base_url: str | None = None, model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.model = model

    def validate_credentials(self, api_key: str | None = None, base_url: str | None = None) -> bool:
        key = api_key or self.api_key
        url = (base_url or self.base_url).rstrip("/") + "/models"
        response = requests.get(url, headers={"Authorization": f"Bearer {key}"}, timeout=15)
        return response.status_code < 300

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        response = requests.post(
            self.base_url + "/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return str(content)
