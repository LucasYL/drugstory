"""Read-only projection. Hidden candidate properties never enter normal browser state."""

from __future__ import annotations

import math

from . import economy as e
from . import engine
from . import science as sc
from .content import (
    CATALOG,
    CLINICAL,
    EXPERIMENTS,
    FACILITIES,
    KINDS,
    PATHS,
    PLANS,
    PROFESSIONS,
    PROMOTION,
    RANKS,
    ROSTER,
    SCENARIOS,
    SKILLS,
    STAGES,
    STATS,
    TERMS,
)
from .model import ACTIVE, DECISIONS, ability, busy, committed, date, payroll

STATUS = {
    "screening": "筛选中",
    "selecting": "选择候选",
    "ready": "准备研究",
    "running": "研究进行中",
    "result": "阶段结果",
    "problem": "需要补正",
    "failed": "未通过",
    "terminated": "已止损",
    "approved": "已上市",
    "licensed": "已授权",
}


def evidence(c, kind="innovative"):
    names = (
        STATS
        if kind != "generic"
        else {"safety": "杂质与质量控制", "exposure": "等效性支持", "quality": "稳定性与放大"}
    )
    return [
        {
            "key": stat,
            "name": name,
            "mean": round(c["belief"][stat]["mean"], 1),
            "low": round(max(0, c["belief"][stat]["mean"] - 1.645 * math.sqrt(c["belief"][stat]["variance"]))),
            "high": round(min(100, c["belief"][stat]["mean"] + 1.645 * math.sqrt(c["belief"][stat]["variance"]))),
            "observations": c["belief"][stat]["observations"],
        }
        for stat, name in names.items()
    ]


def recommended_team(s, p):
    stage = sc.stage_key(p)
    occupied = busy(s)
    available = [h for h in s["heroes"] if h["employed"] and h["id"] not in occupied]
    result = []
    for role in STAGES[stage]["roles"]:
        options = [h for h in available if h["profession"] == role]
        if options:
            result.append(max(options, key=ability)["id"])
    mode = "cro" if stage in CLINICAL and not any(h["profession"] == "clinical" for h in available) else "internal"
    if (
        stage in CLINICAL
        and engine.internal_usage(s) >= FACILITIES[s["facility"]]["slots"]
        and not (p["clinical_started"] and p["mode"] == "internal")
    ):
        mode = "cro"
    return result, mode


def chance_range(probability):
    mid = round(probability * 100)
    return f"约 {max(0, mid - 8)}–{min(99, mid + 8)}%"


def project_view(s, p):
    key = sc.stage_key(p)
    ids, mode = recommended_team(s, p)
    estimates = []
    if p["chosen"] is not None:
        for plan in PLANS:
            if plan == "focused" and (key not in ("II", "III") or not sc.focused_available(s, p)):
                continue
            execution = sc.plan_phase(s, p, ids, plan, mode)
            estimates.append(
                {
                    **execution,
                    "name": PLANS[plan]["name"],
                    "text": PLANS[plan]["text"],
                    "chance": chance_range(sc.phase_probability(p, key, plan, execution["noise_by_stat"])),
                }
            )
    candidates = (
        [
            {
                "id": c["id"],
                "label": c["label"],
                "evidence": evidence(c, p["kind"]),
                "optimized": c["optimized"],
                "checks": c["checks"],
                "marker": c["marker"],
            }
            for c in p["candidates"]
        ]
        if p["status"] != "screening"
        else []
    )
    quotes = [q for kind in TERMS if (q := e.quote(s, p, kind)) is not None]
    return {
        k: p[k]
        for k in (
            "id",
            "name",
            "catalog",
            "kind",
            "status",
            "index",
            "chosen",
            "left",
            "spent",
            "team",
            "results",
            "feedback",
            "repairs",
            "population",
            "mode",
            "started",
            "ended",
        )
    } | {
        "kind_name": KINDS[p["kind"]],
        "status_name": STATUS[p["status"]],
        "active": p["status"] in ACTIVE,
        "deferred": p.get("deferred", False),
        "key": key,
        "phase": STAGES[key]["name"],
        "question": STAGES[key]["question"],
        "path": [STAGES[k]["name"] for k in PATHS[p["kind"]]],
        "candidates": candidates,
        "plans": estimates,
        "quotes": quotes,
        "recommended": ids,
        "recommended_mode": mode,
        "running_experiment": p.get("experiment", {}).get("kind") if p.get("experiment") else None,
        "future_base_cost": sum(
            sc.plan_phase(s, p, [], key=k, mode="cro" if k in CLINICAL else "internal")["cost"]
            for k in PATHS[p["kind"]][p["index"] :]
        ),
        "outlook": chance_range(sc.outlook(p)) if p["chosen"] is not None else "尚未选定候选",
        "can_focus": sc.focused_available(s, p),
    }


