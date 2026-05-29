from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import create_app


def test_health_and_config_endpoint(test_config):
    app = create_app(test_config)
    client = TestClient(app)

    health = client.get("/api/health")
    config = client.get("/api/config")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert config.status_code == 200
    assert config.json()["MODE"] == "development"


def test_scrape_and_analysis_flow(test_config):
    app = create_app(test_config)
    client = TestClient(app)

    scrape = client.post("/api/scrape", json={"domains": ["linkedin", "indeed", "greenhouse", "lever"]})
    assert scrape.status_code == 200
    assert scrape.json()["total_scraped"] > 0

    analysis = client.post("/api/analysis/run")
    assert analysis.status_code == 200
    assert "top_demanded_skills" in analysis.json()


def test_profile_upload_and_pipeline(test_config, tmp_path: Path):
    app = create_app(test_config)
    client = TestClient(app)

    cv_path = tmp_path / "cv.txt"
    cv_path.write_text("Python Docker Kubernetes 6 years of experience", encoding="utf-8")

    with cv_path.open("rb") as handle:
        upload = client.post(
            "/api/profile/upload-cv",
            files={"file": ("cv.txt", handle, "text/plain")},
        )

    assert upload.status_code == 200
    assert "skills" in upload.json()

    linkedin = client.post("/api/profile/linkedin", json={"linkedin_url": "https://www.linkedin.com/in/example"})
    assert linkedin.status_code == 200

    pipeline = client.post(
        "/api/pipeline/run",
        json={"domains": ["linkedin", "indeed"], "linkedin_url": "https://www.linkedin.com/in/example", "preferred_domains": ["machine learning"]},
    )
    assert pipeline.status_code == 200
    data = pipeline.json()
    assert "career_readiness" in data
    assert Path(data["reports"]["jobs_today"]).exists()
    assert Path(data["reports"]["top_jobs"]).exists()


def test_report_download_endpoint(test_config):
    app = create_app(test_config)
    client = TestClient(app)

    client.post("/api/scrape", json={"domains": ["linkedin", "indeed"]})
    client.post("/api/pipeline/run", json={"domains": ["linkedin", "indeed"]})

    resp = client.get("/api/reports/jobs_today.csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
