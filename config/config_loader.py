from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT_DIR / "config" / "config.yaml"


class AppConfig(BaseModel):
    MODE: Literal["development", "production"] = "development"
    ENABLE_EXTERNAL_SCRAPING: bool = False
    AUTO_APPLY: bool = False
    LEARNING_RESOURCES_PER_SKILL: int = 2
    LLM_PROVIDER: str = "none"
    SCHEDULER_CRON: str = "0 3 * * *"
    DATABASE_URL: str = "sqlite:///./career_crawler.db"
    REPORTS_DIR: str = "reports/output"
    MOCK_PAGES_DIR: str = "tests/mock_pages"

    def is_development(self) -> bool:
        return self.MODE == "development"

    def can_scrape_externally(self) -> bool:
        return self.MODE == "production" and self.ENABLE_EXTERNAL_SCRAPING


class RuntimeConfig(BaseModel):
    config_path: Path = Field(default=DEFAULT_CONFIG_PATH)
    settings: AppConfig



def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found at {path}")
    with path.open("r", encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}
    if not isinstance(content, dict):
        raise ValueError("Config file must contain a YAML mapping")
    return content


@lru_cache(maxsize=1)
def get_runtime_config(config_path: Path | None = None) -> RuntimeConfig:
    path = config_path or DEFAULT_CONFIG_PATH
    yaml_data = _load_yaml(path)

    # Environment overrides with identical key names, if present.
    for key in AppConfig.model_fields.keys():
        env_val = __import__("os").environ.get(key)
        if env_val is not None:
            if env_val.lower() in {"true", "false"}:
                yaml_data[key] = env_val.lower() == "true"
            elif env_val.isdigit() and key == "LEARNING_RESOURCES_PER_SKILL":
                yaml_data[key] = int(env_val)
            else:
                yaml_data[key] = env_val

    settings = AppConfig(**yaml_data)
    return RuntimeConfig(config_path=path, settings=settings)



def reload_runtime_config(config_path: Path | None = None) -> RuntimeConfig:
    get_runtime_config.cache_clear()
    return get_runtime_config(config_path)
