from __future__ import annotations

from pathlib import Path

import gradio as gr
import pandas as pd

from backend.models import PipelineRequest
from frontend.onboarding import build_onboarding_tab



def build_dashboard(service):
    config = service.get_config_snapshot()
    mode = config["MODE"]
    external = config["ENABLE_EXTERNAL_SCRAPING"]
    onboarding_complete = config.get("ONBOARDING_COMPLETE", False)

    with gr.Blocks(title="CareerCrawler") as demo:
        gr.Markdown(
            f"""
            # CareerCrawler Dashboard
            **Mode**: `{mode}`
            
            **External Scraping Enabled**: `{external}`
            
            **Onboarding Complete**: `{onboarding_complete}`
            """
        )

        with gr.Tab("Onboarding"):
            build_onboarding_tab(service)

        with gr.Tab("Job Discovery"):
            domains = gr.CheckboxGroup(
                choices=["linkedin", "indeed", "greenhouse", "lever"],
                value=["linkedin", "indeed", "greenhouse", "lever"],
                label="Job Sources",
            )
            scrape_btn = gr.Button("Scrape Latest Jobs")
            scrape_summary = gr.JSON(label="Scrape Summary")
            jobs_df = gr.Dataframe(label="Job Listings", wrap=True)

            def _run_scrape(selected_domains: list[str]):
                result = service.scrape_jobs(selected_domains)
                jobs = pd.DataFrame(result["jobs"])
                if not jobs.empty:
                    display_cols = [
                        "title",
                        "company",
                        "location",
                        "salary_estimate",
                        "match_score",
                        "date_posted",
                        "job_url",
                    ]
                    jobs = jobs[display_cols]
                return result, jobs

            scrape_btn.click(_run_scrape, inputs=[domains], outputs=[scrape_summary, jobs_df])

        with gr.Tab("Profile"):
            cv_file = gr.File(label="Upload CV (PDF/DOCX/TXT)")
            linkedin_input = gr.Textbox(label="LinkedIn Profile URL")
            preferred_domains = gr.Textbox(label="Preferred Domains (comma separated)", value="machine learning, ai")
            profile_btn = gr.Button("Update Profile")
            profile_out = gr.JSON(label="Profile")

            def _update_profile(cv_obj, linkedin_url: str):
                latest = None
                if cv_obj is not None:
                    latest = service.save_user_cv(cv_obj.name)
                if linkedin_url.strip():
                    latest = service.save_linkedin_url(linkedin_url.strip())
                return latest or service.db.get_user_profile().model_dump(mode="json")

            profile_btn.click(_update_profile, inputs=[cv_file, linkedin_input], outputs=[profile_out])

        with gr.Tab("Pipeline"):
            run_btn = gr.Button("Run Full Pipeline")
            pipeline_out = gr.JSON(label="Pipeline Output")
            auto_apply_toggle = gr.Checkbox(label="Auto Apply Toggle (display only)", value=config["AUTO_APPLY"])

            def _run_pipeline(domain_list: list[str], linkedin_url: str, pref_domains: str):
                payload = PipelineRequest(
                    domains=domain_list,
                    linkedin_url=linkedin_url.strip() or None,
                    preferred_domains=[item.strip() for item in pref_domains.split(",") if item.strip()],
                )
                result = service.run_pipeline(payload)
                return result

            run_btn.click(
                _run_pipeline,
                inputs=[domains, linkedin_input, preferred_domains],
                outputs=[pipeline_out],
            )

        with gr.Tab("Insights"):
            analysis_btn = gr.Button("Refresh Market Analysis")
            analysis_out = gr.JSON(label="Market Analysis")
            gap_btn = gr.Button("Compute Skill Gap")
            gap_out = gr.JSON(label="Skill Gap")
            rec_btn = gr.Button("Get Learning Recommendations")
            rec_out = gr.JSON(label="Learning Recommendations")
            score_btn = gr.Button("Calculate Career Readiness")
            score_out = gr.JSON(label="Career Readiness Score")

            skill_heatmap_plot = gr.Plot(label="Skill Demand Heatmap")
            top_companies_plot = gr.Plot(label="Top Hiring Companies")
            salary_plot = gr.Plot(label="Salary Distribution")
            trend_plot = gr.Plot(label="Skill Trend")
            timeline_plot = gr.Plot(label="Hiring Timeline")

            def _refresh_analysis():
                analysis_data = service.run_market_analysis()
                insights = service.db.latest_market_analysis()
                figures = service.dashboard_builder.build(insights) if insights else {}
                return (
                    analysis_data,
                    figures.get("skill_heatmap"),
                    figures.get("top_companies_chart"),
                    figures.get("salary_distribution_chart"),
                    figures.get("skill_trend_chart"),
                    figures.get("hiring_timeline_chart"),
                )

            analysis_btn.click(
                _refresh_analysis,
                outputs=[
                    analysis_out,
                    skill_heatmap_plot,
                    top_companies_plot,
                    salary_plot,
                    trend_plot,
                    timeline_plot,
                ],
            )
            gap_btn.click(lambda: service.compute_skill_gap(), outputs=[gap_out])
            rec_btn.click(lambda: service.recommend_learning_resources(), outputs=[rec_out])
            score_btn.click(lambda: service.calculate_career_readiness(), outputs=[score_out])

        with gr.Tab("Reports"):
            export_btn = gr.Button("Generate CSV Reports")
            reports_out = gr.JSON(label="Generated Files")
            jobs_today_file = gr.File(label="jobs_today.csv")
            top_jobs_file = gr.File(label="top_jobs.csv")

            def _export_reports():
                files = service.export_reports()
                jobs_path = Path(files["jobs_today"]).resolve()
                top_path = Path(files["top_jobs"]).resolve()
                return files, str(jobs_path), str(top_path)

            export_btn.click(_export_reports, outputs=[reports_out, jobs_today_file, top_jobs_file])

    return demo
