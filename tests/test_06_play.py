from lemonade import cli
from lemonade.rules import sell
from lemonade.state import GameState


def fake_input(*lines):
    """假装是玩家：按顺序返回这些输入。"""
    remaining = iter(lines)

    def _input(prompt=""):
        try:
            return next(remaining)
        except StopIteration:
            raise AssertionError("main() 要的输入比预期多：游戏是不是该结束的时候没结束？") from None

    return _input


def test_report_shows_the_numbers():
    result = sell(60, 250, "sunny")  # 晴天卖 2.5 元：50 人想买，做了 60 杯
    report = cli.format_report(result, GameState(day=2, cash=12000))
    assert "晴" in report
    assert "60" in report  # 做了几杯
    assert "50" in report  # 卖出几杯
    assert "¥125.00" in report  # 收入
    assert "¥30.00" in report  # 成本
    assert "¥95.00" in report  # 利润
    assert "¥120.00" in report  # 现在的现金


def test_full_game(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", fake_input("10 2.5", "10 2.5", "10 2.5"))
    cli.main(seed=1, days=3)
    out = capsys.readouterr().out
    assert "游戏结束" in out
    assert "❌" not in out


def test_bad_input_asks_again(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", fake_input("你好", "10 2.5", "9999 2.5", "10 2.5"))
    cli.main(seed=1, days=2)
    out = capsys.readouterr().out
    assert out.count("❌") == 2  # 两次坏输入（看不懂、钱不够），各提示一次
    assert "游戏结束" in out
