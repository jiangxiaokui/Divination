from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
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

ALLOWED_MODULES = {
    "bazi",
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


def _build_module_cards(module: str, payload: ReadingCreate, db: Session | None = None) -> tuple[str, str, list[ResultCard]]:
    data = payload.input_payload

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
        ]
        draw_count = 1 if spread == "single_card" else (10 if spread == "celtic_cross" else 3)
        seed = _sum_text((payload.question or "") + spread + theme)

        drawn = []
        for i in range(draw_count):
            idx = (seed + i * 7) % len(tarot_pool)
            card_name, card_meaning = tarot_pool[idx]
            reversed_flag = orientation and ((seed + i) % 2 == 1)
            drawn.append((card_name, card_meaning, reversed_flag))

        positive = sum(1 for _, _, rev in drawn if not rev)
        score = 45 + int((positive / max(draw_count, 1)) * 45)
        final_label, final_tone = _tone_from_score(score)
        # 从知识库取牌义详解
        drawn_lines = []
        for i, (name, meaning, rev) in enumerate(drawn):
            kb_desc = kb_service.get_content(db, module="tarot", category="大阿卡纳", keyword=name) if db else ""
            pos_label = "逆位" if rev else "正位"
            if kb_desc:
                drawn_lines.append(f"第{i+1}张【{name}·{pos_label}】\n{kb_desc}")
            else:
                drawn_lines.append(f"第{i+1}张【{name}·{pos_label}】{meaning}")
        drawn_text = "\n\n".join(drawn_lines)

        cards = [
            ResultCard(title="牌阵参数", content=f"牌阵: {spread}\n允许逆位: {orientation}\n主题: {theme}", tone="info"),
            ResultCard(title="抽牌结果", content=drawn_text, tone="neutral"),
            ResultCard(
                title="最终结果",
                content=f"结论: {final_label}。建议将重心放在你最可控的下一步行动上。",
                tone=final_tone,
            ),
        ]
        return "塔罗占卜", f"塔罗解读完成，结论为: {final_label}。", cards

    cards = [
        ResultCard(title="输入已接收", content="系统已收到占卜参数。", tone="neutral"),
    ]
    return "占卜请求", "请求已受理。", cards


@router.post("/{module}", response_model=ReadingOut)
def create_reading(module: str, payload: ReadingCreate, db: Session | None = Depends(get_db)) -> ReadingOut:
    if module not in ALLOWED_MODULES:
        raise HTTPException(status_code=400, detail=f"unsupported module: {module}")

    headline, summary, cards = _build_module_cards(module, payload, db)
    llm_result = None

    if payload.reading_mode == "deep":
        try:
            llm_result = enhance_reading(
                module=module,
                question=payload.question,
                summary=summary,
                cards=[c.model_dump() for c in cards],
            )
            if llm_result and llm_result.content:
                cards.append(ResultCard(title="深度解读", content=llm_result.content, tone="advice"))
                summary = f"{summary} 已生成深度解读。"
        except Exception:
            cards.append(ResultCard(title="深度解读", content="当前无法生成深度解读，已返回极速结果。", tone="info"))

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

    # Persist all user-filled fields for full traceability.
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
