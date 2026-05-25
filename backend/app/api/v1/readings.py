import json
import logging
import random
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.user_auth import UserSession, get_optional_user
from app.db.session import get_db
from app.models.divination_record import DivinationRecord
from app.models.divination_session import DivinationSession
from app.models.llm_call_log import LLMCallLog
from app.models.user import User
from app.schemas.reading import ReadingCreate, ReadingOut, ResultCard
from app.services.llm_service import enhance_reading
from app.services import kb_service

router = APIRouter(prefix="/readings", tags=["readings"])
settings = get_settings()
logger = logging.getLogger(__name__)

ALLOWED_MODULES = {
    "bazi",
    "dream",
    "compatibility",
    "liuyao",
    "name_wuge",
    "tarot",
    "lot_guanyin",
    "lot_yuelao",
    "lot_generic",
}


def _sum_text(value: str) -> int:
    return sum(ord(ch) for ch in value)


def _parse_iso_dt(value: str) -> datetime | None:
    if not value:
        return None

    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _month_element(month: int) -> str:
    if month in (2, 3, 4):
        return "木旺"
    if month in (5, 6, 7):
        return "火旺"
    if month in (8, 9, 10):
        return "金旺"
    if month in (11, 12, 1):
        return "水旺"
    return "土旺"


def _hour_branch(hour: int) -> str:
    branches = [
        "子",
        "丑",
        "丑",
        "寅",
        "寅",
        "卯",
        "卯",
        "辰",
        "辰",
        "巳",
        "巳",
        "午",
        "午",
        "未",
        "未",
        "申",
        "申",
        "酉",
        "酉",
        "戌",
        "戌",
        "亥",
        "亥",
        "子",
    ]
    return branches[hour]


def _tone_from_score(score: int) -> tuple[str, str]:
    if score >= 75:
        return "吉势偏强", "advice"
    if score >= 55:
        return "稳中有进", "neutral"
    return "先守后攻", "info"


def _kb_judgment(db: Session | None, module: str, label: str, fallback: str) -> str:
    """优先从数据库知识库取判断文本，取不到则用 fallback。"""
    if db is None:
        return fallback
    text = kb_service.get_content(db, module=module, category="命势判断", keyword=label)
    if text:
        return text
    text = kb_service.search_content(db, module=module, keyword=label)
    return text or fallback


def _short_question(question: str | None, limit: int = 32) -> str | None:
    if not question:
        return None
    compact = " ".join(question.strip().split())
    if not compact:
        return None
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 1]}…"


def _build_question_focus_card(question: str | None) -> ResultCard | None:
    short_question = _short_question(question, limit=120)
    if not short_question:
        return None
    return ResultCard(
        title="本次问题聚焦",
        content=f"你这次最想解决的是: {short_question}",
        tone="info",
    )


