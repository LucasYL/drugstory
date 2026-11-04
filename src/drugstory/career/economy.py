"""Business, characters and progression; shared by public views and commands."""

from __future__ import annotations

import math

from . import competition, honors, talents
from .content import CATALOG, FACILITIES, PATHS, PROFESSIONS, PROMOTION, RANKS, ROSTER, TERMS
from .model import earn, gain_work, log, payroll, rand, spend
from .science import outlook, plan_phase, selected


def recruit_requirements(s, key):
    c = ROSTER[key]
    tier, prof = c["tier"], c["profession"]
    checks = []
    if tier >= 2:
        knowledge = {2: 8, 3: 30, 4: 65}[tier]
        checks += [
            (f"{PROFESSIONS[prof]}知识 {knowledge}", s["knowledge"][prof] >= knowledge),
            (f"研究里程碑 { {2: 2, 3: 8, 4: 20}[tier] }", s["milestones"] >= {2: 2, 3: 8, 4: 20}[tier]),
        ]
    if tier >= 3:
        checks += [
            (f"{FACILITIES[tier - 2]['name']}或更高", s["facility"] >= tier - 2),
            (f"至少一位{RANKS[tier - 1]}角色", any(h["employed"] and h["rank"] >= tier - 1 for h in s["heroes"])),
        ]
    return checks


def recruit_cost(key):
    return [0, 70, 220, 650, 1800][ROSTER[key]["tier"]]


def promotion_requirements(s, h):
    if h["rank"] == 4:
        return []
    c = PROMOTION[h["rank"] + 1]
    return [
        (f"专业经验 {h['xp']}/{c['xp']}", h["xp"] >= c["xp"]),
        (f"有效项目履历 {len(h['cases'])}/{c['cases']}", len(h["cases"]) >= c["cases"]),
        (
            f"专业知识 {s['knowledge'][h['profession']]}/{c['knowledge']}",
            s["knowledge"][h["profession"]] >= c["knowledge"],
        ),
        (f"场地：{FACILITIES[c['facility']]['name']}", s["facility"] >= c["facility"]),
    ]


def orders(s):
    quarter = s["week"] // 12
    random = rand(s, "orders", quarter)
    professions = random.sample(list(PROFESSIONS), 3)
    # Always include an accessible basic proc/chem order in the initial quarters.
    if quarter < 4:
        professions[0] = "proc" if quarter % 2 == 0 else "chem"
    return [
        {
            "id": f"{quarter}-{i}",
            "profession": prof,
            "name": PROFESSIONS[prof] + "技术服务",
            "weeks": 10,
            "reward": 160 + (25 if quarter >= 4 else 0),
            "cost": 20,
            "requirement": 28,
            "taken": f"{quarter}-{i}" in s["service_orders"],
        }
        for i, prof in enumerate(professions)
    ]


def quote(s, p, kind):
    if kind not in TERMS or p["kind"] != "innovative" or p["status"] != "result":
        return None
    last = p["results"][-1]
    if not last["passed"] or last["key"] not in ("preclinical", "II"):
        return None
    chance = outlook(p, p["index"] + 1)
    c = selected(p)
    if chance < 0.12 or c["belief"]["effect"]["mean"] < 57:
        return None
    spec, t = CATALOG[p["catalog"]], TERMS[kind]
    rivalry = competition.pressure(s, spec["market"])
    occupancy = sum(1 for d in s["products"] if d["active"] and d["market"] == spec["market"])
    market = (1 + spec["difficulty"] * 0.35) / (1 + 0.20 * (rivalry + occupancy))
    value = (0.7 + min(0.7, chance)) * market
    base = 700 if last["key"] == "preclinical" else 1700
    remaining = sum(plan_phase(s, p, [], key=key, partner=True)["cost"] for key in PATHS[p["kind"]][p["index"] + 1 :])
    return {
        "kind": kind,
        "name": t["name"],
        "upfront": round(base * value * t["upfront"]),
        "human_milestone": round(140 * value) if last["key"] == "preclinical" else 0,
        "proof_milestone": round(280 * value) if last["key"] == "preclinical" else 0,
        "approval_milestone": round(1100 * value),
        "royalty": t["royalty"],
        "cost_share": t["cost_share"],
        "remaining_cost": remaining,
        "owner_commitment": round(remaining * t["cost_share"]),
        "approval_estimate": chance,
    }


def product_life(d):
    return {"generic": 576, "improved": 432, "innovative": 480}[d["kind"]]


def catalog_in_market(s, catalog):
    return any(
        d["catalog"] == catalog and d["active"] and (d["partner"] or s["week"] - d["launched"] < product_life(d) - 96)
        for d in s["products"]
    )


