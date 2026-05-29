from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class JobRecord(BaseModel):
    title: str
    company: str
    location: str
    salary_estimate: float | None = None
    skills_required: list[str] = Field(default_factory=list)
    job_url: str
    date_posted: datetime
    job_description: str
    source: str
    is_remote: bool = False
    normalized_title: str = ""
    url_hash: str = ""
    match_score: float = 0.0


class UserProfile(BaseModel):
    cv_text: str = ""
    linkedin_url: str | None = None
    skills: list[str] = Field(default_factory=list)
    years_experience: int = 0
    preferred_domains: list[str] = Field(default_factory=list)


class MarketInsights(BaseModel):
    top_demanded_skills: list[dict[str, Any]] = Field(default_factory=list)
    salary_ranges: dict[str, float | int | None] = Field(default_factory=dict)
    top_hiring_companies: list[dict[str, Any]] = Field(default_factory=list)
    trending_technologies: list[dict[str, Any]] = Field(default_factory=list)
    geographic_distribution: list[dict[str, Any]] = Field(default_factory=list)
    skill_trend_over_time: list[dict[str, Any]] = Field(default_factory=list)
    hiring_activity_timeline: list[dict[str, Any]] = Field(default_factory=list)


class SkillGapReport(BaseModel):
    user_skills: list[str] = Field(default_factory=list)
    market_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    matched_skills: list[str] = Field(default_factory=list)


class LearningResource(BaseModel):
    skill: str
    title: str
    url: str
    channel: str
    rank: int


class CareerScoreReport(BaseModel):
    score: int
    band: str
    top_skills_to_improve: list[str] = Field(default_factory=list)
    estimated_improvement_impact: dict[str, int] = Field(default_factory=dict)


class OnboardingRequest(BaseModel):
    has_provider: bool
    provider: str = "none"
    api_key: str | None = None
    base_url: str | None = None


class LinkedInInput(BaseModel):
    linkedin_url: HttpUrl


class ScrapeRequest(BaseModel):
    domains: list[str] = Field(default_factory=lambda: ["linkedin", "indeed", "greenhouse", "lever"])


class PipelineRequest(BaseModel):
    domains: list[str] = Field(default_factory=lambda: ["linkedin", "indeed", "greenhouse", "lever"])
    linkedin_url: str | None = None
    preferred_domains: list[str] = Field(default_factory=list)


class AutoApplyRequest(BaseModel):
    resume_path: str | None = None
    limit: int = 5
