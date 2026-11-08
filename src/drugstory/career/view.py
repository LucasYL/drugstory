"""Read-only projection. Hidden candidate properties never enter normal browser state."""

from __future__ import annotations

import math

from . import (
    assist,
    challenge,
    competition,
    development,
    engine,
    gates,
    honors,
    patents,
    product_design,
    rating,
    readouts,
    stories,
    talents,
    trial_choices,
)
from . import economy as e
from . import science as sc
from .content import (
    BUILD,
    CATALOG,
    CLINICAL,
    EXPERIMENTS,
    FACILITIES,
    KINDS,
    PATHS,
    PLANS,
    PROFESSION_ROOM,
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
from .model import ACTIVE, DECISIONS, ability, busy, check, committed, date, make_hero, payroll
from .units import pts, pts_map

recommended_team = assist.recommended_team
chance_range = assist.chance_range

STATUS = {
    "screening": "筛选中",
    "checkpoint": "临床中途决策",
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
            "mean": pts(c["belief"][stat]["mean"]),
            "low": pts(max(0, c["belief"][stat]["mean"] - 1.645 * math.sqrt(c["belief"][stat]["variance"]))),
            "high": pts(c["belief"][stat]["mean"] + 1.645 * math.sqrt(c["belief"][stat]["variance"])),
            "observations": c["belief"][stat]["observations"],
        }
        for stat, name in names.items()
    ]


def shown_result(r):
    return {**r, "values": pts_map(r["values"]), "limits": pts_map(r["limits"])}


def shown_profile(catalog):
    profile = product_design.profile(catalog)
    return {**profile, "limit": pts(profile["limit"])} if profile else None


def patent_view(s, p):
    patent = p.get("patent")
    if not patent or patent["granted"] is False:
        return None
    return {**patent, "expires_label": date(patent["expires"]), "expired": s["week"] >= patent["expires"]}


def whereabouts(s):
    """Where each employed character is and what kind of work they are doing, for scenes."""
    found = {}
    heroes = {h["id"]: h for h in s["heroes"] if h["employed"]}
    for p in s["projects"]:
        if p["status"] not in ("screening", "running", "checkpoint"):
            continue
        key = sc.stage_key(p)
        for hid in p["team"]:
            if hid not in heroes:
                continue
            building = project_scene(p, key)["activity"] == "make"
            room = PROFESSION_ROOM[heroes[hid]["profession"]] if building else STAGES[key]["room"]
            found[hid] = {"room": room, "activity": "make" if building else "test", "task": p["id"]}
    for job in s["jobs"]:
        for hid in job["heroes"]:
            if hid not in heroes:
                continue
            if job["kind"] == "service":
                place, activity = PROFESSION_ROOM[heroes[hid]["profession"]], "service"
            elif job["kind"] == "independent":
                place, activity = "room_clinical", "test"
            else:
                place, activity = "room_academy", "study"
            found[hid] = {"room": place, "activity": activity, "task": job["name"]}
    return found


