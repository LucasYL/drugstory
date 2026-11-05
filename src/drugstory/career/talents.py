"""One visible signature ability per character, strengthened by their personal project."""

import json

from .content import DATA, STAGES, STATS
from .units import pts

ABILITIES = json.loads((DATA / "abilities.json").read_text())


def value(h):
    spec = ABILITIES[h["id"]]
    return spec["advanced"] if h.get("personal") else spec["base"]


def trait(key):
    a = ABILITIES[key]
    if a["kind"] == "work":
        text = (
            f"在{STAGES[a['stage']]['name']}额外贡献 {pts(a['base'])} 点{STATS[a['stat']]}开发量；"
            f"个人课题后为 {pts(a['advanced'])} 点。"
        )
    elif a["kind"] == "schedule":
        stage = STAGES[a["stage"]]["name"] if a["stage"] != "*" else "临床阶段"
        text = f"{stage}排程缩短 {a['base']} 周；个人课题后为 {a['advanced']} 周。"
    elif a["kind"] == "screen":
        text = f"候选筛选多提供 {a['base']} 条备选线索；个人课题后为 {a['advanced']} 条。"
    else:
        text = f"导师课题使学徒额外获得 {a['base']} 点经验；个人课题后为 {a['advanced']} 点。"
    return {"key": key, "name": a["name"], "description": text, "asset_id": a["asset_id"]}


def work_bonus(h, stage, stat):
    a = ABILITIES[h["id"]]
    return value(h) if a["kind"] == "work" and a["stage"] == stage and a["stat"] == stat else 0


def bonus(s, ids, kind, stage=None):
    return max(
        (
            value(h)
            for h in s["heroes"]
            if h["employed"]
            and h["id"] in ids
            and ABILITIES[h["id"]]["kind"] == kind
            and (stage is None or ABILITIES[h["id"]]["stage"] in (stage, "*"))
        ),
        default=0,
    )
