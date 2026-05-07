from __future__ import annotations

import json
from time import perf_counter
from openai import OpenAI

from app.core.config import get_settings

settings = get_settings()


class LLMEnhanceResult:
    def __init__(self, content: str, prompt_tokens: int | None, completion_tokens: int | None, latency_ms: int):
        self.content = content
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.latency_ms = latency_ms


def _build_messages(module: str, question: str | None, summary: str, cards: list[dict]) -> list[dict]:
    system_prompt = (
        "你是资深命理解读助手。"
        "请基于用户问题和已有规则结果做二次解读，"
        "必须保持克制、清晰、可执行，禁止医疗/法律/投资确定性承诺。"
    )

    user_payload = {
        "module": module,
        "question": question,
        "summary": summary,
        "cards": cards,
        "output_requirements": "输出中文 120-220 字，分为结论与建议两段。",
    }

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]


def enhance_reading(module: str, question: str | None, summary: str, cards: list[dict]) -> LLMEnhanceResult | None:
    if not settings.llm_enabled or not settings.openai_api_key:
        return None

    client = OpenAI(base_url=settings.openai_base_url, api_key=settings.openai_api_key)
    messages = _build_messages(module=module, question=question, summary=summary, cards=cards)

    start = perf_counter()
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        temperature=0.6,
        max_tokens=settings.llm_max_tokens,
        timeout=settings.llm_timeout_seconds,
    )
    latency_ms = int((perf_counter() - start) * 1000)

    content = (response.choices[0].message.content or "").strip()
    usage = response.usage

    return LLMEnhanceResult(
        content=content,
        prompt_tokens=(usage.prompt_tokens if usage else None),
        completion_tokens=(usage.completion_tokens if usage else None),
        latency_ms=latency_ms,
    )
