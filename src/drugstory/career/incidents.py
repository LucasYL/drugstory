"""失败事件卡：没过线时讲清楚出了什么事、谁最懂、能怎么办。

原因按「阶段组 × 第一个没过的指标」从 data/incidents.json 里抽，带键随机（种子、项目、阶段、第几次补正），
同一个失败每次都抽到同一个原因。选项只看公开状态：在职、空闲、能力、专长，不读候选真值。
"""

from __future__ import annotations

import json

from . import talents
from .content import DATA, PROFESSIONS, ROSTER, STATS
from .model import ability, busy, committed, rand

INCIDENTS = json.loads((DATA / "incidents.json").read_text())
GROUP = {stage: group for group, stages in INCIDENTS["groups"].items() for stage in stages}
REWORK = {"weeks": 8, "cost": 100, "gain": 6}
EXPERT = {"weeks": 6, "cost": 130, "gain": 9, "ability": 60}
TALENT_GAIN = 12


def pool(key, stat):
    """这个阶段、这个指标可能的原因；本组没有就从其他组借。"""
    causes = INCIDENTS["causes"]
    own = causes[GROUP[key]].get(stat)
    if own:
        return own
    return [c for group in causes.values() for c in group.get(stat, [])]


def draw(s, p, result):
    """在阶段失败时记下一个原因。"""
    key, stat = result["key"], result["failures"][0]
    cause = rand(s, "incident", p["id"], key, p["repairs"]).choice(pool(key, stat))
    p["incident"] = {"key": key, "stat": stat, "week": s["week"], **cause}
    return p["incident"]


def current(p):
    """还挂在项目上的那张卡（最后一个阶段没过时）。"""
    i = p.get("incident")
    if not i or p["status"] not in ("problem", "failed") or not p["results"]:
        return None
    last = p["results"][-1]
    return i if not last["passed"] and last["key"] == i["key"] else None


def gain(p, h):
    """这位伙伴来补正能补多少：对口专长 +12，对口专业且能力够 +9，否则不能来。"""
    i = current(p)
    if not i or not h["employed"]:
        return 0
    if i.get("talent") and talents.level(h, i["talent"]) >= 1:
        return TALENT_GAIN
    if h["profession"] == i["expert"] and ability(h) >= EXPERT["ability"]:
        return EXPERT["gain"]
    return 0


def _free(s):
    occupied = busy(s)
    return [h for h in s["heroes"] if h["employed"] and h["id"] not in occupied]


def options(s, p):
    """事件卡上的按钮，只读。每个按钮映射到一个已有命令。"""
    i = current(p)
    if not i:
        return []
    cash = s["cash"] - committed(s)
    rows = []
    if p["status"] == "problem" and p["repairs"] < 1:
        free = _free(s)
        holders = [h for h in free if i.get("talent") and talents.level(h, i["talent"]) >= 1]
        for h in holders[:1]:
            rows.append(
                {
                    "kind": "talent",
                    "label": f"让{h['name']}试试",
                    "command": "rework_expert",
                    "args": {"project": p["id"], "hero": h["id"]},
                    "weeks": EXPERT["weeks"],
                    "cost": EXPERT["cost"],
                    "people": [h["name"]],
                    "note": f"{talents.skill_name(i['talent'])}：补正幅度最大",
                    "ok": cash >= EXPERT["cost"],
                }
            )
        experts = sorted(
            (h for h in free if h not in holders and gain(p, h) == EXPERT["gain"]), key=ability, reverse=True
        )
        for h in experts[:1]:
            rows.append(
                {
                    "kind": "expert",
                    "label": f"请{PROFESSIONS[i['expert']]}的{h['name']}来看",
                    "command": "rework_expert",
                    "args": {"project": p["id"], "hero": h["id"]},
                    "weeks": EXPERT["weeks"],
                    "cost": EXPERT["cost"],
                    "people": [h["name"]],
                    "note": "对口专业，比按原方案补得多",
                    "ok": cash >= EXPERT["cost"],
                }
            )
        crew = [h for h in free if h["profession"] in ("proc", "chem")]
        best = max(crew, key=ability, default=None)
        rows.append(
            {
                "kind": "rework",
                "label": "按原方案补正",
                "command": "rework",
                "args": {"project": p["id"], "heroes": [best["id"]] if best else []},
                "weeks": REWORK["weeks"],
                "cost": REWORK["cost"],
                "people": [best["name"]] if best else [],
                "note": "需要制剂或药化能力 35",
                "ok": bool(best) and ability(best) >= 35 and cash >= REWORK["cost"],
            }
        )
    if p["status"] == "problem" and p["index"] < 2:
        rows.append(
            {
                "kind": "switch",
                "label": "换候选",
                "command": "switch_candidate",
                "args": {"project": p["id"]},
                "weeks": 0,
                "cost": 60,
                "people": [],
                "note": "从头验证另一个候选，原候选的证据保留",
                "ok": cash >= 60 and len(p.get("used_candidates", [p["chosen"]])) < len(p["candidates"]),
            }
        )
    if p["status"] == "problem":
        wizard = next((h for h in s["heroes"] if h["employed"] and talents.level(h, "wizard") >= 1), None)
        rows.append(
            {
                "kind": "stop",
                "label": "止损",
                "command": "terminate",
                "args": {"project": p["id"]},
                "weeks": 0,
                "cost": 0,
                "people": [],
                "note": f"{wizard['name']}会记住这次" if wizard else "研究记录和经验都保留",
                "ok": True,
            }
        )
    return rows


def view(s, p):
    i = current(p)
    if not i:
        return None
    talent = i.get("talent")
    return {
        "title": i["title"],
        "text": i["text"],
        "stat": STATS[i["stat"]],
        "expert": PROFESSIONS[i["expert"]],
        "talent": ROSTER[talent]["name"] if talent else None,
        "options": options(s, p),
    }
