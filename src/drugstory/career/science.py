"""Latent candidates, observations and phase-specific evidence. No omniscient UI."""

from __future__ import annotations

import math
from statistics import NormalDist

from . import challenge, product_design, stories, talents
from .content import CATALOG, CLINICAL, EXPERIMENTS, PATHS, PLANS, STAGES, STATS
from .model import ability, check, hero, power, rand

NORMAL = NormalDist()
STAT_ROLE = {"effect": "bio", "safety": "tox", "exposure": "chem", "quality": "proc"}


def selected(p):
    check(p.get("chosen") is not None, "请先选定候选")
    return p["candidates"][p["chosen"]]


def observe(s, p, c, stat, sigma, tag, offset=0):
    actual = c["truth"][stat] + offset
    value = actual + rand(s, "observation", p["id"], c["id"], tag, stat).gauss(0, sigma)
    update_belief(c, stat, value - offset, sigma)
    return value


def update_belief(c, stat, value, sigma):
    b = c["belief"][stat]
    precision = 1 / b["variance"] + 1 / sigma**2
    b["mean"] = (b["mean"] / b["variance"] + value / sigma**2) / precision
    b["variance"] = 1 / precision
    b["observations"] += 1


def generate_candidates(s, p):
    spec = CATALOG[p["catalog"]]
    kind = p["kind"]
    science = max(power(s, p["team"], "bio"), power(s, p["team"], "chem"))
    # Scientific platforms improve the pool available at discovery, not a finished drug retroactively.
    expertise = max(0, science - 40) * 0.10
    means = {"generic": [86, 84, 76, 77], "improved": [70, 76, 73, 74], "innovative": [68 + expertise, 75, 73, 74]}[
        kind
    ]
    deviations = {"generic": [4, 5, 10, 10], "improved": [10, 10, 11, 11], "innovative": [16, 12, 12, 11]}[kind]
    mechanism_key = spec["target"] + "|" + spec["indication"]
    if mechanism_key not in s["mechanisms"]:
        s["mechanisms"][mechanism_key] = rand(s, "mechanism", mechanism_key).gauss(0, 6)
    styles = [
        ("活性线索", {"effect": 6, "safety": -4}),
        ("稳健线索", {"safety": 6, "effect": -3}),
        ("工艺线索", {"quality": 7, "exposure": 3, "effect": -3}),
    ]
    if kind == "generic":
        styles = [
            ("溶出优先处方", {"exposure": 5, "quality": -3}),
            ("稳定优先处方", {"quality": 5, "exposure": -2}),
            ("放大友好处方", {"quality": 7, "safety": -2}),
        ]
    for i, (label, offsets) in enumerate(styles):
        c = {
            "id": i,
            "label": label,
            "truth": {},
            "belief": {},
            "optimized": 0,
            "checks": {},
            "marker": {"mean": 0, "variance": 64, "observations": 0},
            "subgroup": max(0, rand(s, p["id"], i, "subgroup").gauss(5, 5)),
        }
        for stat, mean, sd in zip(STATS, means, deviations, strict=True):
            mean += offsets.get(stat, 0)
            if stat == "effect" and kind == "innovative":
                mean -= 5 * spec["difficulty"]
            actual = rand(s, "candidate", p["id"], i, stat).gauss(mean, sd)
            if stat == "effect" and kind == "innovative":
                actual += s["mechanisms"][mechanism_key]
            c["truth"][stat] = min(98, max(15, actual))
            c["belief"][stat] = {"mean": mean, "variance": sd**2 + (36 if stat == "effect" else 0), "observations": 0}
            sigma = max(12, 24 - power(s, p["team"], STAT_ROLE[stat]) * 0.12)
            sigma *= 0.9 if talents.has(s, p["team"], "screen") else 1
            observe(s, p, c, stat, sigma, "screen")
        p["candidates"].append(c)


def stage_key(p):
    return PATHS[p["kind"]][p["index"]]


def limits(p, key):
    out = dict(STAGES[key]["limits"])
    if "effect" in out and key in ("II", "III"):
        out["effect"] += 4 * CATALOG[p["catalog"]]["difficulty"]
    return product_design.adjust_limits(p, key, out)


