"""Latent candidates, observations and phase-specific evidence. No omniscient UI."""

from __future__ import annotations

import math
from statistics import NormalDist

from . import development, gates, product_design, readouts, talents
from .content import BUILD, CATALOG, CLINICAL, EXPERIMENTS, PATHS, PLANS, STAGES, STATS
from .model import ability, check, hero, power, rand

FINAL = ("failed", "terminated")
# 仿制药「加急」：开发与等效性阶段赶工期，费用更高、读数更粗
RUSH = {"time": 0.7, "cost": 1.2, "noise": 1.1}
RUSH_STAGES = ("formulation", "quality", "be")
# 强化验证（精工）：关键阶段门槛更高、费用和工期增加，读数更准，通过后拿到产品奖励
ENHANCED = {"cost": 1.25, "weeks": 2}

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


def failures_on_target(s, p):
    """同靶点失败或终止过几次（司马衡「失败地图」）。"""
    target = CATALOG[p["catalog"]].get("target")
    return sum(
        1
        for q in s["projects"]
        if q["id"] != p["id"] and q["status"] in FINAL and CATALOG[q["catalog"]].get("target") == target
    )


def combo_tier(s, spec, ids):
    tier = spec.get("combo_tier", 0)
    if tier == -1 and talents.has(s, "alchemist", ids):
        return 0  # 伊莲娜「不可能的分子」
    return tier


def mechanism(s, spec):
    """靶点天生的机制偏移：按种子和靶点确定，不消耗、不改变任何随机状态。"""
    key = spec["target"] + "|" + spec["indication"]
    if key in s["mechanisms"]:
        return s["mechanisms"][key]
    return rand(s, "mechanism", key).gauss(0, 6)


def generate_candidates(s, p):
    spec = CATALOG[p["catalog"]]
    kind = p["kind"]
    science = max(power(s, p["team"], "bio"), power(s, p["team"], "chem"))
    # Scientific platforms improve the pool available at discovery, not a finished drug retroactively.
    expertise = max(0, science - 40) * 0.04
    means = {
        "generic": [86, 84, 76, 77],
        "improved": [70, 76, 73, 74],
        "innovative": [
            58 + expertise + {-2: -24, -1: -12, 0: -3, 1: 2, 2: 6}.get(combo_tier(s, spec, p["team"]), 0),
            72,
            70,
            72,
        ],
    }[kind]
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
    extra = 1 if talents.has(s, "scout", p["team"]) >= 2 else 0
    lessons = min(12, 4 * failures_on_target(s, p)) if kind == "innovative" and talents.has(s, "wizard") else 0
    narrow = 0.7 if talents.has(s, "sprout", p["team"]) else 1.0
    styles += [(f"备用线索 {i + 1}", {}) for i in range(extra)]
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
                mean += lessons
            actual = rand(s, "candidate", p["id"], spec.get("modality_id"), i, stat).gauss(mean, sd)
            if stat == "effect" and kind == "innovative":
                actual += s["mechanisms"][mechanism_key]
                if combo_tier(s, spec, p["team"]) <= -2:
                    # 不可能的组合：获益压在 II 期门槛以下，不再靠运气获批
                    actual = min(actual, STAGES["II"]["limits"]["effect"] - 8)
            c["truth"][stat] = min(98, max(15, actual))
            c["belief"][stat] = {"mean": mean, "variance": sd**2 + (36 if stat == "effect" else 0), "observations": 0}
            sigma = max(12, 24 - power(s, p["team"], STAT_ROLE[stat]) * 0.12)
            if stat == "effect":
                sigma *= narrow

            observe(s, p, c, stat, sigma, "screen")
        p["candidates"].append(c)


def stage_key(p):
    return PATHS[p["kind"]][p["index"]]


def limits(p, key):
    out = dict(STAGES[key]["limits"])
    if "effect" in out and key in ("II", "III"):
        out["effect"] += CATALOG[p["catalog"]].get("threshold_bonus", 4 * CATALOG[p["catalog"]]["difficulty"])
    # 开工时按团队专长（和疾病的特殊难关）记下的门槛调整
    for stat, delta in p.get("adjust", {}).get(key, {}).items():
        if stat in out:
            out[stat] += delta
    return product_design.adjust_limits(p, key, out)


def skill_effects(s, p, ids, key, partner=False):
    """团队专长对本阶段的影响：工期倍率与减免、各指标噪声倍率、门槛调整。"""
    fx = {"weeks": 1.0, "minus": 0, "noise": {}, "limits": {}}
    hard = gates.effects(s, p, key, partner)
    fx["weeks"] *= hard["weeks"]
    fx["limits"].update(hard["limits"])
    for stat in STAGES[key]["limits"]:
        fx["noise"][stat] = hard["noise"]
    if partner:
        return fx

    def noise(stats, factor):
        for stat in stats:
            fx["noise"][stat] = fx["noise"].get(stat, 1.0) * factor

    stats = list(STAGES[key]["limits"])
    if key == "optimize" and talents.has(s, "beaker", ids):
        fx["weeks"] *= 0.75
    if key == "III" and talents.has(s, "strategist", ids):
        fx["weeks"] *= 0.7
    if key == "II" and talents.has(s, "ruler", ids) >= 2:
        fx["minus"] += 2
    if talents.has(s, "bubble", ids) >= 2:
        noise(["safety"], 0.85)
    if key == "preclinical" and talents.has(s, "shield", ids) >= 2:
        noise(stats, 0.7)
    if key == "review" and talents.has(s, "judge", ids):
        noise(stats, 0.5)
    if talents.has(s, "crystal", ids):
        noise(["quality"], 0.5)
    if key == "quality" and talents.has(s, "pill", ids) >= 2:
        noise(stats, 0.5)
    if key in CLINICAL:
        if talents.has(s, "ruler", ids):
            noise(stats, 0.92)
        if talents.has(s, "curve", ids):
            noise(stats, 0.85)
    if key == "III" and talents.has(s, "oracle", ids):
        noise(stats, 0.85)
    if any(h["id"] in ids and h.get("prodigy") and h["rank"] == 1 for h in s["heroes"]):
        noise(stats, 1.1)
    if key == "I" and talents.has(s, "guardian", ids) and not gates.applies(p["catalog"]):
        fx["limits"]["safety"] = fx["limits"].get("safety", 0) - 4
    if key == "confirm" and talents.has(s, "forge", ids):
        fx["limits"]["effect"] = fx["limits"].get("effect", 0) - 6
    return fx


