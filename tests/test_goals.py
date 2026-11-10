"""v0.13 年度目标：每届研究大会后三选一，完成发奖，不选不完成都不罚。"""

import json

import pytest

from drugstory.career import bot, goals, rating
from drugstory.career import engine as g
from drugstory.career.model import dumps, new_game


def after_first_ceremony(seed=3):
    s = bot.play(seed, weeks=49)
    assert s["year_goal"] and s["year_goal"]["year"] == 2
    return s


def test_offers_are_deterministic_and_feasible():
    a, b = after_first_ceremony(), after_first_ceremony()
    assert a["year_goal"]["offers"] == b["year_goal"]["offers"]
    assert len(a["year_goal"]["offers"]) == 3
    for key in a["year_goal"]["offers"]:
        assert goals.GOALS[key][4](a), "只出今年可能做到的题"


def test_infeasible_goal_is_not_offered():
    s = new_game(1)
    assert not goals.GOALS["improved"][4](s), "没有在研的改良药时不出「改良药上市」"
    goals.offer(s, 2)
    assert "improved" not in s["year_goal"]["offers"]


def test_pick_and_complete_pays_out():
    s = json.loads(dumps(after_first_ceremony()))
    s["year_goal"]["offers"][0] = "services4"
    s = g.execute(s, "pick_goal", {"goal": "services4"})
    cash = s["cash"]
    s["services_done"] += 4
    goals.update(s)
    assert s["year_goal"]["done"] and s["cash"] == pytest.approx(cash + 150)
    assert s["goal_log"][-1]["key"] == "services4"
    with pytest.raises(ValueError):
        g.execute(s, "pick_goal", {"goal": "services4"})


def test_picking_outside_the_offers_is_refused():
    s = after_first_ceremony()
    other = next(k for k in goals.GOALS if k not in s["year_goal"]["offers"])
    with pytest.raises(ValueError):
        g.execute(s, "pick_goal", {"goal": other})


def test_not_picking_or_failing_has_no_penalty_and_year_rolls_over():
    s = json.loads(dumps(after_first_ceremony()))
    cash, rep = s["cash"], s["reputation"]
    goals.close_year(s)
    assert s["goal_history"] == [] and s["cash"] == cash and s["reputation"] == rep
    s["year_goal"]["offers"][0] = "hire"
    s["year_goal"]["base"]["heroes"] = len(s["heroes"]) + 1  # 今年还没有新伙伴
    goals.pick(s, "hire")
    goals.close_year(s)
    assert s["goal_history"][-1] == {"year": 2, "key": "hire", "title": "新面孔", "done": False}


def test_year_end_goal_only_checked_at_year_end():
    s = json.loads(dumps(after_first_ceremony()))
    s["year_goal"]["offers"][0] = "steady"
    goals.pick(s, "steady")
    goals.update(s)
    assert not s["year_goal"]["done"], "「稳住现金」要到年末才判断"
    s["cash"] += 1000
    goals.update(s, year_end=True)
    assert s["year_goal"]["done"]


def test_goals_count_toward_reputation():
    s = new_game(1)
    s["term"], s["week"] = 20, 480
    before = rating.dimensions(s)["reputation"]
    s["goal_log"] = [{"year": y, "key": "hire", "title": "新面孔", "week": 0} for y in range(4)]
    assert rating.dimensions(s)["reputation"] > before


def test_long_game_offers_every_year_and_replays():
    s = bot.play(5, weeks=400)
    assert s["year_goal"]["year"] == s["week"] // 48 + 1
    assert g.replay(s["seed"], s["scenario"], s["actions"]) == s
