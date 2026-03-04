from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pdfplumber
from docx import Document

from backend.models import SkillGapReport
from backend.utils import unique_preserve_order

try:
    import spacy
except Exception:  # pragma: no cover
    spacy = None


SKILL_DICTIONARY = [
    "python",
    "sql",
    "pandas",
    "numpy",
    "scikit-learn",
    "tensorflow",
    "pytorch",
    "docker",
    "kubernetes",
    "aws",
    "gcp",
    "azure",
    "llm orchestration",
    "vector databases",
    "langchain",
    "fastapi",
    "playwright",
    "airflow",
    "spark",
    "dbt",
]


class SkillGapAnalyzer:
    def __init__(self) -> None:
        self._nlp = self._load_nlp()

    def _load_nlp(self):
        if spacy is None:
            return None
        try:
            return spacy.load("en_core_web_sm")
        except Exception:
            return spacy.blank("en")

    def extract_text_from_cv(self, cv_path: str) -> str:
        path = Path(cv_path)
        if not path.exists():
            raise FileNotFoundError(f"CV file not found: {cv_path}")

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._extract_from_pdf(path)
        if suffix == ".docx":
            return self._extract_from_docx(path)
        return path.read_text(encoding="utf-8", errors="ignore")

    def _extract_from_pdf(self, path: Path) -> str:
        chunks: list[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                chunks.append(text)
        return "\n".join(chunks)

    def _extract_from_docx(self, path: Path) -> str:
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)

    def extract_skills_from_text(self, text: str) -> list[str]:
        lowered = text.lower()
        matched: list[str] = []
        dict_set = {skill.lower() for skill in SKILL_DICTIONARY}

        for skill in SKILL_DICTIONARY:
            if skill in lowered:
                matched.append(skill.title())

        if self._nlp is not None:
            doc = self._nlp(text)
            try:
                for chunk in doc.noun_chunks:
                    normalized = _normalize_token(chunk.text)
                    if normalized in dict_set:
                        matched.append(normalized.title())
            except Exception:
                pass

            for entity in doc.ents if hasattr(doc, "ents") else []:
                normalized = _normalize_token(entity.text)
                if normalized in dict_set:
                    matched.append(normalized.title())

        regex_candidates = re.findall(r"\b[a-zA-Z\+\-]{2,25}\b", text)
        for candidate in regex_candidates:
            norm = candidate.lower()
            if norm in dict_set:
                matched.append(norm.title())

        return unique_preserve_order(matched)

    def analyze(self, user_skills: Iterable[str], market_skills: Iterable[str]) -> SkillGapReport:
        user = unique_preserve_order([s.strip().title() for s in user_skills if s.strip()])
        market = unique_preserve_order([s.strip().title() for s in market_skills if s.strip()])
        user_set = {s.lower() for s in user}

        missing = [skill for skill in market if skill.lower() not in user_set]
        matched = [skill for skill in market if skill.lower() in user_set]
        return SkillGapReport(
            user_skills=user,
            market_skills=market,
            missing_skills=missing,
            matched_skills=matched,
        )



def _normalize_token(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())