def make_product(s, p, partner=False, name=None):
    spec, candidate = CATALOG[p["catalog"]], selected(p)
    values = candidate["truth"]
    # Efficacy is meaningful relative to the therapeutic need; quality mainly changes cost.
    benefit = max(0.65, min(1.45, 0.85 + (values["effect"] - 65) / 70))
    if p["kind"] == "generic":
        benefit = 1
    reach = 0.65 if p.get("population") == "focused" else 1
    product = {
        "id": f"drug-{p['id']}",
        "project": p["id"],
        "catalog": p["catalog"],
        "name": name or p["name"],
        "kind": p["kind"],
        "market": spec["market"],
        "launched": s["week"],
        "peak": spec["peak"] * benefit * reach,
        "margin": min(
            0.82, {"generic": 0.46, "improved": 0.56, "innovative": 0.66}[p["kind"]] + (values["quality"] - 60) / 300
        ),
        "partner": partner,
        "active": True,
        "production": "contract",
        "total_revenue": 0.0,
        "total_profit": 0.0,
        "last_revenue": 0.0,
        "last_profit": 0.0,
        "benefit": round(benefit, 2),
    }
    if not partner:
        for old in s["products"]:
            if old["catalog"] == p["catalog"] and old["active"] and not old["partner"]:
                old["active"] = False
                log(s, f"{old['name']}完成产品换代，旧生产线退出，避免重复占用同一市场。")
    s["products"].append(product)
    if not partner:
        s["reputation"] += {"generic": 2, "improved": 5, "innovative": 12}[p["kind"]]
    return product


def production_lines(s):
    return sum(
        {"generic": 1, "improved": 1, "innovative": 2}[d["kind"]]
        for d in s["products"]
        if d["active"] and not d["partner"] and d["production"] == "self"
    )


def expected_sales(s, d):
    age = s["week"] - d["launched"]
    life = {"generic": 576, "improved": 432, "innovative": 480}[d["kind"]]
    if not d["active"] or age >= life or d["production"] == "suspended":
        return 0, 0
    ramp = 12 if d["kind"] == "generic" else 40
    curve = min(1, (age + 1) / ramp) * max(0.2, 1 - max(0, age - life * 0.65) / (life * 0.5))
    competitors = competition.pressure(s, d["market"])
    siblings = sum(
        1
        for x in s["products"]
        if x["id"] != d["id"] and x["active"] and x["production"] != "suspended" and x["market"] == d["market"]
    )
    share = 1 / (1 + 0.55 * competitors + 0.4 * siblings)
    price = max(0.65, 1 - age / 1800) if d["kind"] == "generic" else 1
    revenue = d["peak"] * curve * share * price
    margin = min(0.90, d["margin"] + (0.12 if d["production"] == "self" else 0))
    return revenue, revenue * margin


def market_step(s):
    competition.step(s)
    for d in s["products"]:
        life = {"generic": 576, "improved": 432, "innovative": 480}[d["kind"]]
        if d["active"] and s["week"] - d["launched"] >= life:
            d["active"] = False
            log(s, f"{d['name']}进入生命周期末端，退出销售；相关分成同步停止。")
        if d["active"] and not d["partner"] and not d.get("renewal_notice") and s["week"] - d["launched"] >= life - 96:
            d["renewal_notice"] = True
            log(s, f"{d['name']}距离退出市场约 96 周，现在可准备换代方案或其他收入来源。")
        revenue, profit = expected_sales(s, d)
        d["last_revenue"], d["last_profit"] = revenue, profit
        d["total_revenue"] += revenue
        d["total_profit"] += profit
        if d["partner"]:
            deal = next(x for x in s["deals"] if x["project"] == d["project"])
            royalty = revenue * deal["royalty"]
            earn(s, royalty, "royalties")
            deal["royalties"] += royalty
            deal["weekly_royalty"] = royalty
        else:
            earn(s, revenue, "sales")
            spend(s, revenue - profit, "manufacturing")
        if revenue > 0 and s["first_income"] is None:
            s["first_income"] = s["week"]


def objectives(s):
    own = [d for d in s["products"] if not d["partner"]]
    counts = {kind: sum(d["kind"] == kind for d in own) for kind in ("generic", "improved", "innovative")}
    rank2 = sum(h["employed"] and h["rank"] >= 2 for h in s["heroes"])
    rank3 = sum(h["employed"] and h["rank"] >= 3 for h in s["heroes"])
    groups = {
        "foundation": [
            ("自主仿制药", counts["generic"], 2),
            ("自主改良药", counts["improved"], 1),
            ("精英以上角色", rank2, 3),
        ],
        "independent": [("自主创新药", counts["innovative"], 2), ("大师以上角色", rank3, 1)],
        "licensing": [("已签授权", len(s["deals"]), 3), ("已收首付款", s["income"].get("upfront", 0), 1800)],
        "platform": [
            ("知识达 30 的专业", sum(v >= 30 for v in s["knowledge"].values()), 3),
            ("大师以上角色", rank3, 1),
            ("创新成果或授权", counts["innovative"] + len(s["deals"]), 1),
        ],
    }
    rows = [{"name": name, "value": value, "goal": goal} for name, value, goal in groups[s["scenario"]]]
    return rows, all(r["value"] >= r["goal"] for r in rows) and s["cash"] > 0


