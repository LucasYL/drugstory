"""成长建议跟着章节走；第一次出现的成长机会会让「下一件事」停一次。"""

import pytest

from drugstory.career import bot, guide
from drugstory.career import engine as g
from drugstory.career.model import dumps, make_hero, new_game
from drugstory.career.view import snapshot


def ready_for_promotion(s, hid="beaker"):
    h = next(h for h in s["heroes"] if h["id"] == hid)
    h["xp"] = 40
    h["cases"] = ["1", "2"]
    s["knowledge"][h["profession"]] = 20
    return s


def test_fresh_game_suggests_a_generic_project():
    s = new_game(1)
    first = guide.suggestions(s)[0]
    assert first["kind"] == "project" and first["route"] == "generic" and first["ok"]


def test_chapter_two_puts_promotion_first():
    s = new_game(1)
    s["chapter"] = 1
    ready_for_promotion(s)
    first = guide.suggestions(s)[0]
    assert first["kind"] == "promote" and first["chapter"] and first["args"] == {"character": "beaker"}
    assert "第 2 章" in first["text"]


def test_suggestions_are_read_only():
    s = bot.play(5, weeks=400)
    before = dumps(s)
    guide.suggestions(s)
    guide.moments(s)
    snapshot(s)
    assert dumps(s) == before


@pytest.mark.parametrize("seed,weeks", [(1, 150), (2, 300), (3, 500), (4, 700), (6, 900)])
def test_doable_suggestions_really_succeed(seed, weeks):
    """blocker 不复制状态试执行；这里用真实引擎核对它的判断。"""
    s = bot.play(seed, weeks=weeks)
    for item in guide.suggestions(s, limit=10):
        if not item["command"]:
            continue
        if item["ok"]:
            g.execute(s, item["command"], item["args"])
        elif not item["error"].startswith("先攒"):  # 「先攒一攒」是建议等一等，不是引擎拒绝
            with pytest.raises(ValueError):
                g.execute(s, item["command"], item["args"])


def test_next_event_stops_once_for_a_new_promotion():
    s = new_game(1)
    s = g.execute(s, "take_service", {"order": "0-0", "character": "pill"})
    ready_for_promotion(s)
    s = g.execute(s, "next_event", {"batches": 0})
    assert s["week"] == 1 and "promote:beaker:2" in s["tips_seen"]
    assert any(e["type"] == "growth_ready" and e["data"]["key"] == "promote:beaker:2" for e in s["events"])
    s = g.execute(s, "next_event", {"batches": 0})
    assert s["week"] > 1, "同一个机会只停一次"


def test_replay_matches_with_growth_events():
    s = bot.play(7, weeks=300)
    assert g.replay(s["seed"], s["scenario"], s["actions"]) == s


def test_all_generics_taken_points_to_the_next_route():
    s = new_game(1)
    for key in ("g_pressure", "g_lipid", "g_pain", "g_sugar", "g_allergy", "g_inflammation"):
        s["products"].append(
            {"catalog": key, "active": True, "partner": True, "launched": 0, "kind": "generic", "market": "pressure"}
        )
    items = guide.project_items(s)
    assert items and items[0]["route"] in ("improved", "innovative")
    if items[0]["route"] == "improved":
        assert not items[0]["ok"] and "还差" in items[0]["text"]


def test_expansion_is_only_prompted_when_space_is_needed():
    s = new_game(1)
    assert not guide.needs_space(s)
    s["heroes"].append({**make_hero("ruler"), "rank": 2, "xp": 200, "cases": list("123456"), "joined": 0})
    s["knowledge"]["clinical"] = 60
    assert guide.needs_space(s), "只差场地就能晋升大师"
