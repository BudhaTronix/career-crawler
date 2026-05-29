from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from backend.models import CareerScoreReport, JobRecord, LearningResource, MarketInsights, SkillGapReport, UserProfile
from backend.utils import from_json, to_json


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    reputation_score: Mapped[float] = mapped_column(Float, default=5.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    jobs: Mapped[list[Job]] = relationship("Job", back_populates="company")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    normalized_title: Mapped[str] = mapped_column(String(255), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    location: Mapped[str] = mapped_column(String(255))
    salary_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    skills_required: Mapped[str] = mapped_column(Text, default="[]")
    job_url: Mapped[str] = mapped_column(String(1024))
    url_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    date_posted: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    job_description: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(64), index=True)
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    match_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    company: Mapped[Company] = relationship("Company", back_populates="jobs")
    applications: Mapped[list[Application]] = relationship("Application", back_populates="job")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    status: Mapped[str] = mapped_column(String(64), default="pending")
    notes: Mapped[str] = mapped_column(Text, default="")
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    job: Mapped[Job] = relationship("Job", back_populates="applications")


class UserProfileModel(Base):
    __tablename__ = "user_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cv_text: Mapped[str] = mapped_column(Text, default="")
    linkedin_url: Mapped[str] = mapped_column(String(1024), default="")
    skills: Mapped[str] = mapped_column(Text, default="[]")
    years_experience: Mapped[int] = mapped_column(Integer, default=0)
    preferred_domains: Mapped[str] = mapped_column(Text, default="[]")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class MarketAnalysisModel(Base):
    __tablename__ = "market_analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    payload: Mapped[str] = mapped_column(Text, default="{}")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class LearningResourceModel(Base):
    __tablename__ = "learning_resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(1024))
    url: Mapped[str] = mapped_column(String(2048))
    channel: Mapped[str] = mapped_column(String(255), default="")
    rank: Mapped[int] = mapped_column(Integer, default=1)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CareerScoreModel(Base):
    __tablename__ = "career_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    score: Mapped[int] = mapped_column(Integer)
    band: Mapped[str] = mapped_column(String(64))
    top_skills_to_improve: Mapped[str] = mapped_column(Text, default="[]")
    estimated_improvement_impact: Mapped[str] = mapped_column(Text, default="{}")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class DatabaseManager:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, future=True)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)

    def init_db(self) -> None:
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        db = self.SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _get_or_create_company(self, db: Session, company_name: str) -> Company:
        company = db.query(Company).filter(Company.name == company_name).first()
        if company:
            return company
        company = Company(name=company_name)
        db.add(company)
        db.flush()
        return company

    def upsert_jobs(self, jobs: list[JobRecord]) -> int:
        inserted = 0
        with self.session() as db:
            for job in jobs:
                exists = db.query(Job).filter(Job.url_hash == job.url_hash).first()
                if exists:
                    continue
                company = self._get_or_create_company(db, job.company)
                db.add(
                    Job(
                        title=job.title,
                        normalized_title=job.normalized_title,
                        company_id=company.id,
                        location=job.location,
                        salary_estimate=job.salary_estimate,
                        skills_required=to_json(job.skills_required),
                        job_url=job.job_url,
                        url_hash=job.url_hash,
                        date_posted=job.date_posted,
                        job_description=job.job_description,
                        source=job.source,
                        is_remote=job.is_remote,
                        match_score=job.match_score,
                    )
                )
                inserted += 1
        return inserted

    def list_jobs(self, limit: int = 200) -> list[JobRecord]:
        with self.session() as db:
            rows = (
                db.query(Job, Company)
                .join(Company, Job.company_id == Company.id)
                .order_by(Job.date_posted.desc())
                .limit(limit)
                .all()
            )

            output: list[JobRecord] = []
            for job, company in rows:
                output.append(
                    JobRecord(
                        title=job.title,
                        company=company.name,
                        location=job.location,
                        salary_estimate=job.salary_estimate,
                        skills_required=from_json(job.skills_required, []),
                        job_url=job.job_url,
                        date_posted=job.date_posted,
                        job_description=job.job_description,
                        source=job.source,
                        is_remote=job.is_remote,
                        normalized_title=job.normalized_title,
                        url_hash=job.url_hash,
                        match_score=job.match_score,
                    )
                )
            return output

    def save_user_profile(self, profile: UserProfile) -> None:
        with self.session() as db:
            row = db.query(UserProfileModel).first()
            if row is None:
                row = UserProfileModel()
                db.add(row)
            row.cv_text = profile.cv_text
            row.linkedin_url = profile.linkedin_url or ""
            row.skills = to_json(profile.skills)
            row.years_experience = profile.years_experience
            row.preferred_domains = to_json(profile.preferred_domains)
            row.updated_at = datetime.now(timezone.utc)

    def get_user_profile(self) -> UserProfile:
        with self.session() as db:
            row = db.query(UserProfileModel).first()
            if row is None:
                return UserProfile()
            return UserProfile(
                cv_text=row.cv_text,
                linkedin_url=row.linkedin_url or None,
                skills=from_json(row.skills, []),
                years_experience=row.years_experience,
                preferred_domains=from_json(row.preferred_domains, []),
            )

    def save_market_analysis(self, insights: MarketInsights) -> None:
        with self.session() as db:
            db.add(MarketAnalysisModel(payload=insights.model_dump_json()))

    def latest_market_analysis(self) -> MarketInsights | None:
        with self.session() as db:
            row = db.query(MarketAnalysisModel).order_by(MarketAnalysisModel.generated_at.desc()).first()
            if not row:
                return None
            return MarketInsights.model_validate_json(row.payload)

    def save_learning_resources(self, resources: list[LearningResource]) -> None:
        with self.session() as db:
            for resource in resources:
                db.add(
                    LearningResourceModel(
                        skill=resource.skill,
                        title=resource.title,
                        url=resource.url,
                        channel=resource.channel,
                        rank=resource.rank,
                    )
                )

    def latest_learning_resources(self, limit: int = 50) -> list[LearningResource]:
        with self.session() as db:
            rows = (
                db.query(LearningResourceModel)
                .order_by(LearningResourceModel.generated_at.desc(), LearningResourceModel.rank.asc())
                .limit(limit)
                .all()
            )
            return [
                LearningResource(
                    skill=row.skill,
                    title=row.title,
                    url=row.url,
                    channel=row.channel,
                    rank=row.rank,
                )
                for row in rows
            ]

    def save_career_score(self, report: CareerScoreReport) -> None:
        with self.session() as db:
            db.add(
                CareerScoreModel(
                    score=report.score,
                    band=report.band,
                    top_skills_to_improve=to_json(report.top_skills_to_improve),
                    estimated_improvement_impact=to_json(report.estimated_improvement_impact),
                )
            )

    def latest_career_score(self) -> CareerScoreReport | None:
        with self.session() as db:
            row = db.query(CareerScoreModel).order_by(CareerScoreModel.generated_at.desc()).first()
            if not row:
                return None
            return CareerScoreReport(
                score=row.score,
                band=row.band,
                top_skills_to_improve=from_json(row.top_skills_to_improve, []),
                estimated_improvement_impact=from_json(row.estimated_improvement_impact, {}),
            )

    def save_skill_gap(self, report: SkillGapReport) -> None:
        with self.session() as db:
            row = db.query(AppSetting).filter(AppSetting.key == "latest_skill_gap").first()
            if row is None:
                row = AppSetting(key="latest_skill_gap", value=report.model_dump_json())
                db.add(row)
            else:
                row.value = report.model_dump_json()
                row.updated_at = datetime.now(timezone.utc)

    def latest_skill_gap(self) -> SkillGapReport | None:
        with self.session() as db:
            row = db.query(AppSetting).filter(AppSetting.key == "latest_skill_gap").first()
            if not row:
                return None
            return SkillGapReport.model_validate_json(row.value)

    def set_setting(self, key: str, value: str) -> None:
        with self.session() as db:
            row = db.query(AppSetting).filter(AppSetting.key == key).first()
            if row is None:
                row = AppSetting(key=key, value=value)
                db.add(row)
            else:
                row.value = value
                row.updated_at = datetime.now(timezone.utc)

    def get_setting(self, key: str) -> str | None:
        with self.session() as db:
            row = db.query(AppSetting).filter(AppSetting.key == key).first()
            return row.value if row else None

    def count_jobs(self) -> int:
        with self.session() as db:
            return int(db.query(func.count(Job.id)).scalar() or 0)


__all__ = ["DatabaseManager", "Base", "Company", "Job", "Application", "UserProfileModel", "MarketAnalysisModel", "LearningResourceModel", "CareerScoreModel", "AppSetting"]