def plan_phase(s, p, ids, plan="standard", mode="internal", key=None, partner=False):
    key = key or stage_key(p)
    d, strategy = STAGES[key], PLANS[plan]
    cro = mode == "cro" or partner
    skill = max((power(s, ids, role, cro) for role in d["roles"]), default=0)
    if partner:
        skill = 60
    members = sum(min(hero(s, h)["members"], 2 + hero(s, h)["rank"]) for h in ids)
    speed = 1 + min(0.45, members / max(1, len(ids)) * 0.10)
    fx = skill_effects(s, p, ids, key, partner)
    rush = p.get("pace") == "rush" and key in RUSH_STAGES
    weeks = max(
        4, math.ceil(d["weeks"] * strategy["time"] * fx["weeks"] * (RUSH["time"] if rush else 1) / speed) - fx["minus"]
    )
    cost = d["cost"] * strategy["cost"] * (1.3 if cro and not partner else 1) * (RUSH["cost"] if rush else 1)
    if p["kind"] == "innovative":
        cost *= 1.2 if CATALOG[p["catalog"]]["difficulty"] else 1
    if key == "review" and p["kind"] != "generic":
        cost *= 2
    profile = product_design.profile(p["catalog"])
    enhanced = bool(profile and profile["stage"] == key and p.get("design") == "validated")
    if enhanced:
        cost *= ENHANCED["cost"]
        weeks += ENHANCED["weeks"]
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
        noise_by_stat[stat] *= fx["noise"].get(stat, 1.0) * (RUSH["noise"] if rush else 1)
    if enhanced:
        noise_by_stat = {stat: value * 0.8 for stat, value in noise_by_stat.items()}
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
        "category": d["category"],
        "work": development.packages(s, p, ids, key) if p.get("chosen") is not None else [],
        "adjust": fx["limits"],
    }
    if p.get("chosen") is not None:
        preview = development.projected(p, key, result["work"])
        preview.setdefault("adjust", {})[key] = fx["limits"]
        result["probability"] = phase_probability(preview, key, plan, noise_by_stat)
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
    batch_values = readouts.aggregate(p) if execution.get("batches") and key not in BUILD else None
    for stat, threshold in limits(p, key).items():
        offset = c["subgroup"] if p.get("population") == "focused" and stat == "effect" else 0
        noise = execution.get("noise_by_stat", {}).get(stat, execution["noise"])
        value = (
            batch_values[stat]
            if batch_values is not None
            else observe(s, p, c, stat, noise, f"phase-{key}-{attempt}", offset)
        )
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
    repeats = (3 if talents.has(s, "bubble", ids) else 2) if kind == "validate" else 1
    check(c["checks"].get(kind + stat, 0) < repeats, "这项研究已经完成，不能反复刷结果")
    role = EXPERIMENTS[kind]["role"] or STAT_ROLE[stat]
    check(power(s, ids, role) >= (55 if kind in ("translate", "marker") else 25), "需要对应专业的研究能力")
    if kind == "refine":
        most = 3 if talents.has(s, "triple_refine", ids) else 2
        check(c["optimized"] < most, f"这个候选已经完成 {most} 次定向优化")
    if kind == "marker":
        check(
            p["kind"] == "innovative" and p["index"] <= PATHS["innovative"].index("II"),
            "人群分层应在 II 期方案确定前验证",
        )
    plan = {**EXPERIMENTS[kind], "kind": kind, "stat": stat, "role": role}
    if kind == "validate" and talents.has(s, "bubble", ids):
        plan["cost"] = plan["cost"] / 2  # 娜迪亚「再核一遍」
    return plan


def finish_experiment(s, p):
    c, e = selected(p), p["experiment"]
    stat, kind = e["stat"], e["kind"]
    n = c["checks"].get(kind + stat, 0)
    skill = power(s, p["team"], e["role"])
    if kind == "marker":
        if talents.has(s, "bridge", p["team"]) and not c.get("imaging"):
            # 沈墨言「影像标志物」：用影像找到的获益人群效果翻倍
            c["subgroup"] *= 2
            c["imaging"] = True
        sigma = max(3, 9 - skill / 15)
        sample = c["subgroup"] + rand(s, p["id"], "marker").gauss(0, sigma)
        b = c["marker"]
        v = 1 / (1 / b["variance"] + 1 / sigma**2)
        b.update(mean=v * (b["mean"] / b["variance"] + sample / sigma**2), variance=v, observations=1)
        line = "分层研究完成：已有亚组观察，仍需结合临床专业能力判断是否采用。"
    else:
        if kind == "refine":
            delta = 3 + skill / 20
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
