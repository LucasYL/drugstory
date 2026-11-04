"""上市与销售：峰值、销售曲线、利润率、退市（design/game-design.md 第 9 节）。"""

from __future__ import annotations

from drugstory.content import Content
from drugstory.engine.book import earn, round_half_up, say
from drugstory.engine.state import APPROVED, Drug, GameState, Project
from drugstory.engine.systems.progression import add_proficiency


def peak_sales(state: GameState, project: Project, content: Content) -> float:
    """峰值周销售额，在上市那一刻定下来。"""
    m = content.balance.market
    target = content.targets[project.target]
    modality = content.modalities[project.modality]
    route = m.oral_chronic_bonus if target.chronic and modality.route == "oral" else 1.0
    reputation = 1 + state.reputation / m.reputation_divisor
    return m.base_by_tier[target.market - 1] * (project.composite / 100) ** 2 * reputation * route


def margin(project: Project, content: Content) -> float:
    m = content.balance.market
    review = next(r for r in project.results if r.phase == content.phase_keys[-1])
    return m.margin_base + m.margin_per_point * review.scores["manufacturability"]


def curve(weeks_on_market: int, content: Content) -> float:
    """上市后第 n 周（从 0 开始）的销售额是峰值的几成。"""
    m = content.balance.market
    if weeks_on_market < m.ramp_weeks:
        return (weeks_on_market + 1) / m.ramp_weeks
    if weeks_on_market < m.ramp_weeks + m.plateau_weeks:
        return 1.0
    return (1 - m.decline_rate) ** (weeks_on_market - m.ramp_weeks - m.plateau_weeks + 1)


def launch(state: GameState, project: Project, name: str, content: Content) -> Drug:
    hall = content.balance.scoring.hall_of_fame
    drug = Drug(
        id=state.new_id(),
        project_id=project.id,
        name=name,
        target=project.target,
        modality=project.modality,
        composite=project.composite,
        peak=peak_sales(state, project, content),
        margin=margin(project, content),
        launched_week=state.week,
        hall_of_fame=project.composite >= hall,
    )
    state.drugs.append(drug)
    project.stage = APPROVED
    project.ended_week = state.week
    project.drug_id = drug.id
    state.current_year.approvals += 1

    r = content.balance.reputation
    gain = max(r.approval_min, (project.composite - r.approval_offset) / r.approval_divisor)
    state.reputation = min(float(r.max), state.reputation + gain)
    add_proficiency(state, project, content)
    entry = state.notebook.get(f"{project.target}|{project.modality}")
    if entry is not None:
        entry.best_composite = max(entry.best_composite, project.composite)
    hall_text = "，进入名人堂！" if drug.hall_of_fame else ""
    say(state, f"{name} 获批上市：综合分 {project.composite:.1f}，峰值约 ¥{drug.peak:,.0f} 万/周{hall_text}")
    return drug


def sharing(state: GameState) -> dict[str, int]:
    """每个靶点上同时在卖的药有几个。它们分同一个市场。"""
    counts: dict[str, int] = {}
    for d in state.drugs:
        if d.active:
            counts[d.target] = counts.get(d.target, 0) + 1
    return counts


def step(state: GameState, content: Content) -> None:
    m = content.balance.market
    shares = sharing(state)
    for drug in state.drugs:
        if not drug.active:
            continue
        factor = curve(drug.weeks_on_market, content)
        past_plateau = drug.weeks_on_market >= m.ramp_weeks + m.plateau_weeks
        if past_plateau and factor < m.retire_fraction:
            drug.active = False
            say(state, f"{drug.name} 退市，累计销售 ¥{drug.revenue_total:,} 万")
            continue
        revenue = drug.peak * factor / shares[drug.target]
        earn(state, revenue * drug.margin, "sales")
        revenue_int = round_half_up(revenue)
        drug.revenue_total += revenue_int
        state.current_year.revenue += revenue_int
        drug.weeks_on_market += 1