def plan_phase(s, p, ids, plan="standard", mode="internal", key=None, partner=False):
    key = key or stage_key(p)
    d, strategy = STAGES[key], PLANS[plan]
    cro = mode == "cro" or partner
    skill = max((power(s, ids, role, cro) for role in d["roles"]), default=0)
    if partner:
        skill = 60
    members = sum(min(hero(s, h)["members"], 2 + hero(s, h)["rank"]) for h in ids)
    speed = 1 + min(0.45, members / max(1, len(ids)) * 0.10)
    relevant = [h for h in s["heroes"] if h["id"] in ids and h["profession"] in d["roles"]]
    efficiency = 0.08 * any(h.get("focus") == "efficiency" for h in relevant)
    efficiency += 0.08 * talents.has(s, [h["id"] for h in relevant], "speed")
    weeks = math.ceil(d["weeks"] * strategy["time"] * max(0.85, 1 - efficiency) / speed)
    cost = d["cost"] * strategy["cost"] * (1.3 if cro and not partner else 1)
    if key not in CLINICAL and talents.has(s, [h["id"] for h in relevant], "thrift"):
        cost *= 0.95
    if p["kind"] == "innovative":
        cost *= 1.2 if CATALOG[p["catalog"]]["difficulty"] else 1
    if key == "review" and p["kind"] != "generic":
        cost *= 2
    profile = product_design.profile(p["catalog"])
    enhanced = bool(profile and profile["stage"] == key and p.get("design") == "validated")
    if enhanced:
        cost *= 1.25
        weeks += 2
    allies = stories.active(s, ids)
    if any(h["personal"]["choice"] == "handoff" and h["profession"] in d["roles"] for h in allies):
        cost *= 0.95
    maintenance = challenge.policy(s) if challenge.enabled(s) and s["facility"] > 0 and not partner else None
    if maintenance:
        cost *= maintenance["fee"]
    # Each endpoint benefits from its own specialist. Clinical operations and
    # scientific interpretation complement each other; unrelated stars cannot
    # replace a missing specialty merely by having the highest number.
    noise_by_stat = {}
    for stat in limits(p, key):
        specialist = power(s, ids, STAT_ROLE[stat])
        if partner:
            endpoint_skill = 60
        elif key in CLINICAL:
            operations = power(s, ids, "clinical", cro)
            endpoint_skill = operations + 0.18 * specialist
        else:
            endpoint_skill = 0.7 * specialist + 0.3 * skill
        noise_by_stat[stat] = d["noise"] * strategy["noise"] * max(0.65, 1.2 - endpoint_skill / 160)
    for stat in noise_by_stat:
        precise = any(
            h["id"] in ids
            and h.get("focus") == "precision"
            and (h["profession"] == STAT_ROLE[stat] or h["profession"] == "clinical" and key in CLINICAL)
            for h in s["heroes"]
        )
        noise_by_stat[stat] *= 0.9 if precise else 1
        if (stat == "quality" and talents.has(s, ids, "quality")) or (
            stat == "safety" and talents.has(s, ids, "safety")
        ):
            noise_by_stat[stat] *= 0.94
        if key in CLINICAL and talents.has(s, ids, "clinical"):
            noise_by_stat[stat] *= 0.95
    for stat in noise_by_stat:
        if any(
            h["personal"]["choice"] == "verify"
            and (h["profession"] == STAT_ROLE[stat] or h["profession"] == "clinical" and key in CLINICAL)
            for h in allies
        ):
            noise_by_stat[stat] *= 0.92
        if enhanced:
            noise_by_stat[stat] *= 0.8
        if maintenance:
            noise_by_stat[stat] *= maintenance["noise"]
    noise = sum(noise_by_stat.values()) / len(noise_by_stat)
    result = {
        "weeks": weeks,
        "cost": round(cost, 2),
        "noise": noise,
        "noise_by_stat": noise_by_stat,
        "skill": skill,
        "key": key,
        "plan": plan,
        "mode": mode,
    }
    if p.get("chosen") is not None:
        result["probability"] = phase_probability(p, key, plan, noise_by_stat)
    return result


def focused_available(s, p, ids=None):
    if p["kind"] != "innovative" or p.get("chosen") is None:
        return False
    b = selected(p)["marker"]
    clinical = max(
        (
            ability(h)
            for h in s["heroes"]
            if h["employed"] and h["profession"] == "clinical" and (ids is None or h["id"] in ids)
        ),
        default=0,
    )
    return b["observations"] > 0 and b["mean"] - math.sqrt(b["variance"]) > 1 and clinical >= 55


def phase_probability(p, key, plan, sigma):
    c = selected(p)
    result = 1.0
    for stat, limit in limits(p, key).items():
        b = c["belief"][stat]
        extra = c["marker"]["mean"] if plan == "focused" and stat == "effect" else 0
        endpoint_noise = sigma[stat] if isinstance(sigma, dict) else sigma
        var = b["variance"] + endpoint_noise**2
        if extra:
            var += c["marker"]["variance"]
        result *= 1 - NORMAL.cdf((limit - b["mean"] - extra) / math.sqrt(var))
    return result


