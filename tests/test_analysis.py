from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from reportlab.pdfgen import canvas

from analysis.career_score import CareerScoreCalculator
from analysis.job_ranker import JobRanker
from analysis.market_analysis import MarketAnalyzer
from analysis.skill_gap_analyzer import SkillGapAnalyzer
from backend.models import UserProfile


def test_market_analysis_outputs_expected_sections(sample_jobs):
    analyzer = MarketAnalyzer()
    insights = analyzer.analyze(sample_jobs)

    assert insights.top_demanded_skills
    assert insights.salary_ranges["avg"] is not None
    assert insights.top_hiring_companies
    assert insights.geographic_distribution


def test_job_ranker_score_range(sample_jobs):
    profile = UserProfile(skills=["Python", "Kubernetes"], preferred_domains=["machine learning"])
    ranker = JobRanker()

    ranked = ranker.rank_jobs(sample_jobs, profile)
    assert ranked[0].match_score >= ranked[-1].match_score
    assert all(0.0 <= job.match_score <= 10.0 for job in ranked)


def test_skill_gap_and_career_score(sample_jobs):
    analyzer = SkillGapAnalyzer()
    gap = analyzer.analyze(["Python", "SQL"], ["Python", "Docker", "Kubernetes", "SQL"])

    assert "Docker" in gap.missing_skills
    assert "Python" in gap.matched_skills

    calculator = CareerScoreCalculator()
    report = calculator.calculate(
        avg_job_match_score=7.5,
        matched_skills=len(gap.matched_skills),
        missing_skills=len(gap.missing_skills),
        total_market_skills=len(gap.market_skills),
        years_experience=4,
    )
    assert 0 <= report.score <= 100
    assert report.band in {"Early stage", "Developing profile", "Strong candidate", "Highly competitive"}


def test_cv_parsing_pdf_and_docx(tmp_path: Path):
    pdf_path = tmp_path / "resume.pdf"
    docx_path = tmp_path / "resume.docx"

    c = canvas.Canvas(str(pdf_path))
    c.drawString(72, 720, "Python Docker Kubernetes 5 years of experience")
    c.save()

    doc = Document()
    doc.add_paragraph("FastAPI SQL Airflow 4 years of experience")
    doc.save(str(docx_path))

    analyzer = SkillGapAnalyzer()
    pdf_text = analyzer.extract_text_from_cv(str(pdf_path))
    docx_text = analyzer.extract_text_from_cv(str(docx_path))

    assert "Python" in pdf_text
    assert "FastAPI" in docx_text
