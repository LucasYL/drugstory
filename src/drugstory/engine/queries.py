"""只读的查询，给界面和 bot 用：解锁条件、预估、可选项。不修改状态。"""

from __future__ import annotations

from drugstory.content import Content, Contract
from drugstory.engine.book import round_half_up
from drugstory.engine.rules.combo import tier_name
from drugstory.engine.state import CLINICAL, PHASE_REVIEW, RD_REVIEW, RESEARCH, GameState, NotebookEntry, Project, Team
from drugstory.engine.systems.clinical import phase_plan
from drugstory.engine.systems.contracts import duration, reward
from drugstory.engine.systems.research import rd_weeks


def notebook_entry(state: GameState, target: str, modality: str) -> NotebookEntry | None:
    return state.notebook.get(f"{target}|{modality}")


def known_tier_text(state: GameState, target: str, modality: str, content: Content) -> str:
    entry = notebook_entry(state, target, modality)
    return "没做过" if entry is None else f"{tier_name(entry.tier, content)}（{entry.reason}）"


def rd_estimate(target: str, modality: str, content: Content) -> tuple[int, int]:
    """(研发周数, 研发花费)。"""
    t, m = content.targets[target], content.modalities[modality]
    weeks = rd_weeks(t, m)
    return weeks, round_half_up(weeks * m.weekly_cost)


def clinical_estimate(target: str, modality: str, content: Content) -> tuple[int, int]:
    """(三期临床加审评的总周数, 总花费)。"""
    probe = Project(id=0, target=target, modality=modality, stage="", team_ids=[], rd_weeks=0)
    weeks = cost = 0.0
    for key in content.phase_keys:
        w, c = phase_plan(probe, key, content)
        weeks += w
        cost += c
    return int(weeks), round_half_up(cost)


def committed_costs(state: GameState, content: Content) -> int:
    """所有在研项目接下来还要花的钱：剩下的研发周数，加上还没跑完的临床和审评。"""
    keys = content.phase_keys
    total = 0.0
    for p in state.active_projects:
        m = content.modalities[p.modality]
        if p.stage in (RESEARCH, RD_REVIEW):
            total += max(0, p.rd_weeks - p.rd_done) * m.weekly_cost
            remaining = keys
        elif p.stage == CLINICAL:
            total += p.phase_weeks_left * p.phase_weekly_cost
            remaining = keys[keys.index(p.phase) + 1 :]
        elif p.stage == PHASE_REVIEW:
            remaining = keys[keys.index(p.phase) + 1 :]
        else:
            remaining = []
        for key in remaining:
            total += phase_plan(p, key, content)[1]
    return round_half_up(total)


def modality_unlock_problems(state: GameState, key: str, content: Content) -> list[str]:
    """还差什么才能解锁这种分子类型；空列表表示可以解锁。"""
    m = content.modalities[key]
    if key in state.unlocked_modalities:
        return ["已经解锁"]
    problems = []
    names = {k: v.name for k, v in content.modalities.items()}
    for req, level in m.requires_all:
        if state.modality_proficiency.get(req, 0) < level:
            problems.append(f"需要{names[req]}熟练度 {level} 级")
    if m.requires_any and not any(state.modality_proficiency.get(r, 0) >= lv for r, lv in m.requires_any):
        problems.append("需要" + "或".join(f"{names[r]}熟练度 {lv} 级" for r, lv in m.requires_any))
    if m.requires_facility and content.facility_index(state.facility) < content.facility_index(m.requires_facility):
        problems.append(f"需要场地达到{content.facility(m.requires_facility).name}")
    if state.data < m.unlock:
        problems.append(f"需要 {m.unlock} 研究数据")
    return problems


def target_unlock_problems(state: GameState, key: str, content: Content) -> list[str]:
    t = content.targets[key]
    if key in state.unlocked_targets:
        return ["已经解锁"]
    return [] if state.data >= t.unlock else [f"需要 {t.unlock} 研究数据"]


def next_facility(state: GameState, content: Content):
    index = content.facility_index(state.facility) + 1
    facilities = content.balance.facilities
    return facilities[index] if index < len(facilities) else None


def eligible_teams(state: GameState, contract: Contract) -> list[Team]:
    return [t for t in state.idle_teams if t.lead.attr(contract.attr) >= contract.requirement]


def contract_terms(team: Team, contract: Contract, content: Content) -> tuple[int, int]:
    """(工期, 报酬)。"""
    return duration(team, contract, content), reward(team, contract, content)