def outlook(p, start=None):
    """Integrate the same latent property across remaining stages, rather than independent phase draws."""
    if p.get("chosen") is None:
        return 0
    c = selected(p)
    remaining = PATHS[p["kind"]][p["index"] if start is None else start :]
    result = 1.0
    for stat in STATS:
        stages = [(limits(p, key)[stat], STAGES[key]["noise"]) for key in remaining if stat in limits(p, key)]
        if not stages:
            continue
        b = c["belief"][stat]
        vals = []
        for j in range(25):
            latent = b["mean"] + math.sqrt(b["variance"]) * NORMAL.inv_cdf((j + 0.5) / 25)
            prob = 1.0
            for threshold, noise in stages:
                extra = c["marker"]["mean"] if p.get("population") == "focused" and stat == "effect" else 0
                prob *= 1 - NORMAL.cdf((threshold - latent - extra) / noise)
            vals.append(prob)
        result *= sum(vals) / len(vals)
    return result


def evaluate(s, p, execution, attempt=0):
    c, key = selected(p), execution["key"]
    values, failures = {}, []
    for stat, threshold in limits(p, key).items():
        offset = c["subgroup"] if p.get("population") == "focused" and stat == "effect" else 0
        noise = execution.get("noise_by_stat", {}).get(stat, execution["noise"])
        value = observe(s, p, c, stat, noise, f"phase-{key}-{attempt}", offset)
        values[stat] = round(value, 1)
        if value < threshold:
            failures.append(stat)
    # Never let a later phase erase earlier adverse evidence; phase records persist.
    return {
        "key": key,
        "week": s["week"],
        "passed": not failures,
        "values": values,
        "limits": limits(p, key),
        "failures": failures,
        "plan": execution["plan"],
        "noise": execution["noise"],
        "attempt": attempt,
        "probability": execution.get("probability"),
    }


def experiment_plan(s, p, kind, stat, ids):
    check(kind in EXPERIMENTS and stat in STATS, "请选择有效的研究方法和指标")
    if p["kind"] == "generic":
        check(
            stat != "effect" and kind in ("validate", "refine"),
            "普通仿制药研究质量、处方和等效性，不重新筛选药效或人群",
        )
    c = selected(p)
    check(p["index"] < 2 or kind in ("validate", "marker"), "进入临床后不能直接改变分子性质")
    check(p["status"] == "ready", "只能在阶段开始前安排专项研究")
    check(c["checks"].get(kind + stat, 0) < (2 if kind == "validate" else 1), "这项研究已经完成，不能反复刷结果")
    role = EXPERIMENTS[kind]["role"] or STAT_ROLE[stat]
    check(power(s, ids, role) >= (55 if kind in ("translate", "marker") else 25), "需要对应专业的研究能力")
    if kind == "refine":
        check(c["optimized"] < 2, "这个候选已经完成两次定向优化")
    if kind == "marker":
        check(
            p["kind"] == "innovative" and p["index"] <= PATHS["innovative"].index("II"),
            "人群分层应在 II 期方案确定前验证",
        )
    return {**EXPERIMENTS[kind], "kind": kind, "stat": stat, "role": role}


def finish_experiment(s, p):
    c, e = selected(p), p["experiment"]
    stat, kind = e["stat"], e["kind"]
    n = c["checks"].get(kind + stat, 0)
    skill = power(s, p["team"], e["role"])
    if kind == "marker":
        sigma = max(3, 9 - skill / 15)
        sample = c["subgroup"] + rand(s, p["id"], "marker").gauss(0, sigma)
        b = c["marker"]
        v = 1 / (1 / b["variance"] + 1 / sigma**2)
        b.update(mean=v * (b["mean"] / b["variance"] + sample / sigma**2), variance=v, observations=1)
        line = "分层研究完成：已有亚组观察，仍需结合临床专业能力判断是否采用。"
    else:
        if kind == "refine":
            delta = 3 + skill / 20 + (1 if talents.has(s, p["team"], "refine") else 0)
            trade = {"effect": "safety", "safety": "effect", "exposure": "quality", "quality": "exposure"}[stat]
            if p["kind"] == "generic" and stat == "safety":
                trade = "quality"
            for attr, change in ((stat, delta), (trade, -delta * 0.5)):
                actual = min(98, max(10, c["truth"][attr] + change)) - c["truth"][attr]
                c["truth"][attr] += actual
                c["belief"][attr]["mean"] += actual
            c["optimized"] += 1
            line = f"定向优化完成：{STATS[stat]}得到改善，同时牺牲了部分{STATS[trade]}。"
        else:
            line = f"{EXPERIMENTS[kind]['name']}完成：更新了{STATS[stat]}的证据范围。"
        sigma = max(3, (8 if kind == "translate" else 13) - skill / 12)
        observe(s, p, c, stat, sigma, f"experiment-{kind}-{stat}-{n}")
    c["checks"][kind + stat] = n + 1
    return line
