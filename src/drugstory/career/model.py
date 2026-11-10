"""JSON state, deterministic keyed randomness and common accounting helpers."""

from __future__ import annotations

import hashlib
import json
import math
import random
from pathlib import Path

from .content import FACILITIES, PROFESSIONS, ROSTER, SCENARIOS

VERSION = 10
READABLE = (8, 9, 10)
# 每个存档格式由哪一版游戏写入：v8 是原文件（没有后缀），之后每升一次格式，新进度另存到带后缀的文件，
# 旧文件一个字节都不改，旧版本游戏还能接着读它。
SUFFIX = {8: "", 9: "-v11", 10: "-v12"}
FORMAT = "drugstory-career"
ACTIVE = {"screening", "selecting", "ready", "running", "checkpoint", "result", "problem"}
DECISIONS = {"selecting", "ready", "result", "problem", "checkpoint"}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def rand(s, *keys):
    digest = hashlib.sha256(json.dumps([s["seed"], *keys], ensure_ascii=False).encode()).digest()
    return random.Random(int.from_bytes(digest, "big"))


def log(s, text):
    from .events import emit

    emit(s, "notice", data={"text": text})


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


RANK_CAP = [0, 48, 66, 83, 99]


def ability(h):
    """阶位决定当前能练到多高，潜力上限决定这个人最终能练到多高。"""
    from .talents import potential

    cap = min(RANK_CAP[h["rank"]], potential(h))
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
        if p["status"] in ("running", "screening", "checkpoint"):
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
        p.get("cost_per_week", 0) * p.get("left", 0)
        for p in s["projects"]
        if p["status"] in ("running", "screening", "checkpoint")
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
        "prodigy": bool(c.get("prodigy")),
        "joined": 0,
        "inherited": [],
        "retired": False,
    }


def gain_work(s, ids, tag, amount, case_id=None):
    for key in ids:
        h = hero(s, key)
        n = h["work"].get(tag, 0)
        gain = amount if n < 3 else amount // 2 if n < 6 else 0
        if h.get("prodigy"):
            gain = gain * 3 // 2
        h["work"][tag] = n + 1
        h["xp"] += gain
        if gain:
            prof = h["profession"]
            s["knowledge"][prof] += max(1, gain // 2)
        if case_id is not None and case_id not in h["cases"]:
            h["cases"].append(case_id)


def date(week):
    return f"第 {week // 48 + 1} 年 {(week % 48) // 4 + 1} 月"


def new_game(seed=42, scenario="foundation", difficulty="standard", term=20):
    from .challenge import MODES
    from .rating import TERMS

    check(type(term) is int and term in TERMS, "任期只能是 10 年或 20 年")

    check(isinstance(difficulty, str) and difficulty in MODES, "请选择经营难度")
    check(type(seed) is int and 0 <= seed <= 999999999, "种子应为 0 至 999999999 的整数")
    check(isinstance(scenario, str) and scenario in SCENARIOS, "没有这个开局路线")
    c = SCENARIOS[scenario]
    s = {
        "format": FORMAT,
        "version": VERSION,
        "seed": seed,
        "scenario": scenario,
        "difficulty": difficulty,
        "equipment": dict.fromkeys(PROFESSIONS, 0),
        "notebook": {},
        "event_seq": 0,
        "events": [],
        "transition_events": [],
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
        "term": term,
        "final": None,
        "nominations": [],
        "inheritances": [],
        "chapter": 0,
        "chapter_log": [],
        "bounties": [],
        "bounties_done": [],
        "tips_seen": [],
        "chronicle": [],
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
    from . import competition, honors

    competition.initialize(s)
    honors.initialize(s)
    log(s, "街角实验室开张了。普通角色也能成长；先积累现金流和真正的专业经验。")
    return s


def dumps(s):
    return json.dumps(s, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def loads(text):
    try:
        s = json.loads(text)
        check(
            isinstance(s, dict) and s.get("format") == FORMAT and s.get("version") in READABLE,
            "研究所版读取 v8–v10 存档；v7 请在 8883、v6 请在 8881 继续游玩",
        )
        s.pop("migrated_from", None)  # 只标记「这次读入时刚升级」，不随存档延续
        original = s["version"]
        while s["version"] < VERSION:
            MIGRATIONS[s["version"]](s)
        if original < VERSION:
            s["migrated_from"] = original
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


def migrate_v8(s):
    """在内存副本里补齐 v9 字段；不写回原文件（服务端会另存到新路径）。"""
    from .rating import PATIENTS_PER_WAN

    s["version"] = 9
    s.setdefault("term", 20)
    s.setdefault("final", None)
    s.setdefault("nominations", [])
    s.setdefault("inheritances", [])
    s.setdefault("chapter", 0)
    s.setdefault("chapter_log", [])
    s.setdefault("bounties", [])
    s.setdefault("bounties_done", [])
    for h in s["heroes"]:
        h.setdefault("prodigy", False)
        h.setdefault("joined", 0)
        h.setdefault("inherited", [])
        h.setdefault("retired", False)
    for d in s["products"]:
        d.setdefault("patients", round(d.get("total_revenue", 0) * PATIENTS_PER_WAN[d["kind"]]))
    for festival in s.get("festivals", []):
        festival.pop("entry", None)


def migrate_v9(s):
    """v0.12：成长提示记录、编年史、项目的自动推进与节奏、产品销售历史。"""
    s["version"] = 10
    s.setdefault("tips_seen", [])
    s.setdefault("chronicle", [])
    for p in s["projects"]:
        p.setdefault("autopilot", "")
        p.setdefault("pace", "standard")
    for d in s["products"]:
        d.setdefault("history", [])


MIGRATIONS = {8: migrate_v8, 9: migrate_v9}


def load(path: Path):
    return loads(path.read_text())


def save_base(path: Path) -> Path:
    """去掉文件名里各版本的后缀（-v11、-v12），得到这一份存档的基础名字。"""
    for suffix in sorted({v for v in SUFFIX.values() if v}, key=len, reverse=True):
        if path.stem.endswith(suffix):
            return path.with_name(path.stem[: -len(suffix)] + path.suffix)
    return path


def _versioned(base: Path, version: int) -> Path:
    return base.with_name(base.stem + SUFFIX[version] + base.suffix)


def _peek_version(path: Path):
    try:
        data = json.loads(path.read_text())
        return data.get("version") if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def resolve_save(path: Path) -> tuple[Path | None, Path]:
    """返回 (从哪里读, 往哪里写)。

    按「本版文件 → 较旧版本的文件 → 原文件」的顺序找第一个存在的存档。它就是本版本格式时写回它自己；
    否则读它、写到本版本的新文件，旧文件不动。都不存在时是新局：写到调用者给的路径；
    那个路径带旧版后缀（例如 -v11）时改写到本版本的文件。
    """
    base = save_base(path)
    current = _versioned(base, VERSION)
    candidates = [_versioned(base, v) for v in sorted(SUFFIX, reverse=True)]
    for candidate in candidates:
        if candidate.exists():
            return candidate, candidate if _peek_version(candidate) == VERSION else current
    return None, path if path in (base, current) else current
