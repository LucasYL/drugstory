"""每人一项改变规则的专长；大师后完成个人课题即「觉醒」，传奇可以把专长传给弟子。

效果写在各自的规则入口（science、development、engine、economy），这里只回答「谁有哪项专长、
是几级」。等级：0 没有，1 专长，2 觉醒。继承来的专长按 1 级算。
"""

import json

from .content import DATA

ABILITIES = json.loads((DATA / "abilities.json").read_text())
# 传奇传给弟子的特殊专长（不是任何人的本职专长）
EXTRA = {"triple_refine": {"name": "三次优化", "text": "定向优化每个候选可以做三次。"}}
# 潜力上限：能力最高能练到多少。传奇入职即顶格；李天天全员最高。
POTENTIAL = {1: 88, 2: 91, 3: 94, 4: 97}
PRODIGY_POTENTIAL = 99


def potential(h):
    return PRODIGY_POTENTIAL if h.get("prodigy") else POTENTIAL[h["tier"]]


def awakened(h):
    return bool(h.get("personal")) and h["rank"] >= 3


def level(h, key):
    if not h["employed"]:
        return 0
    if h["id"] == key:
        return 2 if awakened(h) else 1
    return 1 if key in h.get("inherited", []) else 0


def has(s, key, ids=None):
    """团队（ids）或全公司（ids=None）里这项专长的最高等级。"""
    return max(
        (level(h, key) for h in s["heroes"] if ids is None or h["id"] in ids),
        default=0,
    )


def trait(key):
    a = ABILITIES[key]
    return {
        "key": key,
        "name": a["name"],
        "description": a["text"],
        "awaken": a["awaken"],
        "asset_id": a["asset_id"],
    }


def holders(s, key, ids=None, minimum=1):
    """团队（ids）或全公司里，这项专长达到 minimum 级的人。"""
    return [h for h in s["heroes"] if (ids is None or h["id"] in ids) and level(h, key) >= minimum]


def skill_name(key):
    return (EXTRA.get(key) or ABILITIES[key])["name"]


def trigger(s, key, text, ids=None, minimum=1, p=None, stage=None):
    """专长生效时发 talent_triggered 事件，让场景飘字、日志记一笔、人物卡计数。

    同一人、同一专长在同一项目的同一阶段只报一次。只记录已经发生的事，不改变任何规则结果。
    """
    from .events import emit

    for h in holders(s, key, ids, minimum):
        if p is not None:
            tag = f"{h['id']}:{key}:{stage}"
            seen = p.setdefault("talent_seen", [])
            if tag in seen:
                continue
            seen.append(tag)
        year = str(s["week"] // 48 + 1)
        uses = h.setdefault("talent_uses", {})
        uses[year] = uses.get(year, 0) + 1
        emit(
            s,
            "talent_triggered",
            actors=[h["id"]],
            project=p["id"] if p is not None else None,
            data={"hero": h["name"], "key": key, "name": skill_name(key), "text": text},
        )


def inherited(h):
    out = []
    for key in h.get("inherited", []):
        spec = EXTRA.get(key) or {"name": ABILITIES[key]["name"], "text": ABILITIES[key]["text"]}
        out.append({"key": key, "name": spec["name"], "description": spec["text"]})
    return out
