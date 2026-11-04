"""JSON state, deterministic keyed randomness and common accounting helpers."""

from __future__ import annotations

import hashlib
import json
import math
import random
from pathlib import Path

from .content import FACILITIES, PROFESSIONS, ROSTER, SCENARIOS

VERSION = 4
FORMAT = "drugstory-career"
ACTIVE = {"screening", "selecting", "ready", "running", "result", "problem"}
DECISIONS = {"selecting", "ready", "result", "problem"}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def rand(s, *keys):
    digest = hashlib.sha256(json.dumps([s["seed"], *keys], ensure_ascii=False).encode()).digest()
    return random.Random(int.from_bytes(digest, "big"))


def log(s, text):
    s["journal"].append({"week": s["week"], "text": text})
    s["journal"] = s["journal"][-600:]


def earn(s, amount, category):
    check(math.isfinite(amount) and amount >= 0, "收入不合法")
    s["cash"] += amount
    s["income"][category] = s["income"].get(category, 0) + amount


def spend(s, amount, category):
    check(math.isfinite(amount) and amount >= 0, "支出不合法")
    s["cash"] -= amount
    s["expense"][category] = s["expense"].get(category, 0) + amount


def find(items, key):
    for item in items:
        if item["id"] == key:
            return item
    raise ValueError("找不到这项记录")


def hero(s, key):
    h = find(s["heroes"], key)
    check(h["employed"], "这位角色暂未在公司任职")
    return h


def ability(h):
    cap = [0, 48, 66, 83, 97][h["rank"]]
    return min(cap, h["base"] + 8 * (h["rank"] - h["tier"]) + h["training"] + min(8, h["xp"] // 15))


def power(s, ids, profession, cro=False):
    values = [ability(hero(s, key)) for key in ids if hero(s, key)["profession"] == profession]
    main = max(values, default=0)
    # A second scientist contributes limited complementary capacity, never a sum of everyone.
    extra = sum(sorted(values, reverse=True)[1:]) * 0.08
    return max(55 if cro and profession == "clinical" else 0, min(98, main + extra))


def busy(s):
    result = {}
    for p in s["projects"]:
        if p["status"] in ("running", "screening"):
            for key in p["team"]:
                result[key] = p["name"]
    for job in s["jobs"]:
        for key in job["heroes"]:
            result[key] = job["name"]
    return result


def payroll(s):
    return sum(
        (1.3 + h["rank"] * 0.65 + ability(h) * 0.018 + h["members"] * 0.42) for h in s["heroes"] if h["employed"]
    )


def committed(s):
    phases = sum(
        p.get("cost_per_week", 0) * p.get("left", 0) for p in s["projects"] if p["status"] in ("running", "screening")
    )
    partners = sum(d.get("remaining_cost", 0) * d["cost_share"] for d in s["deals"] if d["status"] == "developing")
    return phases + partners


def available_money(s, amount):
    check(s["cash"] - committed(s) >= amount, f"扣除已承诺支出后，需要至少 ¥{amount:,.0f} 万")


def free_team(s, ids, allow_empty=False):
    check(isinstance(ids, list) and all(isinstance(k, str) for k in ids), "请正确选择角色")
    check(len(ids) == len(set(ids)) and len(ids) <= 3, "每阶段最多 3 位不同负责人")
    check(bool(ids) or allow_empty, "至少安排一位角色")
    occupied = busy(s)
    for key in ids:
        hero(s, key)
        check(key not in occupied, "角色正在执行另一项任务")


def make_hero(key):
    c = ROSTER[key]
    return {
        "id": key,
        "name": c["name"],
        "profession": c["profession"],
        "tier": c["tier"],
        "base": c["ability"],
        "rank": c["tier"],
        "xp": 0,
        "training": 0,
        "cases": [],
        "work": {},
        "members": 2,
        "employed": True,
        "mentored": [],
    }


def gain_work(s, ids, tag, amount, case_id=None):
    for key in ids:
        h = hero(s, key)
        n = h["work"].get(tag, 0)
        gain = amount if n < 3 else amount // 2 if n < 6 else 0
        h["work"][tag] = n + 1
        h["xp"] += gain
        if gain:
            prof = h["profession"]
            s["knowledge"][prof] += max(1, gain // 2)
        if case_id is not None and case_id not in h["cases"]:
            h["cases"].append(case_id)


def date(week):
    return f"第 {week // 48 + 1} 年 {(week % 48) // 4 + 1} 月"


def new_game(seed=42, scenario="foundation"):
    check(type(seed) is int and 0 <= seed <= 999999999, "种子应为 0 至 999999999 的整数")
    check(isinstance(scenario, str) and scenario in SCENARIOS, "没有这个开局路线")
    c = SCENARIOS[scenario]
    s = {
        "format": FORMAT,
        "version": VERSION,
        "seed": seed,
        "scenario": scenario,
        "week": 0,
        "capital": c["cash"],
        "cash": float(c["cash"]),
        "facility": 0,
        "reputation": 0,
        "knowledge": dict.fromkeys(PROFESSIONS, 0),
        "heroes": [make_hero(k) for k in c["starters"]],
        "projects": [],
        "products": [],
        "jobs": [],
        "deals": [],
        "journal": [],
        "income": {},
        "expense": {},
        "next_id": 1,
        "service_orders": [],
        "services_done": 0,
        "connections": [],
        "milestones": 0,
        "objective_done": False,
        "career_done": False,
        "negative_months": 0,
        "game_over": False,
        "minimum_cash": float(c["cash"]),
        "first_income": None,
        "first_rank2": None,
        "first_rank3": None,
        "first_rank4": None,
        "actions": [],
        "rivals": [],
        "research_archive": [],
        "mechanisms": {},
    }
    if scenario == "platform":
        s["knowledge"]["proc"] = 8
    for index, (name, market) in enumerate(
        [("银叶制药", "lipid"), ("赤杉研究所", "inflammation"), ("蓝鲸药业", "lung")]
    ):
        s["rivals"].append(
            {
                "name": name,
                "market": market,
                "launch": 192 + index * 48,
                "end": 432 + index * 48,
                "active": False,
                "cycles": 0,
            }
        )
    log(s, "街角实验室开张了。普通角色也能成长；先积累现金流和真正的专业经验。")
    return s


def dumps(s):
    return json.dumps(s, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def loads(text):
    try:
        s = json.loads(text)
        check(
            isinstance(s, dict) and s.get("format") == FORMAT and s.get("version") == VERSION,
            "养成版只读取独立 v4 存档；旧版请继续在 8877 或 8878 游玩",
        )
        check(type(s["week"]) is int and s["week"] >= 0, "存档时间不正确")
        check(type(s["seed"]) is int and s["scenario"] in SCENARIOS, "开局数据不正确")
        check(type(s["facility"]) is int and 0 <= s["facility"] < len(FACILITIES), "场地数据不正确")
        check(math.isfinite(s["cash"]), "存档资金不正确")
        for field in ("heroes", "projects", "products", "jobs", "deals", "actions"):
            check(isinstance(s[field], list), "存档结构不正确")
        dumps(s)
        return s
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        raise ValueError("无法读取养成版存档") from e


def load(path: Path):
    return loads(path.read_text())