def _sse_pack(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _build_user_context(user: User | None, db: Session | None) -> dict | None:
    if user is None or db is None:
        return None

    recent_sessions = db.scalars(
        select(DivinationSession)
        .where(DivinationSession.user_id == user.id)
        .order_by(DivinationSession.created_at.desc(), DivinationSession.id.desc())
        .limit(3)
    ).all()

    return {
        "nickname": user.nickname,
        "profile": user.profile_payload or {},
        "recent_questions": [session.question for session in recent_sessions if session.question],
        "recent_categories": [session.category for session in recent_sessions],
    }


def _append_user_context_card(cards: list[ResultCard], user_context: dict | None) -> list[ResultCard]:
    if not user_context:
        return cards

    profile = user_context.get("profile") or {}
    hints: list[str] = []
    if user_context.get("nickname"):
        hints.append(f"当前用户: {user_context['nickname']}")
    if profile.get("city"):
        hints.append(f"所在城市: {profile['city']}")
    if profile.get("relationship_status"):
        hints.append(f"情感状态: {profile['relationship_status']}")
    tags = profile.get("tags")
    if isinstance(tags, list) and tags:
        hints.append(f"关注标签: {'、'.join(str(tag) for tag in tags[:4])}")
    recent_questions = user_context.get("recent_questions") or []
    if recent_questions:
        hints.append(f"最近提问: {' / '.join(str(item) for item in recent_questions[:2])}")

    if not hints:
        return cards

    return cards + [ResultCard(title="个人上下文参考", content="\n".join(hints), tone="info")]


def _build_module_cards(module: str, payload: ReadingCreate, db: Session | None = None) -> tuple[str, str, list[ResultCard]]:
    data = payload.input_payload

    if module == "dream":
        dream_text = (data.get("dream_text") or payload.question or "").strip()
        emotion = data.get("emotion", "mixed")
        recent_focus = data.get("recent_focus", "综合")
        question_hint = _short_question(payload.question, limit=42)
        symbols = [token.strip() for token in str(data.get("symbols", "")).split("，") if token.strip()]
        if not dream_text:
            dream_text = "梦境内容未填写，系统将按近期状态做象征性解读。"

        seed = _sum_text(dream_text + emotion + recent_focus + "".join(symbols))
        score = 42 + (seed % 49)
        final_label, final_tone = _tone_from_score(score)

        symbol_keywords = symbols[:3] or [dream_text[:6] or "梦境"]
        symbol_desc = []
        if db:
            for keyword in symbol_keywords:
                hit = kb_service.search_content(db, module="dream", keyword=keyword)
                if hit:
                    symbol_desc.append(f"【{keyword}】{hit}")

        cards = [
            ResultCard(
                title="梦境速描",
                content=f"情绪底色: {emotion}\n近期关注: {recent_focus}\n象征关键词: {', '.join(symbols) if symbols else '待系统提取'}",
                tone="info",
            ),
            ResultCard(
                title="潜意识映射",
                content="\n\n".join(symbol_desc)
                or f"这段梦更像是在放大你对“{recent_focus}”的悬念与期待。若梦里反复出现追逐、坠落、错过，通常对应现实中的节奏失控感。",
                tone="neutral",
            ),
            ResultCard(
                title="当下提示",
                content=(
                    f"结论: {final_label}。"
                    f"{f' 围绕“{question_hint}”，' if question_hint else ' '}"
                    "先记录最近 3 天触发你情绪波动的人和事，再对照梦中重复出现的场景，你会更快找到真正的焦点。"
                ),
                tone=final_tone,
            ),
        ]
        return "梦境解析", f"梦境解析完成，当前信号为: {final_label}。", cards

    if module == "compatibility":
        focus = data.get("focus", "relationship")
        person_a = (data.get("person_a") or "甲方").strip()
        person_b = (data.get("person_b") or "乙方").strip()
        relation_stage = data.get("relation_stage", "暧昧观察")
        concern = (payload.question or data.get("concern") or "").strip()
        seed = _sum_text(person_a + person_b + relation_stage + concern + focus)
        score = 38 + (seed % 57)
        final_label, final_tone = _tone_from_score(score)

        dynamic_text = "你们之间的连接感存在，但推进方式比结果更关键。"
        if score >= 75:
            dynamic_text = "双方节奏相对同频，适合把关系从试探推进到明确表达。"
        elif score < 55:
            dynamic_text = "当前更像是一方偏热、一方偏慢，过度追问容易透支关系弹性。"

        kb_text = ""
        if db:
            kb_text = kb_service.search_content(db, module="compatibility", keyword=relation_stage)

        cards = [
            ResultCard(
                title="关系盘面",
                content=f"对象 A: {person_a}\n对象 B: {person_b}\n阶段: {relation_stage}\n主题: {focus}",
                tone="info",
            ),
            ResultCard(
                title="缘分走势",
                content=kb_text or dynamic_text,
                tone="neutral",
            ),
            ResultCard(
                title="相处建议",
                content=f"结论: {final_label}。建议先统一期待，再决定是否升级承诺；最忌在信息不足时要求对方立刻给答案。",
                tone=final_tone,
            ),
        ]
        return "姻缘合盘", f"姻缘合盘完成，当前关系判断为: {final_label}。", cards

    if module == "bazi":
        birth_raw = data.get("birth_datetime", "")
        birth_place = data.get("birth_place") or "未填写"
        gender = data.get("gender", "未填写")
        dt = _parse_iso_dt(birth_raw)

        month = dt.month if dt else 0
        hour = dt.hour if dt else 12
        season_element = _month_element(month if month else 6)
        hour_zhi = _hour_branch(hour)

        question = payload.question or ""
        score = 50 + (_sum_text(question + birth_raw) % 41)
        final_label, final_tone = _tone_from_score(score)

        # 优先从知识库取五行含义和命势判断
        element_key = season_element.replace("旺", "")
        element_desc = kb_service.get_content(db, module="bazi", category="五行旺衰", keyword=season_element) if db else ""
        judgment_desc = _kb_judgment(db, "bazi", final_label, f"当前命势评分: {score}/100。你近期更适合先做积累与布局，再在窗口期主动推进。")
        # 取时支知识
        zhi_desc = kb_service.get_content(db, module="bazi", category="地支", keyword=hour_zhi) if db else ""
        overview_extra = f"\n【{hour_zhi}时支释义】{zhi_desc}" if zhi_desc else ""

        cards = [
            ResultCard(
                title="命盘速览",
                content=f"季节五行倾向: {season_element}\n时支: {hour_zhi}时\n性别: {gender}\n出生地: {birth_place}{overview_extra}",
                tone="info",
            ),
            ResultCard(
                title="五行解析",
                content=element_desc or f"五行倾向: {season_element}，详细解析请开启深度模式。",
                tone="neutral",
            ),
            ResultCard(
                title="核心判断",
                content=judgment_desc,
                tone="neutral",
            ),
            ResultCard(
                title="最终结果",
                content=f"结论: {final_label}。",
                tone=final_tone,
            ),
        ]
        return "八字命理测算", f"八字测算完成，结论为: {final_label}。", cards

    if module == "liuyao":
        question_type = data.get("question_type", "综合")
        method = data.get("casting_method", "coin")
        raw_lines = data.get("line_values", [])
        lines = [int(v) for v in raw_lines if str(v).isdigit() and int(v) in (6, 7, 8, 9)]
        if len(lines) != 6:
            seed = _sum_text((payload.question or "") + question_type)
            lines = [6 + ((seed >> i) % 4) for i in range(6)]

        moving = sum(1 for v in lines if v in (6, 9))
        yang = sum(1 for v in lines if v in (7, 9))
        score = 45 + yang * 6 + (3 - abs(3 - moving)) * 7
        final_label, final_tone = _tone_from_score(score)

        # 动爻知识库
        if moving == 0:
            moving_desc = kb_service.get_content(db, module="liuyao", category="动爻", keyword="无动爻") if db else ""
        elif moving <= 2:
            moving_desc = kb_service.get_content(db, module="liuyao", category="动爻", keyword="一爻动") if db else ""
        else:
            moving_desc = kb_service.get_content(db, module="liuyao", category="动爻", keyword="多爻动") if db else ""
        if score >= 75:
            jixiong_key = "大吉"
        elif score >= 60:
            jixiong_key = "小吉"
        elif score >= 45:
            jixiong_key = "平"
        else:
            jixiong_key = "凶"
        jixiong_desc = kb_service.get_content(db, module="liuyao", category="吉凶判断", keyword=jixiong_key) if db else ""

        cards = [
            ResultCard(
                title="卦象输入",
                content=f"问题类型: {question_type}\n起卦方式: {method}\n六爻: {lines}",
                tone="info",
            ),
            ResultCard(
                title="动静分析",
                content=(moving_desc or f"动爻数量: {moving}，阳爻数量: {yang}，变化{'较快' if moving >= 3 else '较缓'}。"),
                tone="neutral",
            ),
            ResultCard(
                title="吉凶判断",
                content=jixiong_desc or f"综合评分: {score}/100，结论: {jixiong_key}。",
                tone=final_tone,
            ),
            ResultCard(
                title="最终结果",
                content=f"结论: {final_label}。当前事项以“边观察边推进”为佳，避免一次性押注。",
                tone=final_tone,
            ),
        ]
        return "六爻占卜", f"六爻占断完成，结论为: {final_label}。", cards

    if module == "name_wuge":
        full_name = data.get("full_name", "")
        if not full_name:
            full_name = "无名"
        gender = data.get("gender", "未填写")
        script = data.get("script_type", "simplified")

        values = [ord(ch) % 30 + 1 for ch in full_name]
        tian = 1 + (values[0] if values else 1)
        ren = (values[0] if values else 1) + (values[1] if len(values) > 1 else 1)
        di = sum(values[1:]) + 1 if len(values) > 1 else (values[0] + 1)
        wai = (tian + di - ren) or 1
        zong = sum(values)

        score = 40 + (zong % 51)
        final_label, final_tone = _tone_from_score(score)

        # 五格知识库
        tian_desc = kb_service.get_content(db, module="name_wuge", category="五格解析", keyword="天格") if db else ""
        ren_desc = kb_service.get_content(db, module="name_wuge", category="五格解析", keyword="人格") if db else ""
        di_desc = kb_service.get_content(db, module="name_wuge", category="五格解析", keyword="地格") if db else ""
        # 数理吉凶知识库
        ren_shuli = kb_service.search_content(db, module="name_wuge", keyword=str(ren)) if db else ""

        cards = [
            ResultCard(
                title="五格数理",
                content=f"天格: {tian}\n人格: {ren}\n地格: {di}\n外格: {wai}\n总格: {zong}",
                tone="info",
            ),
            ResultCard(
                title="五格释义",
                content=(tian_desc or "天格：先天祖业运") + "\n\n" + (ren_desc or "人格：命运核心") + "\n\n" + (di_desc or "地格：晚年及子女"),
                tone="neutral",
            ),
            ResultCard(
                title="结构评估",
                content=(ren_shuli or f"综合评分: {score}/100") + f"\n姓名: {full_name}\n性别: {gender}",
                tone="neutral",
            ),
            ResultCard(
                title="最终结果",
                content=f"结论: {final_label}。该名字整体气场{'更偏稳健' if score < 70 else '有上扬势能'}。",
                tone=final_tone,
            ),
        ]
        return "姓名学五格", f"姓名学分析完成，结论为: {final_label}。", cards

    if module == "tarot":
        spread = data.get("spread", "three_card")
        orientation = bool(data.get("allow_reversed", True))
        theme = data.get("question_type", "综合")
        question_hint = _short_question(payload.question, limit=42)

        tarot_pool = [
            ("太阳", "积极成长，信心增强"),
            ("星星", "愿景回归，逐步好转"),
            ("战车", "行动力提升，需聚焦目标"),
            ("正义", "权衡利弊，讲求平衡"),
            ("节制", "循序渐进，避免过度"),
            ("愚者", "新阶段开启，勇于尝试"),
            ("魔法师", "意志显现，主动出击"),
            ("女祭司", "直觉敏锐，内省智慧"),
            ("皇后", "丰盛创造，感性滋养"),
            ("皇帝", "权威稳定，领导结构"),
            ("力量", "勇气耐心，内在力量"),
            ("命运之轮", "命运转折，关键时机"),
            ("死神", "结束转化，旧阶段终结"),
            ("审判", "觉醒召唤，重要决定"),
            ("世界", "完成整合，新循环开始"),
            ("恋人", "关系选择，价值对齐"),
            ("隐士", "向内回看，寻找真正答案"),
            ("倒吊人", "暂停换角度，别急着下判断"),
            ("恶魔", "执念束缚，先看清依赖点"),
            ("高塔", "旧结构震动，倒逼重新调整"),
            ("月亮", "情绪起伏，信息尚未完全明朗"),
            ("教皇", "回到原则，重视长期秩序"),
        ]
        draw_count = 1 if spread == "single_card" else (10 if spread == "celtic_cross" else 3)
        seed = _sum_text((payload.question or "") + spread + theme)

        rng = random.Random(seed)
        shuffled_pool = tarot_pool[:]
        rng.shuffle(shuffled_pool)
        drawn = []
        for i, (card_name, card_meaning) in enumerate(shuffled_pool[:draw_count]):
            reversed_flag = orientation and (rng.random() >= 0.5)
            drawn.append((card_name, card_meaning, reversed_flag))

        position_labels_map = {
            "single_card": ["核心指引"],
            "three_card": ["过去", "现在", "未来"],
            "celtic_cross": [
                "现状",
                "阻力",
                "显性目标",
                "潜在基础",
                "近期过去",
                "近期发展",
                "你的位置",
                "外部环境",
                "希望与担忧",
                "最终走向",
            ],
        }
        position_labels = position_labels_map.get(spread, [f"第{i + 1}张" for i in range(draw_count)])

        positive = sum(1 for _, _, rev in drawn if not rev)
        score = 45 + int((positive / max(draw_count, 1)) * 45)
        final_label, final_tone = _tone_from_score(score)

        cards = [
            ResultCard(
                title="牌阵参数",
                content=(
                    f"牌阵: {spread}\n允许逆位: {orientation}\n主题: {theme}"
                    + (f"\n咨询重点: {question_hint}" if question_hint else "")
                ),
                tone="info",
            )
        ]
        for i, (name, meaning, rev) in enumerate(drawn):
            kb_desc = kb_service.get_content(db, module="tarot", category="大阿卡纳", keyword=name) if db else ""
            pos_label = "逆位" if rev else "正位"
            position_label = position_labels[i] if i < len(position_labels) else f"第{i + 1}张"
            detail_text = kb_desc or meaning
            direction_hint = "逆位提示: 当前能量受阻，建议先处理卡点。" if rev else "正位提示: 这张牌的能量可以顺势放大。"
            cards.append(
                ResultCard(
                    title=f"{position_label} · {name} {pos_label}",
                    content=f"{detail_text}\n{direction_hint}",
                    tone="neutral",
                )
            )

        cards.append(
            ResultCard(
                title="最终结果",
                content=(
                    f"结论: {final_label}。"
                    f"{f' 围绕“{question_hint}”，' if question_hint else ' ' }"
                    "建议将重心放在你最可控的下一步行动上，先确认当前最该推进的是判断、沟通还是行动。"
                ),
                tone=final_tone,
            ),
        )
        return "塔罗占卜", f"塔罗解读完成，结论为: {final_label}。", cards

    cards = [
        ResultCard(title="输入已接收", content="系统已收到占卜参数。", tone="neutral"),
    ]
    return "占卜请求", "请求已受理。", cards


def _apply_deep_reading(
    module: str,
    payload: ReadingCreate,
    summary: str,
    cards: list[ResultCard],
    user_context: dict | None = None,
) -> tuple[str, list[ResultCard], object | None]:
    llm_result = None

    if payload.reading_mode == "deep":
        try:
            llm_result = enhance_reading(
                module=module,
                question=payload.question,
                summary=summary,
                cards=[c.model_dump() for c in cards],
                user_context=user_context,
            )
            if llm_result and llm_result.content:
                cards.append(ResultCard(title="深度解读", content=llm_result.content, tone="advice"))
                summary = f"{summary} 已生成深度解读。"
        except Exception as exc:
            logger.warning("deep reading LLM call failed: %s: %s", type(exc).__name__, exc)
            cards.append(ResultCard(title="深度解读", content="当前无法生成深度解读，已返回极速结果。", tone="info"))

    return summary, cards, llm_result


def _persist_reading(
    module: str,
    payload: ReadingCreate,
    headline: str,
    summary: str,
    cards: list[ResultCard],
    llm_result: object | None,
    db: Session | None,
) -> ReadingOut:
    if not settings.db_persistence_enabled:
        return ReadingOut(
            session_id=0,
            record_id=0,
            module=module,
            created_at=datetime.now(),
            headline=headline,
            summary=summary,
            cards=cards,
        )

    if payload.user_id is not None:
        user = db.get(User, payload.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="user not found")

    session = DivinationSession(
        user_id=payload.user_id,
        category=module,
        question=payload.question,
        client_meta=payload.client_meta,
    )
    db.add(session)
    db.flush()

    record = DivinationRecord(
        session_id=session.id,
        module=module,
        input_payload=payload.model_dump(),
        calc_result={"status": "pending_engine", "cards": [c.model_dump() for c in cards]},
        final_text=summary,
        confidence_level="low",
    )
    db.add(record)
    db.flush()

    if llm_result is not None:
        llm_log = LLMCallLog(
            record_id=record.id,
            provider="openai-compatible",
            model=settings.openai_model,
            prompt_tokens=llm_result.prompt_tokens,
            completion_tokens=llm_result.completion_tokens,
            latency_ms=llm_result.latency_ms,
            request_payload_masked={"module": module, "reading_mode": payload.reading_mode},
            response_payload={"content": llm_result.content},
        )
        db.add(llm_log)

    db.commit()
    db.refresh(record)

    return ReadingOut(
        session_id=session.id,
        record_id=record.id,
        module=module,
        created_at=record.created_at or datetime.now(),
        headline=headline,
        summary=summary,
        cards=cards,
    )


def _execute_reading(module: str, payload: ReadingCreate, db: Session | None) -> ReadingOut:
    if module not in ALLOWED_MODULES:
        raise HTTPException(status_code=400, detail=f"unsupported module: {module}")

    user = db.get(User, payload.user_id) if (db is not None and payload.user_id is not None) else None
    user_context = _build_user_context(user, db)
    headline, summary, cards = _build_module_cards(module, payload, db)
    question_card = _build_question_focus_card(payload.question)
    if question_card is not None:
        cards = [question_card, *cards]
        summary = f"{summary} 当前聚焦问题: {_short_question(payload.question, limit=28)}。"
    cards = _append_user_context_card(cards, user_context)
    if user_context:
        summary = f"{summary} 已参考你的个人档案与最近记录。"
    summary, cards, llm_result = _apply_deep_reading(module, payload, summary, cards, user_context=user_context)
    return _persist_reading(module, payload, headline, summary, cards, llm_result, db)


@router.post("/{module}", response_model=ReadingOut)
def create_reading(
    module: str,
    payload: ReadingCreate,
    current_user: UserSession | None = Depends(get_optional_user),
    db: Session | None = Depends(get_db),
) -> ReadingOut:
    if current_user is not None:
        payload.user_id = current_user.user_id
    return _execute_reading(module, payload, db)


@router.post("/{module}/stream")
async def stream_reading(
    module: str,
    payload: ReadingCreate,
    current_user: UserSession | None = Depends(get_optional_user),
    db: Session | None = Depends(get_db),
) -> StreamingResponse:
    if module not in ALLOWED_MODULES:
        raise HTTPException(status_code=400, detail=f"unsupported module: {module}")

    if current_user is not None:
        payload.user_id = current_user.user_id

    async def event_generator():
        try:
            yield _sse_pack("stage", {"message": "请求已接收，正在构建基础盘面…", "module": module})
            user = db.get(User, payload.user_id) if (db is not None and payload.user_id is not None) else None
            user_context = _build_user_context(user, db)
            headline, summary, cards = _build_module_cards(module, payload, db)
            cards = _append_user_context_card(cards, user_context)
            if user_context:
                summary = f"{summary} 已参考你的个人档案与最近记录。"

            partial_cards: list[ResultCard] = []
            for index, card in enumerate(cards, start=1):
                partial_cards.append(card)
                yield _sse_pack(
                    "card",
                    {
                        "step": index,
                        "headline": headline,
                        "summary": summary,
                        "module": module,
                        "cards": [item.model_dump() for item in partial_cards],
                    },
                )

            llm_result = None
            if payload.reading_mode == "deep":
                yield _sse_pack("stage", {"message": "正在生成深度解读…", "module": module})
                summary, cards, llm_result = _apply_deep_reading(module, payload, summary, cards, user_context=user_context)
                if cards:
                    yield _sse_pack(
                        "card",
                        {
                            "step": len(cards),
                            "headline": headline,
                            "summary": summary,
                            "module": module,
                            "cards": [item.model_dump() for item in cards],
                        },
                    )

            result = _persist_reading(module, payload, headline, summary, cards, llm_result, db)
            yield _sse_pack("result", result.model_dump(mode="json"))
            yield _sse_pack("done", {"ok": True})
        except Exception as exc:
            yield _sse_pack("error", {"message": str(exc)})

    return StreamingResponse(event_generator(), media_type="text/event-stream")
