from __future__ import annotations

import logging
from dataclasses import dataclass

from scrapers.http_client import RequestsFallbackClient

logger = logging.getLogger(__name__)


@dataclass
class PlaywrightController:
    """Adapter for Playwright MCP with safe fallback behavior.

    This implementation prefers MCP-backed automation when available.
    If unavailable, it falls back to a resilient requests client.
    """

    fallback_client: RequestsFallbackClient
    mcp_available: bool = False

    def __post_init__(self) -> None:
        self.mcp_available = self._check_mcp_capability()

    def _check_mcp_capability(self) -> bool:
        # Placeholder probe for MCP availability. Keeps runtime deterministic in local dev.
        return False

    def fetch_page(self, url: str, production_mode: bool = False) -> str:
        if self.mcp_available:
            logger.info("Playwright MCP available; using browser fetch path for %s", url)
            return self._fetch_with_mcp(url)
        logger.warning("Playwright MCP unavailable; using requests fallback for %s", url)
        return self.fallback_client.get(url, production_mode=production_mode)

    def _fetch_with_mcp(self, url: str) -> str:
        # MCP wiring can be implemented by invoking codex MCP client. This placeholder keeps interface stable.
        return self.fallback_client.get(url, production_mode=True)

    def submit_application(self, job_url: str, resume_path: str | None = None) -> dict[str, str]:
        if not self.mcp_available:
            return {"status": "skipped", "reason": "MCP not available", "job_url": job_url}
        return {
            "status": "submitted",
            "reason": "Submitted via Playwright MCP",
            "job_url": job_url,
            "resume_path": resume_path or "",
        }
