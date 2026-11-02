"""游戏状态，以及「过一天」的状态转移。"""

from dataclasses import dataclass

from lemonade.rules import COST_PER_CUP, DayResult, sell


class NotEnoughCashError(Exception):
    """钱不够做这么多杯。"""


@dataclass(frozen=True)
class GameState:
    """某一天早上的局面。（第 3 课）"""

    # TODO：day（第几天，从 1 开始）、cash（现金，单位是分）


@dataclass(frozen=True)
class Decision:
    """玩家每天早上做的决定。（第 3 课）"""

    # TODO：cups（做几杯）、price（每杯卖多少分）


def step(state: GameState, decision: Decision, weather: str) -> tuple[GameState, DayResult]:
    """过一天：返回 (新的状态, 今天的结果)。不能修改传进来的 state。（第 3 课）"""
    raise NotImplementedError
