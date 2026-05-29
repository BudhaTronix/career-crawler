from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from backend.models import AutoApplyRequest, LinkedInInput, OnboardingRequest, PipelineRequest, ScrapeRequest

router = APIRouter(prefix="/api", tags=["career-crawler"])



def _service(request: Request):
    return request.app.state.service


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/config")
def config_snapshot(request: Request):
    return _service(request).get_config_snapshot()


@router.post("/onboarding/submit")
def submit_onboarding(payload: OnboardingRequest, request: Request):
    return _service(request).submit_onboarding(payload)


@router.post("/scrape")
def scrape(payload: ScrapeRequest, request: Request):
    return _service(request).scrape_jobs(payload.domains)


@router.get("/jobs")
def list_jobs(request: Request, limit: int = 200):
    return _service(request).list_jobs(limit=limit)


@router.post("/analysis/run")
def run_analysis(request: Request):
    return _service(request).run_market_analysis()


@router.get("/analysis/latest")
def latest_analysis(request: Request):
    return _service(request).latest_market_analysis()


@router.post("/profile/upload-cv")
async def upload_cv(request: Request, file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".pdf", ".docx", ".txt"}:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF, DOCX, or TXT.")

    uploads_dir = Path("reports") / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    dest = uploads_dir / file.filename

    content = await file.read()
    dest.write_bytes(content)

    return _service(request).save_user_cv(str(dest))


@router.post("/profile/linkedin")
def save_linkedin(payload: LinkedInInput, request: Request):
    return _service(request).save_linkedin_url(str(payload.linkedin_url))


@router.get("/skill-gap")
def skill_gap(request: Request):
    return _service(request).get_latest_skill_gap()


@router.get("/recommendations")
def recommendations(request: Request):
    return _service(request).get_learning_resources()


@router.get("/career-score")
def career_score(request: Request):
    return _service(request).get_latest_career_score()


@router.post("/pipeline/run")
def pipeline(payload: PipelineRequest, request: Request):
    return _service(request).run_pipeline(payload)


@router.post("/auto-apply/run")
def auto_apply(payload: AutoApplyRequest, request: Request):
    return _service(request).run_auto_apply(payload.resume_path, payload.limit)


@router.get("/reports/{name}")
def download_report(name: str, request: Request):
    if name not in {"jobs_today.csv", "top_jobs.csv"}:
        raise HTTPException(status_code=404, detail="Report not found")

    config = _service(request).config
    report_path = Path(config.REPORTS_DIR) / name
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not generated yet")

    return FileResponse(report_path)
