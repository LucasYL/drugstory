import pytest

from lemonade.cli import format_money, parse_decision
from lemonade.state import Decision


@pytest.mark.parametrize(
    ("cents", "text"),
    [
        (275, "¥2.75"),
        (2000, "¥20.00"),
        (5, "¥0.05"),
        (0, "¥0.00"),
        (-50, "-¥0.50"),
        (-12345, "-¥123.45"),
    ],
)
def test_format_money(cents, text):
    assert format_money(cents) == text


@pytest.mark.parametrize(
    ("text", "cups", "price"),
    [
        ("30 2.5", 30, 250),
        ("30 2.75", 30, 275),
        ("30 3", 30, 300),
        ("30 2.50", 30, 250),
        ("0 1", 0, 100),
        ("  12    0.5  ", 12, 50),
    ],
)
def test_parse_decision(text, cups, price):
    assert parse_decision(text) == Decision(cups=cups, price=price)


@pytest.mark.parametrize(
    "text",
    [
        "",  # 什么都没输
        "30",  # 少了价格
        "30 2.5 1",  # 多了东西
        "abc 2.5",  # 杯数不是数字
        "2.5 30",  # 杯数不能是小数
        "-5 2",  # 杯数不能是负的
        "30 abc",  # 价格不是数字
        "30 0",  # 价格必须大于 0
        "30 -1",
        "30 2.555",  # 价格最多精确到分
    ],
)
def test_parse_decision_rejects_bad_input(text):
    with pytest.raises(ValueError):
        parse_decision(text)