def project_view(s, p):
    key = sc.stage_key(p)
    ids, mode = recommended_team(s, p)
    estimates = []
    # 方案估计只给等待开工的阶段算；结束和进行中的项目用不到，长局里能省下大部分快照时间
    if p["chosen"] is not None and p["status"] == "ready":
        for plan in PLANS:
            if plan == "focused" and (key not in ("II", "III") or not sc.focused_available(s, p)):
                continue
            execution = sc.plan_phase(s, p, ids, plan, mode)
            estimates.append(
                {
                    **execution,
                    "work": development.expected(p, key, execution["work"]),
                    "name": PLANS[plan]["name"],
                    "text": PLANS[plan]["text"],
                    "chance": chance_range(execution["probability"]),
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
    next_stage = None
    if p["status"] == "result" and key != "review":
        following = project_view(s, {**p, "index": p["index"] + 1, "status": "ready"})
        next_stage = {k: following[k] for k in ("key", "phase", "question", "plans", "recommended", "recommended_mode")}
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
            "feedback",
            "repairs",
            "population",
            "mode",
            "started",
            "ended",
        )
    } | {
        "scene": project_scene(p, key),
        "kind_name": KINDS[p["kind"]],
        "results": [shown_result(r) for r in p["results"]],
        "patent": patent_view(s, p),
        "product_profile": shown_profile(p["catalog"]),
        "design": p.get("design", "standard"),
        "work_focus": p.get("work_focus", "balanced"),
        "work": development.expected(p, p["execution"]["key"], p["execution"]["work"])
        if p.get("execution") and p["status"] in ("running", "checkpoint")
        else [],
        "readings": [
            {
                "stage": r["stage"],
                "stage_name": STAGES[r["stage"]]["name"],
                "candidate": r["candidate"],
                "index": r["index"],
                "week": r["week"],
                "values": pts_map(r["values"]),
            }
            for r in p.get("readings", [])
        ][-16:],
        "interim_chance": chance_range(readouts.forecast(p))
        if p["status"] in ("running", "checkpoint") and readouts.forecast(p) is not None
        else None,
        "trial_decision": trial_choices.view(p),
        "trial_history": p.get("trial_history", []),
        "next_stage": next_stage,
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
        )
        if p["status"] in ACTIVE
        else 0,
        "outlook": chance_range(sc.outlook(p))
        if p["chosen"] is not None and p["status"] in ACTIVE
        else ("尚未选定候选" if p["chosen"] is None else "已结束"),
        "can_focus": sc.focused_available(s, p),
    }


def project_scene(p, key):
    """Only public timing and location, never a preview of future evidence."""
    running = p["status"] in ("screening", "running", "checkpoint")
    experiment = p.get("experiment")
    screening = p["status"] == "screening"
    weeks = 8 if screening else (experiment or p.get("execution") or {}).get("weeks", 0)
    if experiment and experiment["kind"] == "rework":
        weeks = 8
    making = experiment["kind"] in ("refine", "rework") if experiment else screening or key in BUILD
    return {
        "room": STAGES[key]["room"],
        "limits": pts_map(sc.limits(p, key)),
        "activity": ("make" if making else "test") if running else "idle",
        "total": weeks if running else 0,
        "elapsed": max(0, weeks - p["left"]) if running else 0,
        "executor": "cro" if running and key in CLINICAL and p["mode"] == "cro" and not experiment else "internal",
    }


def discovery(s, key, c):
    """组合手记：筛选后才写入；丹尼尔「靶点侦察」在职时立项前就能看到适配档位，叶清和看到机制偏移。"""
    note = s["notebook"].get(key)
    if c["kind"] != "innovative":
        return note
    if note is None and talents.has(s, "scout"):
        note = {"tier": c["combo_tier"], "reason": c["combo_reason"], "week": None, "scouted": True}
    if note is not None and talents.has(s, "star"):
        note = {**note, "mechanism": pts(sc.mechanism(s, c))}
    elif talents.has(s, "star"):
        note = {"tier": None, "reason": None, "week": None, "mechanism": pts(sc.mechanism(s, c))}
    return note


