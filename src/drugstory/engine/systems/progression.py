"""成长：熟练度、成就、年报、20 年结算（design/game-design.md 6.3、第 11 节）。"""

from __future__ import annotations

from collections.abc import Callable

from drugstory.content import Content
from drugstory.engine import decisions
from drugstory.engine.book import say
from drugstory.engine.state import GameState, Project, YearStats


def add_proficiency(state: GameState, project: Project, content: Content) -> None:
    cap = content.balance.research.max_proficiency
    for table, key in ((state.modality_proficiency, project.modality), (state.target_proficiency, project.target)):
        table[key] = min(cap, table.get(key, 0) + 1)


def total_profit(state: GameState) -> int:
    return sum(state.income.values()) - sum(state.expense.values())


def final_score(state: GameState, content: Content) -> dict[str, int]:
    f = content.balance.final_score
    profit = total_profit(state)
    approvals = len(state.drugs)
    hall = sum(d.hall_of_fame for d in state.drugs)
    achievements = len(state.achievements)
    score = (
        profit / 10000 * f.per_100m_profit
        + approvals * f.per_approval
        + hall * f.per_hall_of_fame
        + achievements * f.per_achievement
    )
    return {
        "profit": profit,
        "approvals": approvals,
        "hall_of_fame": hall,
        "achievements": achievements,
        "score": round(score),
    }


def year_end(state: GameState, content: Content) -> None:
    ys = state.current_year
    decisions.add(
        state,
        decisions.YEAR_END,
        year=ys.year,
        revenue=ys.revenue,
        income=ys.income,
        expense=ys.expense,
        approvals=ys.approvals,
        failures=ys.failures,
        cash=state.cash,
        reputation=round(state.reputation, 1),
    )
    if ys.year >= content.balance.time.career_years and not state.career_done:
        state.career_done = True
        decisions.add(state, decisions.GAME_END, **final_score(state, content))
    state.years.append(YearStats(year=ys.year + 1))


def _checks(state: GameState, content: Content) -> dict[str, Callable[[], bool]]:
    a = content.balance.achievements
    return {
        "first_approval": lambda: bool(state.drugs),
        "perfect_match": lambda: any(e.tier == 2 for e in state.notebook.values()),
        "hall_of_fame": lambda: any(d.hall_of_fame for d in state.drugs),
        "revenue_100m": lambda: any(y.revenue >= a.revenue_100m for y in state.years),
        "revenue_1b": lambda: any(y.revenue >= a.revenue_1b for y in state.years),
        "staff_100": lambda: state.headcount > a.staff,
        "pipeline_5": lambda: len(state.active_projects) >= a.pipeline,
        "all_modalities": lambda: len(state.unlocked_modalities) == len(content.modalities),
        "rare_disease": lambda: any(content.targets[d.target].category == "rare" for d in state.drugs),
        "alzheimer": lambda: any(d.hall_of_fame and d.target == a.alzheimer_target for d in state.drugs),
    }


def check_achievements(state: GameState, content: Content) -> None:
    for key, check in _checks(state, content).items():
        if key not in state.achievements and check():
            state.achievements.append(key)
            say(state, f"🏆 成就达成：{content.texts.achievements[key].name}")
