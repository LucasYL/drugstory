"""Distinct product constraints and explicit investment into commercial usefulness."""

import json

from .content import DATA

PROFILES = json.loads((DATA / "products.json").read_text())


def profile(catalog):
    p = PROFILES.get(catalog)
    if not p:
        return None
    title, stage, stat, limit, enhanced, reward, text = p
    return {
        "title": title,
        "stage": stage,
        "stat": stat,
        "limit": limit,
        "enhanced": enhanced,
        "reward": reward,
        "text": text,
    }


def adjust_limits(p, key, limits):
    spec = profile(p["catalog"])
    if spec and spec["stage"] == key:
        limits[spec["stat"]] = max(limits.get(spec["stat"], 0), spec["limit"])
    return limits


def reward(p):
    spec = profile(p["catalog"])
    if not spec or p.get("design", "standard") != "validated":
        return None
    return spec["reward"] if any(r["key"] == spec["stage"] and r["passed"] for r in p["results"]) else None


def supply_factor(s, d):
    if d["catalog"] == "g_pressure" and d.get("design_reward") != "supply" and s["week"] // 12 % 3 == 2:
        return 0.88
    return 1.0
