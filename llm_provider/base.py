from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    @abstractmethod
    def validate_credentials(self, api_key: str, base_url: str | None = None) -> bool:
        raise NotImplementedError

    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class LocalDeterministicProvider(BaseLLMProvider):
    def validate_credentials(self, api_key: str, base_url: str | None = None) -> bool:
        return True

    def generate(self, prompt: str) -> str:
        return f"Deterministic analysis: {prompt[:200]}"
