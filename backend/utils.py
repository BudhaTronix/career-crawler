from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Iterable
from urllib.parse import urlparse, urlunparse

SENIORITY_PATTERNS = [
    r"\bsenior\b",
    r"\bjunior\b",
    r"\blead\b",
    r"\bprincipal\b",
    r"\bstaff\b",
    r"\bii\b",
    r"\biii\b",
]



def normalize_job_title(title: str) -> str:
    normalized = title.lower()
    for pattern in SENIORITY_PATTERNS:
        normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return " ".join(word.capitalize() for word in normalized.split())



def canonicalize_url(url: str) -> str:
    parsed = urlparse(url)
    cleaned = parsed._replace(query="", fragment="")
    return urlunparse(cleaned)



def hash_url(url: str) -> str:
    canonical = canonicalize_url(url)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()



def parse_date_posted(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    lowered = value.strip().lower()
    now = datetime.now(timezone.utc)

    if lowered.endswith("hours ago"):
        hours = int(lowered.split()[0])
        return now - timedelta(hours=hours)
    if lowered.endswith("hour ago"):
        return now - timedelta(hours=1)
    if lowered.endswith("days ago"):
        days = int(lowered.split()[0])
        return now - timedelta(days=days)
    if lowered.endswith("day ago"):
        return now - timedelta(days=1)

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)



def is_within_last_24_hours(date_posted: datetime) -> bool:
    now = datetime.now(timezone.utc)
    return date_posted >= now - timedelta(hours=24)



def to_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)



def from_json(value: str | None, default: object) -> object:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default



def unique_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output
