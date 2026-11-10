"""v0.11 任期与研究所评级；存档 v9 与 v8 兼容。"""

import json

import pytest

from drugstory.career import engine as g
from drugstory.career import rating
from drugstory.career.model import SUFFIX, VERSION, dumps, load, loads, new_game
from drugstory.career.view import snapshot


def test_new_game_takes_a_ten_or_twenty_year_term():
    assert new_game(3)["term"] == 20 and new_game(3, term=10)["term"] == 10
    with pytest.raises(ValueError, match="任期"):
        new_game(3, term=15)
    s = g.execute(new_game(3), "new_game", {"seed": 5, "term": 10})
    assert s["term"] == 10 and s["final"] is None


def test_rating_is_read_only_and_uses_public_results():
    s = new_game(4)
    before = dumps(s)
    view = snapshot(s)["rating"]
    assert dumps(s) == before
    assert view["term"] == 20 and view["weeks_left"] == 960 and view["final"] is None
    assert {d["key"] for d in view["current"]["dimensions"]} == set(rating.WEIGHTS)
    assert sum(rating.WEIGHTS.values()) == pytest.approx(1)
    assert view["current"]["grade"] in "SABCD"


def test_term_end_freezes_the_grade_once_and_play_can_continue():
    s = new_game(6, term=10)
    s["cash"] = 1e6  # 边界单测：只验证任期结算，不经营
    while s["week"] < 476:
        s = g.execute(s, "advance", {"weeks": 4})
    for _ in range(3):
        s = g.execute(s, "advance", {"weeks": 1})
    assert s["week"] == 479 and s["final"] is None
    s = g.execute(s, "advance", {"weeks": 1})
    final = s["final"]
    assert final and final["week"] == 480 and not final["early"]
    assert any(e["type"] == "term_ended" for e in s["events"])
    assert final["grade"] in "SABCD" and final["ending"] and final["highlights"]["approved"] == 0
    s = g.execute(s, "advance", {"weeks": 4})
    assert s["final"] == final, "定格后不再变化"
    assert snapshot(s)["rating"]["final"] == final


def test_bankruptcy_settles_the_term_early():
    s = new_game(8)
    s["cash"] = -5000.0
    while not s["game_over"]:
        s = g.execute(s, "advance", {"weeks": 4})
    assert s["final"]["early"] and s["final"]["dimensions"][3]["score"] == 0


def test_products_count_patients_helped():
    from tests.test_career import complete_phase, ready

    s = ready("generic", strong=True)
    for index in range(4):
        s = complete_phase(s)
        if index < 3:
            s = g.execute(s, "continue_project", {"project": "1"})
    s = g.execute(s, "launch", {"project": "1"})
    for _ in range(6):
        s = g.execute(s, "advance", {"weeks": 4})
    d = s["products"][0]
    assert d["patients"] == pytest.approx(d["total_revenue"] * rating.PATIENTS_PER_WAN["generic"])
    assert snapshot(s)["rating"]["patients"] == round(d["patients"])


def test_v8_saves_load_without_rewriting_the_original(tmp_path):
    from drugstory.career.server import GameSession

    s = json.loads(dumps(new_game(9)))
    s["version"] = 8
    for key in ("term", "final", "nominations"):
        s.pop(key)
    for f in s["festivals"]:
        f["entry"] = None
    old = tmp_path / "scene-autosave.json"
    old.write_text(json.dumps(s, ensure_ascii=False))
    original = old.read_text()
    migrated = load(old)
    assert migrated["version"] == VERSION and migrated["term"] == 20 and migrated["migrated_from"] == 8
    session = GameSession(old)
    assert session.path != old and session.path.name == f"scene-autosave{SUFFIX[VERSION]}.json"
    session.execute({"name": "advance", "args": {"weeks": 4}, "revision": 0})
    assert old.read_text() == original, "v8 原文件不被改写"
    assert loads(session.path.read_text())["week"] == 4
