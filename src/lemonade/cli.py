"""命令行界面：整个项目里只有这个文件用 print 和 input。"""

from lemonade.game import DAYS, Game
from lemonade.rules import DayResult
from lemonade.state import Decision, GameState, NotEnoughCashError

WEATHER_NAMES = {"sunny": "☀️ 晴", "cloudy": "⛅ 多云", "rainy": "🌧️ 雨"}


def format_money(cents: int) -> str:
    """把分显示成元：275 -> "¥2.75"，-50 -> "-¥0.50"。（第 5 课）"""
    raise NotImplementedError


def parse_decision(text: str) -> Decision:
    """把玩家输入的 "30 2.5" 解析成 Decision(cups=30, price=250)。（第 5 课）"""
    raise NotImplementedError


def format_report(result: DayResult, state: GameState) -> str:
    """把一天的结果排成给玩家看的几行字。state 是这一天结束之后的状态。（第 6 课）"""
    raise NotImplementedError


def main(seed: int | None = None, days: int = DAYS) -> None:
    """游戏主循环。（第 6 课）"""
    raise NotImplementedError
