"""月底结算：工资、月租、破产判定（design/game-design.md 第 10 节）。"""

from __future__ import annotations

from drugstory.content import Content
from drugstory.engine import decisions
from drugstory.engine.book import say, spend
from drugstory.engine.state import GameState
from drugstory.engine.systems.teams import payroll


def month_end(state: GameState, content: Content) -> None:
    spend(state, payroll(state, content), "salary")
    spend(state, content.facility(state.facility).rent, "rent")
    if state.cash >= 0:
        state.negative_months = 0
        state.cash_warned = False
        return
    state.negative_months += 1
    limit = content.balance.finance.bankrupt_months
    if state.negative_months >= limit:
        state.game_over = True
        say(state, f"连续 {limit} 个月现金为负，公司破产了")
        return
    say(state, f"⚠️ 现金为负（¥{state.cash:,} 万），连续 {limit} 个月为负就会破产")
    if not state.cash_warned:
        state.cash_warned = True
        decisions.add(state, decisions.CASH_NEGATIVE, cash=state.cash, months=state.negative_months, limit=limit)
