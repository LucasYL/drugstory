import pytest

from lemonade.state import Decision, GameState, NotEnoughCashError, step


def test_one_day_passes():
    state = GameState(day=1, cash=2000)
    new_state, result = step(state, Decision(cups=20, price=100), "sunny")
    # 成本 20 × 50 = 1000，20 杯全卖光收入 2000，赚 1000
    assert result.profit == 1000
    assert new_state.day == 2
    assert new_state.cash == 3000


def test_losing_money():
    state = GameState(day=3, cash=3000)
    new_state, result = step(state, Decision(cups=40, price=100), "rainy")
    # 成本 2000，只卖出 16 杯，收入 1600，亏 400
    assert result.profit == -400
    assert new_state.day == 4
    assert new_state.cash == 2600


def test_original_state_is_untouched():
    state = GameState(day=1, cash=2000)
    step(state, Decision(cups=20, price=100), "sunny")
    assert state == GameState(day=1, cash=2000)


def test_not_enough_cash():
    # 41 杯要 2050 分，手里只有 2000
    with pytest.raises(NotEnoughCashError):
        step(GameState(day=1, cash=2000), Decision(cups=41, price=100), "sunny")


def test_exactly_enough_cash():
    # 40 杯正好 2000 分。晴天卖 1 元有 80 人想买，40 杯全卖光，收入 4000
    new_state, _ = step(GameState(day=1, cash=2000), Decision(cups=40, price=100), "sunny")
    assert new_state.cash == 4000


def test_states_and_decisions_are_frozen():
    state = GameState(day=1, cash=2000)
    with pytest.raises(AttributeError):
        state.cash = 1_000_000
    decision = Decision(cups=10, price=100)
    with pytest.raises(AttributeError):
        decision.cups = 0
