from __future__ import annotations

from llm_provider.openai_provider import OpenAIProvider


class KimiProvider(OpenAIProvider):
    def __init__(self, api_key: str, base_url: str | None = None, model: str = "moonshot-v1-8k") -> None:
        super().__init__(api_key=api_key, base_url=base_url or "https://api.moonshot.ai/v1", model=model)
