"""项目授权：首付款、合作方逐期开发、成功里程碑与销售分成。"""
from __future__ import annotations

from drugstory.content import Content
from drugstory.engine.book import earn, round_half_up, say
from drugstory.engine.rules.scoring import composite, project_scores
from drugstory.engine.rules.texts import project_label
from drugstory.engine.state import PHASE_REVIEW, RD_REVIEW, Drug, GameState, Project
from drugstory.engine.systems import clinical, market
from drugstory.engine.systems.world import pressure


def offer(state: GameState, project: Project, content: Content, kind: str) -> dict:
    terms = content.balance.license_types[kind]
    b = content.balance.licensing
    stage_ok = project.stage == RD_REVIEW or (project.stage == PHASE_REVIEW and project.phase == "II")
    scores = project_scores(project, "NDA", state.week, content)
    efficacy = project_scores(project, "III", state.week, content)["efficacy"]
    quality = min(1.2, sum(scores.values()) / 28)
    profile = content.balance.profiles[project.profile]
    market_factor = (0.7 + 0.1 * content.targets[project.target].market) * profile.market_factor
    if project.strategy_chosen:
        market_factor *= content.balance.clinical_strategies[project.clinical_strategy].market_factor
    share = 1 / (1 + market.sharing(state, content).get(project.target, pressure(state, project.target, content)))
    market_factor *= share
    base = b.rd_value if project.stage == RD_REVIEW else b.phase2_value
    problem = ""
    if not stage_ok or project.deal_id:
        problem = "仅可在研发结束或 II 期成功后授权"
    elif efficacy < b.min_efficacy or sum(scores.values()) < b.min_review_total:
        problem = f"报价要求：III 期疗效预估 ≥{b.min_efficacy}、审评合计 ≥{b.min_review_total}；请先补齐质量"
    return {"kind": kind, "name": terms.name, "description": terms.description,
            "partner": b.partners[(state.seed + project.id) % len(b.partners)],
            "upfront": round_half_up(base * quality * market_factor * terms.upfront_factor),
            "milestone": round_half_up(b.milestone * quality * market_factor),
            "royalty_rate": terms.royalty_rate, "problem": problem, "market_share": share,
            "remaining_weeks": sum(clinical.phase_plan(project, k, content)[0]
                                   for k in content.phase_keys[(2 if project.stage == PHASE_REVIEW else 0):])}


def step(state: GameState, content: Content) -> None:
    for deal in state.deals:
        if deal.status != "developing":
            continue
        p = state.project(deal.project_id)
        deal.weeks_left -= 1
        if deal.weeks_left > 0:
            continue
        result = clinical.evaluate_phase(state, p, deal.phase, content, stream="partners")
        p.results.append(result)
        name = project_label(p, content)
        if not result.passed:
            deal.status = "failed"
            say(state, f"授权进展：{deal.partner}的 {name} 在 {content.phase(deal.phase).name} 失败；"
                "已收首付款保留，不再产生上市里程碑或销售分成")
        elif deal.phase == content.phase_keys[-1]:
            p.composite = composite(p.results, content)
            deal.status = "marketed"
            deal.milestone_paid = True
            earn(state, deal.milestone, "license_milestones")
            state.reputation = min(float(content.balance.reputation.max), state.reputation + 2)
            deal.drug = Drug(id=state.new_id(), project_id=p.id, name=f"{deal.partner} · {name}", target=p.target,
                             modality=p.modality, composite=p.composite, peak=market.peak_sales(state, p, content),
                             margin=market.margin(p, content), launched_week=state.week)
            say(state, f"授权药获批：{name}，收到里程碑 ¥{deal.milestone:,} 万，"
                f"开始收取销售额 {deal.royalty_rate:.0%} 的分成")
        else:
            keys = content.phase_keys
            deal.phase = keys[keys.index(deal.phase) + 1]
            deal.weeks_left = clinical.phase_plan(p, deal.phase, content)[0]
            say(state, f"授权进展：{deal.partner}的 {name} 通过 {content.phase(result.phase).name}，"
                f"进入 {content.phase(deal.phase).name}；费用由合作方承担")
