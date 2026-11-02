"""游戏规则：全是纯函数。不碰随机数，不碰输入输出，同样的输入永远得到同样的输出。"""

from dataclasses import dataclass

# ---- 数值：相当于策划给你的表 ----
# 钱一律用「分」（整数）表示，50 就是 0.5 元。为什么？见第 1 课最后的「做完再看」。
COST_PER_CUP = 50  # 每杯的成本
MAX_PRICE = 500  # 卖到 5 元，就一个客人都没有了
BASE_CUSTOMERS = {  # 价格极低时，不同天气会来多少客人
    "sunny": 100,
    "cloudy": 60,
    "rainy": 20,
}


def demand(price: int, weather: str) -> int:
    """在这个天气、这个价格（分）下，有多少客人想买。（第 1 课）"""
    raise NotImplementedError


@dataclass(frozen=True)
class DayResult:
    """一天营业的结果。（第 2 课）"""

    # TODO 第 2 课：在这里加上字段 weather, cups_made, cups_sold, revenue, cost, profit


def sell(cups: int, price: int, weather: str) -> DayResult:
    """早上做了 cups 杯、每杯卖 price 分，在这个天气下卖一天。（第 2 课）"""
    raise NotImplementedError
