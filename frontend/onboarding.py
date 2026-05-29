from __future__ import annotations

import gradio as gr

from backend.models import OnboardingRequest


PROVIDER_OPTIONS = ["OpenAI", "NVIDIA Kimi", "Other OpenAI-compatible API"]



def build_onboarding_tab(service):
    with gr.Column() as onboarding_col:
        gr.Markdown(
            """
            ## Welcome to CareerCrawler
            AI models can improve analysis quality, but they are optional.

            Do you have access to an AI model provider?
            """
        )

        has_provider = gr.Radio(choices=["Yes", "No (Local Analysis Mode)"], value="No (Local Analysis Mode)", label="Provider Access")
        provider = gr.Dropdown(choices=PROVIDER_OPTIONS, label="Provider", value="OpenAI")
        api_key = gr.Textbox(label="API Key", type="password")
        base_url = gr.Textbox(label="Base URL (optional for OpenAI)")
        submit = gr.Button("Save Onboarding")
        status = gr.Textbox(label="Status", interactive=False)

        def _toggle_provider_fields(choice: str):
            visible = choice == "Yes"
            return {
                provider: gr.update(visible=visible),
                api_key: gr.update(visible=visible),
                base_url: gr.update(visible=visible),
            }

        has_provider.change(
            _toggle_provider_fields,
            inputs=[has_provider],
            outputs=[provider, api_key, base_url],
        )

        def _submit(has_choice: str, provider_choice: str, api_key_value: str, base_url_value: str) -> str:
            payload = OnboardingRequest(
                has_provider=has_choice == "Yes",
                provider=provider_choice,
                api_key=api_key_value or None,
                base_url=base_url_value or None,
            )
            result = service.submit_onboarding(payload)
            return f"{result.get('status')}: {result.get('message')}"

        submit.click(
            _submit,
            inputs=[has_provider, provider, api_key, base_url],
            outputs=[status],
        )

    return onboarding_col
