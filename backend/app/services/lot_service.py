import random

LOT_POOLS = {
    "guanyin": [
        {
            "lot_no": 1,
            "title": "钟离成道",
            "poem": "开天辟地作良缘，吉日良时万物全。",
            "meaning": "先难后易，守正待时。",
        },
        {
            "lot_no": 2,
            "title": "苏秦不第",
            "poem": "鲸鱼未变守江河，不可升腾离碧波。",
            "meaning": "当前需蓄势，勿躁进。",
        },
    ],
    "yuelao": [
        {
            "lot_no": 1,
            "title": "天作之合",
            "poem": "花开并蒂，月照双心。",
            "meaning": "缘分可期，宜真诚沟通。",
        },
        {
            "lot_no": 2,
            "title": "迟来良缘",
            "poem": "云开见月，莫急莫忧。",
            "meaning": "时机稍后更稳妥。",
        },
    ],
    "generic": [
        {
            "lot_no": 1,
            "title": "上签",
            "poem": "时来运转，百事可成。",
            "meaning": "整体偏吉，仍需踏实行动。",
        },
        {
            "lot_no": 2,
            "title": "中签",
            "poem": "稳中求进，自有回响。",
            "meaning": "平稳发展，耐心布局。",
        },
    ],
}


def draw_lot(lot_type: str, seed: int | None = None) -> tuple[dict, dict]:
    pool = LOT_POOLS.get(lot_type, LOT_POOLS["generic"])
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
        },
    }
    return lot, trace
