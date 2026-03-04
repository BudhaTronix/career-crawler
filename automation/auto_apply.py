from __future__ import annotations

from backend.models import JobRecord
from config.config_loader import AppConfig
from scrapers.playwright_controller import PlaywrightController


class AutoApplyEngine:
    def __init__(self, config: AppConfig, playwright: PlaywrightController) -> None:
        self.config = config
        self.playwright = playwright

    def run(self, jobs: list[JobRecord], resume_path: str | None = None, limit: int = 5) -> list[dict[str, str]]:
        if not self.config.AUTO_APPLY:
            return [{"status": "disabled", "reason": "AUTO_APPLY=false", "count": str(len(jobs))}]

        selected = jobs[:limit]
        results: list[dict[str, str]] = []

        for job in selected:
            ats = self._detect_ats(job.job_url)
            if self.config.MODE == "development":
                results.append(
                    {
                        "job_url": job.job_url,
                        "status": "dry-run",
                        "ats": ats,
                        "reason": "Development mode blocks real submissions",
                    }
                )
                continue

            if ats == "unknown":
                results.append(
                    {
                        "job_url": job.job_url,
                        "status": "skipped",
                        "ats": ats,
                        "reason": "Unsupported ATS",
                    }
                )
                continue

            submission = self.playwright.submit_application(job.job_url, resume_path)
            submission["ats"] = ats
            results.append(submission)

        return results

    def _detect_ats(self, url: str) -> str:
        lowered = url.lower()
        if "greenhouse" in lowered:
            return "greenhouse"
        if "lever" in lowered:
            return "lever"
        if "workday" in lowered:
            return "workday"
        return "unknown"