def snapshot(s):
    occupied = busy(s)
    heroes = []
    for h in s["heroes"]:
        if not h["employed"]:
            continue
        heroes.append(
            {
                **h,
                "ability": ability(h),
                "profession_name": PROFESSIONS[h["profession"]],
                "rank_name": RANKS[h["rank"]],
                "title": RANKS[h["rank"]] + "·" + h["name"],
                "busy": occupied.get(h["id"]),
                "skill": SKILLS[h["profession"]],
                "promotion": [{"text": label, "ok": ok} for label, ok in e.promotion_requirements(s, h)],
                "promotion_cost": PROMOTION[h["rank"] + 1]["cost"] if h["rank"] < 4 else 0,
                "weekly_salary": round(1.3 + h["rank"] * 0.65 + ability(h) * 0.018 + h["members"] * 0.42, 1),
                "story": ROSTER[h["id"]]["story"],
            }
        )
    roster = []
    for key, c in ROSTER.items():
        if any(h["id"] == key and h["employed"] for h in s["heroes"]):
            continue
        checks = e.recruit_requirements(s, key)
        roster.append(
            {
                **c,
                "profession_name": PROFESSIONS[c["profession"]],
                "rank_name": RANKS[c["tier"]],
                "title": RANKS[c["tier"]] + "·" + c["name"],
                "cost": e.recruit_cost(key),
                "requirements": [{"text": t, "ok": ok} for t, ok in checks],
                "unlocked": all(ok for _, ok in checks),
                "connected": key in s["connections"],
                "connecting": any(j.get("target") == key for j in s["jobs"]),
                "skill": SKILLS[c["profession"]],
            }
        )
    catalogs = [
        {
            **c,
            "kind_name": KINDS[c["kind"]],
            "requirements": [{"text": label, "ok": ok} for label, ok in engine.catalog_requirements(s, k)],
            "unlocked": all(ok for _, ok in engine.catalog_requirements(s, k)),
            "occupied": any(p["catalog"] == k and p["status"] in ACTIVE for p in s["projects"])
            or e.catalog_in_market(s, k),
        }
        for k, c in CATALOG.items()
    ]
    weekly_profit = sum(e.expected_sales(s, d)[1] for d in s["products"] if not d["partner"])
    weekly_royalty = sum(d["weekly_royalty"] for d in s["deals"])
    burn = e.costs_per_week(s) - weekly_profit - weekly_royalty
    goals, _ = e.objectives(s)
    return {
        "version": "0.4",
        "date": date(s["week"]),
        "week": s["week"],
        "cash": s["cash"],
        "committed": committed(s),
        "available_cash": s["cash"] - committed(s),
        "runway": int(max(0, s["cash"]) / burn) if burn > 0 else None,
        "payroll": payroll(s),
        "costs_per_week": e.costs_per_week(s),
        "weekly_profit": weekly_profit,
        "weekly_royalty": weekly_royalty,
        "reputation": s["reputation"],
        "knowledge": s["knowledge"],
        "facility": {**FACILITIES[s["facility"]], "level": s["facility"]},
        "next_facility": FACILITIES[s["facility"] + 1] if s["facility"] < 3 else None,
        "headcount": engine.headcount(s),
        "clinical_used": engine.internal_usage(s),
        "lines_used": e.production_lines(s),
        "scenario": s["scenario"],
        "opening": SCENARIOS[s["scenario"]],
        "scenarios": SCENARIOS,
        "goals": goals,
        "objective_done": s["objective_done"],
        "heroes": heroes,
        "roster": roster,
        "catalog": catalogs,
        "projects": [project_view(s, p) for p in s["projects"]],
        "products": s["products"],
        "deals": [{k: v for k, v in d.items() if k != "execution"} for d in s["deals"]],
        "rivals": s["rivals"],
        "orders": e.orders(s),
        "jobs": s["jobs"],
        "journal": s["journal"][-30:],
        "income": s["income"],
        "expense": s["expense"],
        "report": e.report(s),
        "professions": PROFESSIONS,
        "stats": STATS,
        "experiments": EXPERIMENTS,
        "game_over": s["game_over"],
        "career_done": s["career_done"],
        "pending": sum(p["status"] in DECISIONS and not p.get("deferred") for p in s["projects"]),
    }


def phase_preview(s, args):
    simulated = engine.execute(s, "run_phase", args)
    p = next(p for p in simulated["projects"] if p["id"] == args["project"])
    execution = p["execution"]
    return {
        "weeks": execution["weeks"],
        "cost": execution["cost"],
        "chance": chance_range(
            sc.phase_probability(p, execution["key"], execution["plan"], execution["noise_by_stat"])
        ),
        "reserve": simulated["cash"] - committed(simulated),
        "note": "基于现有证据的本阶段估计，后续仍有不确定性；负面结果也会更新判断。",
    }
