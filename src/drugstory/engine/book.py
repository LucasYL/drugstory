"""账本和消息：所有的进账、支出都走这里，所以总能核对"现金 = 开局资金 + 进账 − 支出"。"""

from __future__ import annotations

import math

from drugstory.engine.state import GameState, Message

MAX_MESSAGES = 200


def round_half_up(x: float) -> int:
    """四舍五入（Python 自带的 round 是"四舍六入五成双"）。"""
    return math.floor(x + 0.5)


def earn(state: GameState, amount: float, category: str) -> int:
    value = round_half_up(amount)
    state.cash += value
    state.income[category] = state.income.get(category, 0) + value
    state.current_year.income += value
    return value


def spend(state: GameState, amount: float, category: str) -> int:
    value = round_half_up(amount)
    state.cash -= value
    state.expense[category] = state.expense.get(category, 0) + value
    state.current_year.expense += value
    return value


def can_afford(state: GameState, amount: float) -> bool:
    return state.cash >= round_half_up(amount)


def say(state: GameState, text: str) -> None:
    state.messages.append(Message(state.week, text))
    if len(state.messages) > MAX_MESSAGES:
        del state.messages[: len(state.messages) - MAX_MESSAGES]
