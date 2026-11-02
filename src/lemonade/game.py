"""一局游戏：掷骰子决定天气、记住第几天、判断游戏有没有结束。"""

import random

from lemonade.rules import DayResult
from lemonade.state import Decision, GameState, step

START_CASH = 2000  # 开局 20 元
DAYS = 14  # 一局两周
WEATHER_PROBS = {  # 每天天气的概率
    "sunny": 0.5,
    "cloudy": 0.3,
    "rainy": 0.2,
}


class GameOverError(Exception):
    """游戏已经结束了，不能再玩。"""


class Game:
    """一局柠檬水摊。（第 4 课）

    game.state    当前的 GameState
    game.weather  今天的天气
    game.is_over  是不是已经结束了
    """

    def __init__(self, seed: int | None = None, days: int = DAYS, start_cash: int = START_CASH) -> None:
        raise NotImplementedError

    @property
    def weather(self) -> str:
        """今天的天气：早上就知道，读多少次都一样。"""
        raise NotImplementedError

    @property
    def is_over(self) -> bool:
        """days 天都过完了吗？"""
        raise NotImplementedError

    def play(self, decision: Decision) -> DayResult:
        """按玩家的决定过完今天，返回今天的结果。"""
        raise NotImplementedError
