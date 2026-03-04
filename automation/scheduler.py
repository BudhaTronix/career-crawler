from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


class PipelineScheduler:
    JOB_ID = "daily_career_pipeline"

    def __init__(self) -> None:
        self.scheduler = BackgroundScheduler(timezone="UTC")

    def register(self, cron_expr: str, callback) -> None:
        minute, hour, day, month, day_of_week = cron_expr.split()
        trigger = CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week)

        self.scheduler.add_job(callback, trigger, id=self.JOB_ID, replace_existing=True)

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
