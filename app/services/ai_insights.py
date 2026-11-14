import json
import os

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

DEFAULT_MODEL = "gpt-5.5"
INSIGHT_INSTRUCTIONS = (
    "You explain personal budget calculations in Thai. Use only the supplied, "
    "precomputed metrics. Do not recalculate, alter, or invent any amount or date. "
    "Explain cash runway and the remaining amount/time for the savings goal when present. "
    "Mention that forecasts are estimates based on historical averages. If a metric is null, "
    "explain that there is not enough positive savings/spending history to estimate it. "
    "Write at most three concise bullet points. Do not recommend investment, credit, tax, "
    "or financial products."
)


class AIConfigurationError(Exception):
    pass


class AIProviderError(Exception):
    pass


def get_ai_config() -> tuple[str | None, str]:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY", "").strip() or None
    model = os.getenv("OPENAI_MODEL", "").strip() or DEFAULT_MODEL
    return api_key, model


def generate_insight(metrics: dict) -> tuple[str, str]:
    api_key, model = get_ai_config()
    if not api_key:
        raise AIConfigurationError("ตั้งค่า OPENAI_API_KEY ก่อนใช้ AI")

    try:
        client = OpenAI(api_key=api_key, timeout=20.0, max_retries=0)
        response = client.responses.create(
            model=model,
            instructions=INSIGHT_INSTRUCTIONS,
            input=json.dumps(metrics, ensure_ascii=False),
            max_output_tokens=250,
            store=False,
        )
    except OpenAIError as error:
        raise AIProviderError("เรียกใช้ AI ไม่สำเร็จ กรุณาลองใหม่ภายหลัง") from error

    insight = response.output_text.strip()
    if not insight:
        raise AIProviderError("AI ยังไม่สามารถสรุปผลได้ กรุณาลองใหม่")
    return insight[:2000], model
