from collections import Counter

import pytest

from lemonade.game import START_CASH, WEATHER_PROBS, Game, GameOverError
from lemonade.state import Decision, NotEnoughCashError


def nothing():
    return Decision(cups=0, price=100)  # 一杯都不做，只看天气


def too_many():
    return Decision(cups=1_000_000, price=100)  # 钱肯定不够


def test_new_game():
    game = Game(seed=1)
    assert game.state.day == 1
    assert game.state.cash == START_CASH
    assert game.weather in WEATHER_PROBS
    assert not game.is_over
    assert Game(seed=1, start_cash=500).state.cash == 500


def test_reading_weather_changes_nothing():
    game = Game(seed=1)
    assert len({game.weather for _ in range(20)}) == 1


def test_play_one_day():
    game = Game(seed=1)
    weather = game.weather
    result = game.play(Decision(cups=10, price=100))
    assert result.weather == weather  # 早上看到的天气，就是今天的天气
    assert game.state.day == 2
    assert game.state.cash == START_CASH + result.profit


def test_same_seed_same_story():
    decisions = [Decision(cups=c, price=p) for c, p in [(10, 100), (20, 150), (5, 300)] * 4]

    def play_all(seed):
        game = Game(seed=seed, days=len(decisions))
        return [game.play(d) for d in decisions], game.state

    assert play_all(42) == play_all(42)


def test_different_seeds_different_weather():
    def weathers(seed):
        game = Game(seed=seed, days=50)
        return [game.play(nothing()).weather for _ in range(50)]

    assert weathers(1) != weathers(2)


def test_weather_follows_probabilities():
    days = 10_000
    game = Game(seed=7, days=days)
    counts = Counter(game.play(nothing()).weather for _ in range(days))
    for weather, p in WEATHER_PROBS.items():
        assert abs(counts[weather] / days - p) < 0.03


def test_failed_play_changes_nothing():
    for seed in range(10):
        game = Game(seed=seed)
        weather, state = game.weather, game.state
        with pytest.raises(NotEnoughCashError):
            game.play(too_many())
        assert game.weather == weather
        assert game.state == state


def test_failed_play_does_not_change_the_future():
    honest, clumsy = Game(seed=3), Game(seed=3)
    with pytest.raises(NotEnoughCashError):
        clumsy.play(too_many())
    for _ in range(5):
        assert honest.play(nothing()) == clumsy.play(nothing())


def test_game_ends():
    game = Game(seed=1, days=3)
    for _ in range(3):
        assert not game.is_over
        game.play(nothing())
    assert game.is_over
    with pytest.raises(GameOverError):
        game.play(nothing())
