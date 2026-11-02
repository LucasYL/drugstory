import pytest

from lemonade.rules import COST_PER_CUP, sell


def test_sell_out():
    # 晴天卖 1 元：80 个人想买，只做了 50 杯，全部卖光
    r = sell(50, 100, "sunny")
    assert r.weather == "sunny"
    assert r.cups_made == 50
    assert r.cups_sold == 50
    assert r.revenue == 5000
    assert r.cost == 50 * COST_PER_CUP
    assert r.profit == 2500


def test_made_too_many():
    # 雨天卖 1 元：只有 16 个人想买，做了 50 杯，剩下的倒掉
    r = sell(50, 100, "rainy")
    assert r.cups_made == 50
    assert r.cups_sold == 16
    assert r.revenue == 1600
    assert r.cost == 2500
    assert r.profit == -900  # 亏了


def test_made_nothing():
    r = sell(0, 100, "sunny")
    assert r.cups_sold == 0
    assert r.revenue == 0
    assert r.cost == 0
    assert r.profit == 0


def test_negative_cups():
    with pytest.raises(ValueError):
        sell(-1, 100, "sunny")


def test_bad_price_is_still_rejected():
    # demand() 已经会检查价格了，复用它，别再写一遍
    with pytest.raises(ValueError):
        sell(10, 0, "sunny")


def test_result_cannot_be_changed():
    r = sell(10, 100, "sunny")
    with pytest.raises(AttributeError):
        r.cups_sold = 999
