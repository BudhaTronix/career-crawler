from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import seaborn as sns

from backend.models import MarketInsights


class MarketDashboardBuilder:
    def __init__(self, reports_dir: str) -> None:
        self.reports_dir = Path(reports_dir)
        self.plots_dir = self.reports_dir / "plots"
        self.plots_dir.mkdir(parents=True, exist_ok=True)

    def build(self, insights: MarketInsights) -> dict[str, object]:
        figures: dict[str, object] = {}
        figures["skill_heatmap"] = self._skill_heatmap(insights)
        figures["top_companies_chart"] = self._top_companies_chart(insights)
        figures["salary_distribution_chart"] = self._salary_distribution_chart(insights)
        figures["skill_trend_chart"] = self._skill_trend_chart(insights)
        figures["hiring_timeline_chart"] = self._hiring_timeline_chart(insights)

        self._save_static_snapshot(insights)
        return figures

    def _skill_heatmap(self, insights: MarketInsights):
        if not insights.top_demanded_skills:
            return px.imshow([[0]], x=["No data"], y=["No data"], title="Skill Demand Heatmap")

        df = pd.DataFrame(insights.top_demanded_skills)
        return px.density_heatmap(
            df,
            x="skill",
            y="count",
            z="count",
            title="Skill Demand Heatmap",
            color_continuous_scale="Viridis",
        )

    def _top_companies_chart(self, insights: MarketInsights):
        df = pd.DataFrame(insights.top_hiring_companies)
        if df.empty:
            return px.bar(title="Top Hiring Companies")
        return px.bar(df, x="company", y="count", title="Top Hiring Companies", color="count")

    def _salary_distribution_chart(self, insights: MarketInsights):
        salary_info = insights.salary_ranges
        if not salary_info or salary_info.get("avg") is None:
            return px.histogram(title="Salary Distribution")
        values = [salary_info.get("min"), salary_info.get("median"), salary_info.get("avg"), salary_info.get("max")]
        df = pd.DataFrame({"salary": [v for v in values if v is not None]})
        return px.histogram(df, x="salary", nbins=8, title="Salary Distribution")

    def _skill_trend_chart(self, insights: MarketInsights):
        df = pd.DataFrame(insights.skill_trend_over_time)
        if df.empty:
            return px.line(title="Skill Demand Trend")
        return px.line(df, x="date", y="count", color="skill", title="Skill Demand Trend")

    def _hiring_timeline_chart(self, insights: MarketInsights):
        df = pd.DataFrame(insights.hiring_activity_timeline)
        if df.empty:
            return px.line(title="Hiring Activity Timeline")
        y_col = "smoothed_count" if "smoothed_count" in df.columns else "count"
        return px.line(df, x="date", y=y_col, title="Hiring Activity Timeline")

    def _save_static_snapshot(self, insights: MarketInsights) -> None:
        if not insights.top_demanded_skills:
            return

        df = pd.DataFrame(insights.top_demanded_skills).head(15)
        plt.figure(figsize=(10, 6))
        sns.barplot(data=df, x="count", y="skill", palette="mako")
        plt.title("Top Skill Demand")
        plt.tight_layout()
        plt.savefig(self.plots_dir / "top_skill_demand.png")
        plt.close()
