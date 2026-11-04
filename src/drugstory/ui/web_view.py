"""只读的网页视图；数值、预估和可用操作都来自同一个游戏引擎。"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass, replace
from typing import Any

from drugstory.content import ACTIONS, ATTRS, STATS, Content, Section
from drugstory.engine.calendar import label
from drugstory.engine.queries import (
    clinical_estimate,
    committed_costs,
    contract_terms,
    eligible_teams,
    known_tier_text,
    modality_unlock_problems,
    next_facility,
    rd_estimate,
    target_unlock_problems,
)
from drugstory.engine.rules.combo import compat, multiplier, tier_name
from drugstory.engine.rules.scoring import passed, project_scores, score_noise
from drugstory.engine.rules.texts import project_label
from drugstory.engine.save import to_data
from drugstory.engine.state import CLINICAL, PHASE_REVIEW, QUEUED, RD_REVIEW, RESEARCH, GameState, Project
from drugstory.engine.systems.clinical import operations, phase_plan, unresolved_hazards
from drugstory.engine.systems.licensing import offer as license_offer
from drugstory.engine.systems.market import curve, sharing
from drugstory.engine.systems.progression import final_score
from drugstory.engine.systems.research import (
    extensions_used,
    milestone_plan,
    point_multiplier,
    project_gain,
    project_teams,
)
from drugstory.engine.systems.teams import (
    capacity,
    exp_to_next,
    lead_salary,
    payroll,
    size_factor,
    team_salary,
    training_cap,
    training_cost,
    weekly_output,
)
from drugstory.engine.systems.world import objective, pressure


def plain(value: Any) -> Any:
    if is_dataclass(value):
        return plain(asdict(value))
    if isinstance(value, (dict, Section)):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [plain(v) for v in value]
    return value


def forecasts(state: GameState, p: Project, content: Content) -> list[dict]:
    """用现有属性、各期预计结束时的标准预估，避免跨年时过于乐观。"""
    keys = content.phase_keys
    week = state.week
    if p.stage in (RESEARCH, RD_REVIEW, QUEUED):
        week += max(0, p.rd_weeks - p.rd_done)
    elif p.stage == CLINICAL:
        keys = keys[keys.index(p.phase):]
    elif p.stage == PHASE_REVIEW:
        keys = keys[keys.index(p.phase) + 1:]
    else:
        return []
    out = []
    for key in keys:
        duration, cost = phase_plan(p, key, content)
        if p.stage == CLINICAL and key == p.phase:
            duration = p.phase_weeks_left
            cost = duration * p.phase_weekly_cost
        week += duration
        phase = content.phase(key)
        scores = project_scores(p, key, max(0, week - 1), content)
        low = {k: max(content.balance.scoring.min_score, v - score_noise(p, key, content))
               for k, v in scores.items()}
        out.append({
            "key": key, "name": phase.name, "weeks": duration, "cost": cost,
            "finish": "排队时间未计入" if p.stage == QUEUED else label(max(0, week - 1), content), "scores": scores,
            "passed": passed(key, scores, content), "requirements": plain(phase.pass_),
            "total_required": phase.pass_total,
            "margin_ok": passed(key, low, content) and not unresolved_hazards(p),
        })
    return out


def route_info(target: str, modality: str, content: Content) -> dict:
    tier, reason = compat(content.targets[target], content.modalities[modality], content)
    return {"tier": tier, "name": tier_name(tier, content), "reason": reason,
            "multiplier": multiplier(tier, content), "allowed": tier > -2}


def snapshot(state: GameState, content: Content) -> dict:
    s, c = state, content
    names = c.texts.names
    current = c.facility(s.facility)
    overhead = payroll(s, c) + current.rent
    committed = committed_costs(s, c)
    ops = operations(s, c)
    shares = sharing(s, c)
    drugs = []
    for drug in s.drugs:
        gross = drug.peak * curve(drug.weeks_on_market, c) / shares[drug.target] if drug.active else 0
        drugs.append({
            **to_data(drug), "label": f"{c.targets[drug.target].name} × {c.modalities[drug.modality].name}",
            "weekly_sales": gross, "weekly_profit": gross * drug.margin,
        })
    projects = []
    for p in s.projects:
        data = to_data(p)
        data["hazards"] = [to_data(h) for h in unresolved_hazards(p)]
        for hazard in data["hazards"]:
            hazard.pop("phase", None)  # 留住临床揭晓的未知信息
        used = extensions_used(p, c)
        gains = {stat: project_gain(
            p, stat, sum(weekly_output(t, stat, c) for t in project_teams(s, p))
            * point_multiplier(s, p, c) * c.balance.research.extension_weeks, c,
        ) for stat in STATS}
        polished = replace(p, stats={k: v + gains[k] for k, v in p.stats.items()},
                           rd_weeks=p.rd_weeks + c.balance.research.extension_weeks)
        future = forecasts(s, p, c)
        operating_reserve = sum(f["weeks"] for f in future) * overhead / c.balance.time.weeks_per_month
        projects.append({
            **data, "label": project_label(p, c), "active": p.active,
            "phase_name": c.phase(p.phase).name if p.phase else "研发",
            "profile_info": plain(c.balance.profiles[p.profile]),
            "strategy_info": plain(c.balance.clinical_strategies[p.clinical_strategy]),
            "license_offers": [license_offer(s, p, c, k) for k in c.balance.license_types]
            if p.stage == RD_REVIEW or (p.stage == PHASE_REVIEW and p.phase == "II") else [],
            "known_tier": known_tier_text(s, p.target, p.modality, c),
            "forecasts": future, "weekly_cost": c.modalities[p.modality].weekly_cost,
            "operating_reserve": operating_reserve,
            "cash_after_reserve": s.cash - committed - operating_reserve,
            "queue_position": ops["queue"].index(p.id) + 1 if p.id in ops["queue"] else 0,
            "contract_cost": sum(phase_plan(replace(p, clinical_mode="contract"), k, c)[1] for k in c.phase_keys),
            "validation": {"cost": len(p.hazards) * c.balance.research.final_validation_cost,
                           "weeks": c.balance.research.validate_weeks,
                           "available": bool(p.hazards and p.team_ids)
                           and p.validation_count < c.balance.research.max_validations,
                           "remaining": max(0, c.balance.research.max_validations - p.validation_count)},
            "route": route_info(p.target, p.modality, c),
            "quality_knee": c.balance.scoring.base_standard * c.targets[p.target].difficulty
            * c.balance.research.quality_knee,
            "polish": {"used": used, "limit": c.balance.research.max_extensions,
                       "remaining": max(0, c.balance.research.max_extensions - used),
                       "gains": gains, "forecasts": forecasts(s, polished, c),
                       "cash_cost": c.balance.research.extension_weeks
                       * (c.modalities[p.modality].weekly_cost + overhead / c.balance.time.weeks_per_month)},
        })
    teams = []
    for t in s.teams:
        task = "空闲"
        if t.task == "project":
            task = project_label(s.project(t.task_id), c)
        elif t.task == "contract":
            contract = next(x for x in s.contracts if x.id == t.task_id)
            task = f"{c.contracts[contract.kind].name} · 还剩 {contract.weeks_left} 周"
        teams.append({
            **to_data(t), "specialty": t.lead.specialty, "type": names.teams[t.lead.specialty],
            "trait": plain(c.balance.traits[t.lead.trait]),
            "task_label": task, "salary": team_salary(t, c), "exp_next": exp_to_next(t.lead, c),
            "size_factor": size_factor(t, c),
            "weekly_output": {stat: weekly_output(t, stat, c) for stat in STATS},
            "training_caps": {a: training_cap(t.lead, a, c) for a in ATTRS},
            "training": {a: dict(zip(("cost", "data"), training_cost(t.lead, a, c), strict=True)) for a in ATTRS},
            "severance": lead_salary(t.lead, c) + t.members * c.balance.team.member_severance,
        })
    pending = []
    for d in s.pending:
        item = to_data(d)
        if d.kind == "phase_result" and not d.data["passed"]:
            result = s.project(d.project_id).results[-1]
            phase = c.phase(result.phase)
            item["failure_reasons"] = [
                f"{names.stats[stat]} {result.scores[stat]} 分，门槛 ≥{line} 分"
                for stat, line in phase.pass_.items() if result.scores[stat] < line
            ]
            total = sum(result.scores.values())
            if total < phase.pass_total:
                item["failure_reasons"].append(f"合计 {total} 分，门槛 ≥{phase.pass_total} 分")
        if d.kind == "phase_result" and d.data["passed"] and s.project(d.project_id).phase == "I":
            p = s.project(d.project_id)
            if not p.strategy_chosen:
                item["strategies"] = []
                for key, strategy in c.balance.clinical_strategies.items():
                    variant = replace(p, clinical_strategy=key, strategy_chosen=True)
                    rows = forecasts(s, variant, c)
                    item["strategies"].append({"key": key, **plain(strategy), "forecasts": rows,
                                               "remaining_cost": sum(f["cost"] for f in rows),
                                               "remaining_weeks": sum(f["weeks"] for f in rows)})
        if d.kind == "milestone":
            p = s.project(d.project_id)
            item["options"] = [
                {"team_id": t.id, "name": t.lead.name, "type": names.teams[t.lead.specialty],
                 "trait": plain(c.balance.traits[t.lead.trait]),
                 "plans": {key: milestone_plan(s, p, t, key, c) for key in ("boost", "validate", "fast")}}
                for t in project_teams(s, p)
            ]
        if d.kind == "candidates" and s.recruitment:
            item["candidates"] = [
                {**to_data(lead), "type": names.teams[lead.specialty], "salary": lead_salary(lead, c),
                 "trait_info": plain(c.balance.traits[lead.trait]),
                 "fee": lead_salary(lead, c) * c.balance.recruiting.signing_months}
                for lead in s.recruitment.candidates
            ]
        pending.append(item)
    targets = []
    for t in c.targets.values():
        locations = {"secreted": "胞外分泌", "surface": "细胞表面", "intracellular": "细胞内", "nucleic": "基因层面"}
        pockets = {"yes": "有口袋", "hard": "口袋很难做", "no": "没有口袋"}
        intervention = "、".join(names.actions[a] for a in ACTIONS if a in t.actions)
        targets.append({
            "key": t.key, "name": t.name, "disease": t.disease, "market": t.market,
            "difficulty": t.difficulty, "unlock": t.unlock, "unlocked": t.key in s.unlocked_targets,
            "problems": target_unlock_problems(s, t.key, c), "proficiency": s.target_proficiency.get(t.key, 0),
            "tags": f"{locations[t.location]} · {pockets[t.pocket]} · {intervention} · {names.tissues[t.tissue]}",
        })
    modalities = [{
        "key": m.key, "name": m.name, "route": m.route_name, "unlock": m.unlock,
        "unlocked": m.key in s.unlocked_modalities, "problems": modality_unlock_problems(s, m.key, c),
        "proficiency": s.modality_proficiency.get(m.key, 0),
    } for m in c.modalities.values()]
    estimates = {}
    for t in s.unlocked_targets:
        for m in s.unlocked_modalities:
            rd_w, rd_cost = rd_estimate(t, m, c)
            clinical_w, clinical_cost = clinical_estimate(t, m, c)
            operating = (rd_w + clinical_w) * overhead / c.balance.time.weeks_per_month
            estimates[f"{t}|{m}"] = {
                "rd_weeks": rd_w, "rd_cost": rd_cost, "clinical_weeks": clinical_w,
                "clinical_cost": clinical_cost, "known_tier": known_tier_text(s, t, m, c),
                "route": route_info(t, m, c),
                "operating_reserve": operating,
                "cash_after_reserve": s.cash - committed - rd_cost - clinical_cost - operating,
                "same_target_drugs": [d.name for d in s.drugs if d.active and d.target == t],
                "rivals": [{"name": r.name, "launch": label(r.launch_week, c), "active": r.launched}
                           for r in s.rivals if r.target == t],
                "market_share": 1 / (1 + shares.get(t, pressure(s, t, c))),
            }
    offers = []
    for offer in s.offers:
        contract = c.contracts[offer.kind]
        offers.append({
            **plain(contract), "id": offer.id, "attr_name": names.attrs[contract.attr],
            "teams": [{"id": t.id, "name": t.lead.name,
                       "weeks": contract_terms(t, contract, c)[0], "reward": contract_terms(t, contract, c)[1]}
                      for t in eligible_teams(s, contract)],
        })
    project_burn = sum(
        c.modalities[p.modality].weekly_cost if p.stage == RESEARCH and p.team_ids
        else p.phase_weekly_cost if p.stage == CLINICAL else 0 for p in s.active_projects
    )
    deals = []
    for deal in s.deals:
        drug = deal.drug
        royalty = (drug.peak * curve(drug.weeks_on_market, c) / shares[drug.target] * deal.royalty_rate
                   if drug and drug.active else 0)
        deals.append({**to_data(deal), "label": project_label(s.project(deal.project_id), c),
                      "phase_name": c.phase(deal.phase).name, "weekly_royalty": royalty})
    weekly_royalties = sum(d["weekly_royalty"] for d in deals)
    weekly_net_cost = project_burn + overhead / c.balance.time.weeks_per_month - sum(
        d["weekly_profit"] for d in drugs
    ) - weekly_royalties
    return {
        "week": s.week, "date": label(s.week, c), "seed": s.seed, "cash": s.cash, "data": s.data,
        "reputation": s.reputation, "headcount": s.headcount, "capacity": capacity(s, c),
        "committed": committed, "uncommitted": s.cash - committed, "monthly_overhead": overhead,
        "weekly_project_cost": project_burn, "weekly_sales_profit": sum(d["weekly_profit"] for d in drugs),
        "cash_weeks": max(0, s.cash) / weekly_net_cost if weekly_net_cost > 0 else None,
        "facility": plain(current), "next_facility": plain(next_facility(s, c)),
        "game_over": s.game_over, "career_done": s.career_done, "score": final_score(s, c),
        "projects": projects, "teams": teams, "drugs": drugs, "pending": pending,
        "recruitment": to_data(s.recruitment), "channels": plain(c.balance.recruiting.channels),
        "targets": targets, "modalities": modalities, "estimates": estimates, "offers": offers,
        "contracts": [{**to_data(x), "name": c.contracts[x.kind].name} for x in s.contracts],
        "notebook": [{**to_data(v), "label": f"{c.targets[k.split('|')[0]].name} × "
                     f"{c.modalities[k.split('|')[1]].name}", "tier_name": names.tiers[str(v.tier)]}
                    for k, v in s.notebook.items()],
        "achievements": [{"key": k, **plain(v), "earned": k in s.achievements}
                         for k, v in c.texts.achievements.items()],
        "years": to_data(s.years),
        "messages": [{"date": label(m.week, c), **to_data(m)} for m in s.messages[-80:]],
        "names": plain(names), "team_rules": plain(c.balance.team),
        "extension_weeks": c.balance.research.extension_weeks,
        "training_gain": c.balance.growth.training_gain,
        "clinical_operations": ops, "edition": "下一版 v0.3",
        "profiles": plain(c.balance.profiles), "scenarios": plain(c.balance.scenarios),
        "scenario": s.scenario, "objective": objective(s, c), "deals": deals,
        "weekly_royalties": weekly_royalties, "income": dict(s.income),
        "rivals": [{**to_data(r), "target_name": c.targets[r.target].name,
                    "launch_date": label(r.launch_week, c), "remaining": max(0, r.launch_week - s.week),
                    "market_share": 1 / (1 + shares.get(r.target, pressure(s, r.target, c)))} for r in s.rivals],
    }