def company_score(s):
    own = [p for p in s["products"] if not p["partner"]]
    product_points = sum({"generic": 8, "improved": 25, "innovative": 80}[p["kind"]] for p in own)
    role_points = sum((h["rank"] - 1) ** 2 * 12 for h in s["heroes"] if h["employed"])
    return round(
        product_points
        + role_points
        + sum(s["knowledge"].values()) / 5
        + len(s["deals"]) * 30
        + len(s["awards"]) * 20
        + len(s["legacies"]) * 500
        + (100 if s["objective_done"] else 0)
        + max(0, s["cash"] - s["capital"]) / 1500
    )


def costs_per_week(s):
    return (
        payroll(s)
        + FACILITIES[s["facility"]]["rent"]
        + sum(p.get("cost_per_week", 0) for p in s["projects"] if p["status"] in ("screening", "running"))
        + sum(d.get("cost_per_week", 0) * d["cost_share"] for d in s["deals"] if d["status"] == "developing")
    )


def finish_job(s, job):
    if job["kind"] == "independent":
        honors.finish_proof(s, job)
        gain_work(s, job["heroes"], "independent-" + job["product"] + str(job["step"]), 10)
        return
    if job["kind"] == "service":
        earn(s, job["reward"], "services")
        s["services_done"] += 1
        gain_work(s, job["heroes"], "service-" + job["profession"], 4)
        if s["first_income"] is None:
            s["first_income"] = s["week"]
        log(s, f"{job['name']}交付，收到 ¥{job['reward']} 万；常规服务的经验会逐渐递减。")
    elif job["kind"] == "train":
        h = next(h for h in s["heroes"] if h["id"] == job["heroes"][0])
        h["training"] += 3
        h["xp"] += 5 + (2 if talents.trait(h["id"])["key"] == "learner" else 0)
        log(s, f"{h['name']}完成培训。晋阶仍需要真实项目履历。")
    elif job["kind"] == "mentor":
        pupil = next(h for h in s["heroes"] if h["id"] == job["heroes"][1])
        pupil["xp"] += 10 + (5 if talents.has(s, [job["heroes"][0]], "mentor") else 0)
        pupil["training"] += 2
        pupil["mentored"].append(job["heroes"][0])
        log(s, f"{pupil['name']}完成导师课题，专业经验增加；还需要自己的项目履历。")
    elif job["kind"] == "connect":
        s["connections"].append(job["target"])
        gain_work(s, job["heroes"], "collaboration-" + job["target"], 6)
        log(s, f"与{ROSTER[job['target']]['name']}的合作完成，现在可以正式邀请加入。")


def report(s):
    completed = [p for p in s["projects"] if p["status"] in ("approved", "failed", "terminated", "licensed")]
    entries = [p for p in s["projects"] if any(r["key"] == "I" for r in p["results"]) or p.get("entered_I")]
    return {
        "week": s["week"],
        "cash": round(s["cash"]),
        "minimum_cash": round(s["minimum_cash"]),
        "bankrupt": s["game_over"],
        "objective": s["objective_done"],
        "score": company_score(s),
        "approvals": {
            k: sum(p["kind"] == k and not p["partner"] for p in s["products"])
            for k in ("generic", "improved", "innovative")
        },
        "licenses": len(s["deals"]),
        "clinical_entries": len(entries),
        "clinical_approved": sum(p["status"] == "approved" for p in entries),
        "clinical_failed": sum(p["status"] == "failed" for p in entries),
        "clinical_licensed": sum(p["status"] == "licensed" for p in entries),
        "clinical_ongoing": sum(p["status"] not in ("approved", "failed", "licensed", "terminated") for p in entries),
        "clinical_terminated": sum(p["status"] == "terminated" for p in entries),
        "completed": len(completed),
        "failures": sum(p["status"] == "failed" for p in completed),
        "first_income": s["first_income"],
        "rank2": s["first_rank2"],
        "rank3": s["first_rank3"],
        "rank4": s["first_rank4"],
        "highest_rank": max(h["rank"] for h in s["heroes"]),
        "partner_approvals": sum(d["status"] == "approved" for d in s["deals"]),
        "partner_failures": sum(d["status"] == "failed" for d in s["deals"]),
        "profit": math.floor(sum(s["income"].values()) - sum(s["expense"].values())),
    }