def snapshot(s):
    occupied = busy(s)
    places = whereabouts(s)
    heroes = []
    for h in s["heroes"]:
        if not h["employed"]:
            continue
        spec = ROSTER[h["id"]]
        place = places.get(h["id"], {"room": None, "activity": "idle", "task": None})
        heroes.append(
            {
                **{k: h[k] for k in ("id", "name", "profession", "rank", "xp", "members", "cases", "mentored")},
                "tier": spec["tier"],
                "nickname": spec["nickname"],
                "bio": spec["bio"],
                "look": spec["look"],
                "room": place["room"],
                "activity": place["activity"],
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
                "trait": talents.trait(h["id"]),
                "personal_project": stories.options(s, h),
                "awakened": talents.awakened(h),
                "potential": talents.potential(h),
                "inherited": talents.inherited(h),
                "inherit_to": engine.inherit_options(s, h["id"]),
                "retire_in": (
                    max(0, engine.LEGEND_YEARS * 48 - (s["week"] - h.get("joined", 0))) if h["tier"] == 4 else None
                ),
            }
        )
    roster = []
    for key, c in ROSTER.items():
        if any(h["id"] == key and h["employed"] for h in s["heroes"]):
            continue
        checks = e.recruit_requirements(s, key)
        recruit = make_hero(key)
        roster.append(
            {
                **c,
                "weekly_salary": round(
                    1.3 + recruit["rank"] * 0.65 + ability(recruit) * 0.018 + recruit["members"] * 0.42, 1
                ),
                "profession_name": PROFESSIONS[c["profession"]],
                "rank_name": RANKS[c["tier"]],
                "title": RANKS[c["tier"]] + "·" + c["name"],
                "cost": e.recruit_cost(key),
                "requirements": [{"text": t, "ok": ok} for t, ok in checks],
                "unlocked": all(ok for _, ok in checks),
                "connected": key in s["connections"],
                "connecting": any(j.get("target") == key for j in s["jobs"]),
                "skill": SKILLS[c["profession"]],
                "trait": talents.trait(key),
                "potential": talents.potential(recruit),
            }
        )
    catalogs = [
        {
            **{k: v for k, v in c.items() if k not in ("combo_tier", "combo_reason")},
            "discovery": discovery(s, k, c),
            "gates": gates.view(s, k),
            "kind_name": KINDS[c["kind"]],
            "product_profile": shown_profile(c["key"]),
            "competition": round(competition.pressure(s, c["market"]), 2),
            "announced_rivals": [
                r["name"] for r in s["rivals"] if r["status"] == "developing" and r["pipeline_market"] == c["market"]
            ],
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
        "version": "0.10",
        "api_version": 2,
        "display_scale": 10,
        "event_cursor": s["event_seq"],
        "events": s["events"][-32:],
        "transition_events": s.get("transition_events", []),
        "equipment": development.view(s),
        "notebook": s["notebook"],
        "challenge": challenge.view(s),
        "market_capacity": {k: e.market_capacity(s, k) for k in challenge.CAPACITY},
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
        "next_facility": {
            **FACILITIES[s["facility"] + 1],
            "upkeep": challenge.upkeep({**s, "facility": s["facility"] + 1}),
        }
        if s["facility"] < 3
        else None,
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
        "projects": [
            {
                **project_view(s, p),
                "quick": assist.quick(s, p),
                "advice": assist.advice(s, p),
                "gates": gates.view(s, p["catalog"], p),
            }
            for p in s["projects"]
        ],
        "products": [
            {**d, "patent_expires_label": date(d["exclusive_until"]) if d.get("exclusive_until") else None}
            for d in s["products"]
        ],
        "patents": patents.view(s),
        "deals": [{k: v for k, v in d.items() if k != "execution"} for d in s["deals"]],
        "rivals": competition.public(s),
        "honors": honors.view(s),
        "rating": rating.view(s),
        "work_focuses": development.FOCUSES,
        "orders": e.orders(s),
        "assist": assist.view(s),
        "jobs": s["jobs"],
        "journal": s["journal"][-30:],
        "income": s["income"],
        "expense": s["expense"],
        "report": e.report(s),
        "professions": PROFESSIONS,
        "stats": STATS,
        "experiments": EXPERIMENTS,
        "game_over": s["game_over"],
        "negative_months": s["negative_months"],
        "career_done": s["career_done"],
        "pending": sum(p["status"] in DECISIONS and not p.get("deferred") for p in s["projects"]),
    }


def phase_preview(s, args):
    p = next((p for p in s["projects"] if p["id"] == args["project"]), None)
    check(p is not None, "没有这个研究项目")
    command = "continue_and_run" if p["status"] == "result" else "run_phase"
    simulated = engine.execute(s, command, args)
    p = next(p for p in simulated["projects"] if p["id"] == args["project"])
    execution = p["execution"]
    return {
        "weeks": execution["weeks"],
        "cost": execution["cost"],
        "chance": chance_range(execution["probability"]),
        "work": development.expected(p, execution["key"], execution["work"]),
        "reserve": simulated["cash"] - committed(simulated),
        "note": "基于现有证据的本阶段估计，后续仍有不确定性；负面结果也会更新判断。",
    }
