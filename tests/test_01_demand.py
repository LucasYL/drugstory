import pytest

from lemonade.rules import BASE_CUSTOMERS, MAX_PRICE, demand


def test_sunny_day():
    # 100 个基础客人，卖 1 元：100 × (500 − 100) ÷ 500 = 80
    assert demand(100, "sunny") == 80


def test_cloudy_day():
    assert demand(250, "cloudy") == 30


def test_rainy_day():
    assert demand(100, "rainy") == 16


def test_rounds_down():
    # 100 × 499 ÷ 500 = 99.8，半个客人不算客人
    assert demand(1, "sunny") == 99


def test_nobody_buys_at_max_price():
    assert demand(MAX_PRICE, "sunny") == 0


def test_never_negative():
    assert demand(800, "sunny") == 0


def test_higher_price_never_brings_more_customers():
    for weather in BASE_CUSTOMERS:
        for price in range(1, MAX_PRICE + 100):
            assert demand(price + 1, weather) <= demand(price, weather)


@pytest.mark.parametrize("price", [0, -100])
def test_price_must_be_positive(price):
    with pytest.raises(ValueError):
        demand(price, "sunny")


def test_unknown_weather():
    with pytest.raises(ValueError):
        demand(100, "snowy")
