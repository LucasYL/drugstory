"""v0.13 专长看得见：专长起作用时发 talent_triggered；同一阶段不重复；授权给合作方的阶段不发。"""

import json

from drugstory.career import bot, talents
from drugstory.career import engine as g
from drugstory.career import science as sc
from drugstory.career.model import dumps, make_hero, new_game


def talent_events(s, key=None):
    return [e for e in s["events"] if e["type"] == "talent_triggered" and (key is None or e["data"]["key"] == key)]


def test_phase_start_reports_the_talents_that_shaped_it():
    s = new_game(1)
    s = g.execute(s, "start_project", {"catalog": "g_pressure", "heroes": ["beaker", "pill"]})
    assert not talent_events(s)
    s = g.execute(s, "next_event", {"batches": 0})
    p = s["projects"][0]
    s = g.execute(s, "choose_candidate", {"project": p["id"], "candidate": 0})
    s = g.execute(s, "run_phase", {"project": p["id"], "heroes": ["pill", "beaker"]})
    events = talent_events(s, "pill")
    assert events and "工艺稳定 +40" in events[-1]["data"]["text"] and events[-1]["actors"] == ["pill"]
    assert s["heroes"][1]["talent_uses"]


def test_same_stage_reports_once():
    s = new_game(1)
    p = {"id": "x"}
    talents.trigger(s, "pill", "测试", ["pill"], p=p, stage="formulation")
    talents.trigger(s, "pill", "测试", ["pill"], p=p, stage="formulation")
    talents.trigger(s, "pill", "测试", ["pill"], p=p, stage="quality")
    assert len(talent_events(s, "pill")) == 2


def test_partner_phases_have_no_talent_notes():
    s = new_game(1)
    s["heroes"].append({**make_hero("curve"), "joined": 0})
    p = {"catalog": "n_lung", "kind": "innovative", "index": 3, "chosen": None, "candidates": []}
    fx = sc.skill_effects(s, p, ["curve"], "II", partner=True)
    assert fx["notes"] == []
    assert sc.skill_effects(s, p, ["curve"], "II")["notes"][0]["key"] == "curve"


def test_service_bonus_is_reported():
    s = new_game(1)
    s = g.execute(s, "take_service", {"order": "0-0", "character": "pill"})
    for _ in range(12):
        s = g.execute(s, "advance", {"weeks": 1})
    events = talent_events(s, "pill")
    assert events and "服务回款 +30%" in events[-1]["data"]["text"]


def test_quick_button_names_the_talents_it_uses():
    from drugstory.career.view import snapshot

    s = new_game(1)
    s = g.execute(s, "start_project", {"catalog": "g_pressure", "heroes": ["beaker", "pill"]})
    s = g.execute(s, "next_event", {"batches": 0})
    s = g.execute(s, "choose_candidate", {"project": s["projects"][0]["id"], "candidate": 0})
    q = snapshot(s)["projects"][0]["quick"]
    assert any(x == "苏小禾·每一炉都一样" for x in q["talents"])


def test_long_game_most_talents_show_up_and_replay_matches():
    s = bot.play(3, weeks=958)
    silent = {"bubble", "bridge", "star"}  # 要靠专项复核、分层研究或只在立项页显示，证据型玩家用不到
    for h in s["heroes"]:
        served = (s["week"] - h.get("joined", 0)) / 48
        if served >= 2 and h["id"] not in silent:
            assert sum(h.get("talent_uses", {}).values()) >= 1, h["name"]
    assert g.replay(s["seed"], s["scenario"], s["actions"]) == json.loads(dumps(s))
