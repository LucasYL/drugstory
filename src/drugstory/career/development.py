"""Finite engineering work improves a candidate before clinical testing."""

import math

from . import events, talents
from .content import BUILD, PROFESSIONS, STAGES, STATS
from .model import ability, available_money, check, hero, spend

FOCUSES = {
    "balanced": {"name": "均衡开发", "text": "按团队分工改善相关性质，保留平衡。"},
    "potency": {"name": "活性优先", "text": "活性开发量增加 25%，同时付出相当于活性开发量 25% 的安全代价。"},
    "robust": {"name": "稳定优先", "text": "工艺开发量增加 25%，同时付出相当于工艺开发量 20% 的暴露代价。"},
}
ROLE_OUTPUT = {
    "optimize": {
        "bio": {"effect": 1},
        "chem": {"exposure": 0.8, "safety": 0.65},
        "proc": {"quality": 1},
        "tox": {"safety": 1},
    },
    "formulation": {"proc": {"quality": 0.65}, "chem": {"exposure": 0.45}},
    "quality": {"proc": {"quality": 0.35}, "tox": {"safety": 0.35}},
    "design": {"proc": {"quality": 0.6, "exposure": 0.7}, "chem": {"safety": 0.45}, "bio": {"effect": 0.45}},
}
ROOMS = {key: "room_" + key for key in PROFESSIONS}
EQUIPMENT_COST = [0, 800, 3000, 9000]


def packages(s, p, ids, key):
    if key not in BUILD:
        return []
    existing = p["candidates"][p["chosen"]].get("build_plans", {}).get(key)
    if existing:
        return existing["packages"]
    result = []
    best = {}
    for identity in ids:
        h = hero(s, identity)
        role = h["profession"]
        if role not in ROLE_OUTPUT[key]:
            continue
        if role not in best or ability(h) > ability(best[role]):
            best[role] = h
    for role, h in best.items():
        members = min(h["members"], 2 + h["rank"])
        mastery = max(0, (ability(h) - 22) / 65) ** 1.25
        base = (2 + 15 * mastery) * (1 + 0.16 * math.sqrt(members))
        base += s.get("equipment", {}).get(role, 0) * 2
        output = {
            stat: min(24, base * weight + talents.work_bonus(h, key, stat))
            for stat, weight in ROLE_OUTPUT[key][role].items()
        }
        focus = p.get("work_focus", "balanced")
        if focus == "potency" and "effect" in output:
            output["safety"] = output.get("safety", 0) - output["effect"] * 0.25
            output["effect"] *= 1.25
        if focus == "robust" and "quality" in output:
            output["exposure"] = output.get("exposure", 0) - output["quality"] * 0.20
            output["quality"] *= 1.25
        result.append(
            {"actor": h["id"], "role": role, "members": members, "amounts": {k: round(v, 1) for k, v in output.items()}}
        )
    return result


def initialize(s, p):
    key = p["execution"]["key"]
    if key not in BUILD:
        return
    c = p["candidates"][p["chosen"]]
    c.setdefault("build_plans", {}).setdefault(key, {"packages": packages(s, p, p["team"], key), "completed": 0})


def tick(s, p):
    key = p["execution"]["key"]
    if key not in BUILD:
        return
    plan = p["candidates"][p["chosen"]]["build_plans"][key]
    elapsed = p["execution"]["weeks"] - p["left"]
    target = min(3, int(elapsed * 4 / p["execution"]["weeks"]))
    while plan["completed"] < target:
        c = p["candidates"][p["chosen"]]
        for package in plan["packages"]:
            detail = []
            for stat, total in package["amounts"].items():
                delta = total / 3
                c["truth"][stat] = min(98, max(10, c["truth"][stat] + delta))
                c["belief"][stat]["mean"] = min(98, max(10, c["belief"][stat]["mean"] + delta))
                detail.append(f"{STATS[stat]}开发量 {delta:+.1f}")
            events.emit(
                s,
                "work_completed",
                actors=[package["actor"]],
                project=p["id"],
                room=ROOMS[package["role"]],
                data={
                    "name": hero(s, package["actor"])["name"],
                    "stage": STAGES[key]["name"],
                    "detail": "、".join(detail),
                    "amounts": {k: round(v / 3, 2) for k, v in package["amounts"].items()},
                },
            )
        plan["completed"] += 1


def upgrade(s, profession):
    check(profession in PROFESSIONS and profession != "clinical", "请选择专业实验室")
    level = s["equipment"][profession]
    check(level < 3, "实验室已达到最高级")
    check(s["facility"] >= level, "先扩建到下一档场地")
    available_money(s, EQUIPMENT_COST[level + 1])
    spend(s, EQUIPMENT_COST[level + 1], "equipment")
    s["equipment"][profession] += 1
    events.emit(
        s,
        "equipment_upgraded",
        room=ROOMS[profession],
        data={"name": PROFESSIONS[profession] + "实验室", "level": level + 1},
    )


def view(s):
    return [
        {
            "id": ROOMS[k],
            "profession": k,
            "name": v + "实验室",
            "level": s["equipment"][k],
            "cost": EQUIPMENT_COST[s["equipment"][k] + 1] if s["equipment"][k] < 3 else None,
            "available": s["equipment"][k] < 3 and s["facility"] >= s["equipment"][k],
            "text": "每级为本专业开发工作增加 2 点基础开发量；高级分子类型需要相应设备。",
        }
        for k, v in PROFESSIONS.items()
        if k != "clinical"
    ]


def projected(p, key, packages):
    """Read-only remaining planned improvements, without looking at hidden truth."""
    import copy

    result = copy.deepcopy(p)
    c = result["candidates"][result["chosen"]]
    completed = c.get("build_plans", {}).get(key, {}).get("completed", 0)
    for package in packages:
        for stat, total in package["amounts"].items():
            c["belief"][stat]["mean"] = min(98, max(10, c["belief"][stat]["mean"] + total * (3 - completed) / 3))
    return result
