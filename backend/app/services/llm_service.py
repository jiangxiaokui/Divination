from __future__ import annotations

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


def _build_messages(
    module: str,
    question: str | None,
    summary: str,
    cards: list[dict],
    user_context: dict | None = None,
) -> list[dict]:
    card_lines = "\n\n".join(
        f"{index + 1}. {card.get('title', '未命名卡片')}\n{card.get('content', '')}"
        for index, card in enumerate(cards)
    ) or "暂无规则卡片"

    profile = (user_context or {}).get("profile") or {}
    context_lines: list[str] = []
    if (user_context or {}).get("nickname"):
        context_lines.append(f"用户昵称: {user_context['nickname']}")
    if profile.get("city"):
        context_lines.append(f"所在城市: {profile['city']}")
    if profile.get("relationship_status"):
        context_lines.append(f"情感状态: {profile['relationship_status']}")
    if profile.get("tags"):
        context_lines.append(f"关注标签: {'、'.join(str(item) for item in profile['tags'])}")
    recent_questions = (user_context or {}).get("recent_questions") or []
    if recent_questions:
        context_lines.append(f"最近问题: {' / '.join(str(item) for item in recent_questions[:3])}")

    system_prompt = (
        "你是资深命理解读助手。"
        "请基于用户当前问题、已有规则结果和个人上下文做二次解读。"
        "你的回答必须直接回应用户提问，不能只复述通用模板。"
        "第一段先明确回答用户最关心的核心判断，第二段再给出 2-3 条可执行建议。"
        "必须引用规则结果里的关键信号，不得编造不存在的牌面、卦象或设定。"
        "禁止医疗/法律/投资确定性承诺。"
    )

    user_prompt = "\n".join(
        [
            f"模块: {module}",
            f"用户当前问题: {question or '用户没有额外补充问题，请围绕当前模块输入直接解读。'}",
            f"规则引擎摘要: {summary}",
            "规则卡片:",
            card_lines,
            "个人上下文:",
            "\n".join(context_lines) if context_lines else "暂无额外个人上下文",
            "输出要求: 中文 160-260 字，分成“结论”和“建议”两段；结论必须直接回答用户问题。",
        ]
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def enhance_reading(
    module: str,
    question: str | None,
    summary: str,
    cards: list[dict],
    user_context: dict | None = None,
) -> LLMEnhanceResult | None:
    if not settings.llm_enabled or not settings.openai_api_key:
        return None

    client = OpenAI(base_url=settings.openai_base_url, api_key=settings.openai_api_key)
    messages = _build_messages(
        module=module,
        question=question,
        summary=summary,
        cards=cards,
        user_context=user_context,
    )

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
