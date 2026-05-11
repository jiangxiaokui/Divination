from __future__ import annotations

import random
import re

from sqlalchemy.orm import Session

from app.services import kb_service

LOT_MODULE_MAP = {
    "guanyin": "lot_guanyin",
    "yuelao": "lot_yuelao",
    "generic": "lot_generic",
}


def _extract_lot_no(keyword: str) -> int:
    match = re.search(r"(\d+)", keyword or "")
    return int(match.group(1)) if match else 0


def _parse_lot_entry(entry) -> dict:
    content = entry.content or ""
    lot_no = _extract_lot_no(entry.keyword)

    title_match = re.search(r"：([^。\n]+)", content)
    poem_match = re.search(r"签诗[:：](.+?)(?:\n|解意[:：])", content, re.DOTALL)
    meaning_match = re.search(r"解意[:：](.+)$", content, re.DOTALL)

    title = title_match.group(1).strip() if title_match else entry.keyword
    poem = poem_match.group(1).strip() if poem_match else content.strip()
    meaning = meaning_match.group(1).strip() if meaning_match else content.strip()

    return {
        "lot_no": lot_no,
        "title": title,
        "poem": poem,
        "meaning": meaning,
        "source": getattr(entry, "source", "knowledge_base"),
        "keyword": entry.keyword,
    }


def _generic_pool_from_common(db: Session) -> list[dict]:
    entries = kb_service.get_entries(db, module="common", category="吉凶总论", limit=20)
    pool: list[dict] = []
    for index, entry in enumerate(entries, start=1):
        pool.append(
            {
                "lot_no": index,
                "title": entry.keyword,
                "poem": f"通用签意 · {entry.keyword}",
                "meaning": entry.content,
                "source": getattr(entry, "source", "knowledge_base"),
                "keyword": entry.keyword,
            }
        )
    return pool


def _load_lot_pool(db: Session, lot_type: str) -> list[dict]:
    module = LOT_MODULE_MAP.get(lot_type, LOT_MODULE_MAP["generic"])
    entries = kb_service.get_entries(db, module=module, category="签文", limit=200)
    pool = [_parse_lot_entry(entry) for entry in entries]
    pool = [item for item in pool if item["lot_no"] > 0]
    pool.sort(key=lambda item: item["lot_no"])

    if pool:
        return pool
    if lot_type == "generic":
        return _generic_pool_from_common(db)
    return []


def draw_lot(db: Session, lot_type: str, seed: int | None = None) -> tuple[dict, dict]:
    pool = _load_lot_pool(db, lot_type)
    if not pool:
        raise ValueError(f"no lot entries found for {lot_type}")

    actual_seed = seed if seed is not None else random.SystemRandom().randint(1, 10**9)
    rng = random.Random(actual_seed)
    idx = rng.randrange(0, len(pool))
    lot = pool[idx]

    trace = {
        "rng_algorithm": "python_random_mersenne_twister",
        "seed": str(actual_seed),
        "draw_steps": {
            "pool_size": len(pool),
            "picked_index": idx,
            "picked_keyword": lot.get("keyword"),
            "picked_source": lot.get("source"),
        },
    }
    return lot, trace
