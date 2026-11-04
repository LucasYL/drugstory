"""主循环：按固定顺序推进一周（design/tech.md 第 5 节）。"""

from __future__ import annotations

from drugstory.content import Content
from drugstory.engine.state import GameState
from drugstory.engine.systems import (
    clinical,
    contracts,
    finance,
    licensing,
    market,
    progression,
    recruiting,
    research,
    world,
)


def step_week(state: GameState, content: Content) -> None:
    if state.game_over:
        return
    world.step(state, content)
    research.step(state, content)
    contracts.step(state, content)
    clinical.step(state, content)
    licensing.step(state, content)
    market.step(state, content)
    recruiting.step(state, content)
    state.week += 1
    t = content.balance.time
    if state.week % t.weeks_per_month == 0:
        finance.month_end(state, content)
        if state.game_over:
            return
        contracts.refresh_offers(state, content)
    if state.week % t.weeks_per_year == 0:
        progression.year_end(state, content)
    progression.check_achievements(state, content)


def advance(state: GameState, content: Content, max_weeks: int) -> int:
    """一周一周往前推，出现需要玩家决定的事就停。返回实际推进了几周。"""
    weeks = 0
    while weeks < max_weeks and not state.pending and not state.game_over:
        step_week(state, content)
        weeks += 1
    return weeks
