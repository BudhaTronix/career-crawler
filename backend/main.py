from __future__ import annotations

import logging

import gradio as gr
from fastapi import FastAPI

from automation.scheduler import PipelineScheduler
from backend.api.routes import router as api_router
from backend.models import PipelineRequest
from backend.services import CareerCrawlerService
from config.config_loader import AppConfig, get_runtime_config
from frontend.dashboard import build_dashboard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



def create_app(config_override: AppConfig | None = None) -> FastAPI:
    runtime = get_runtime_config()
    settings = config_override or runtime.settings
    service = CareerCrawlerService(settings)

    base_app = FastAPI(title="CareerCrawler", version="0.1.0")
    base_app.include_router(api_router)
    base_app.state.service = service

    scheduler = PipelineScheduler()

    def _scheduled_pipeline() -> None:
        logger.info("Running scheduled CareerCrawler pipeline")
        service.run_pipeline(PipelineRequest())

    @base_app.on_event("startup")
    def on_startup() -> None:
        scheduler.register(settings.SCHEDULER_CRON, _scheduled_pipeline)
        scheduler.start()
        base_app.state.scheduler = scheduler
        logger.info("Scheduler started with cron '%s'", settings.SCHEDULER_CRON)

    @base_app.on_event("shutdown")
    def on_shutdown() -> None:
        scheduler.shutdown()

    dashboard = build_dashboard(service)
    return gr.mount_gradio_app(base_app, dashboard, path="/")


app = create_app()
