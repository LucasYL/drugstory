"""v0.13 失败事件卡：同一失败同一原因、选项按在职情况出现、请专家补得更多、止损等同终止。"""

import json

import pytest

from drugstory.career import engine as g
from drugstory.career import incidents
from drugstory.career import science as sc
from drugstory.career.model import dumps, make_hero, new_game
from drugstory.career.view import snapshot


def problem(seed_range=range(1, 60)):
    """从新局开始，把第一款仿制药的工艺做到「差一点」（构造候选真值，只用于边界测试）。"""
    for seed in seed_range:
        s = new_game(seed)
        s = g.execute(s, "start_project", {"catalog": "g_pressure", "heroes": ["beaker", "pill"]})
        s = g.execute(s, "next_event", {"batches": 0})
        pid = s["projects"][0]["id"]
        s = g.execute(s, "choose_candidate", {"project": pid, "candidate": 0})
        c = sc.selected(s["projects"][0])
        c["truth"]["quality"] = sc.limits(s["projects"][0], "formulation").get("quality", 60) - 4
        s = g.execute(s, "run_phase", {"project": pid, "heroes": ["beaker", "pill"]})
        while s["projects"][0]["status"] == "running":
            s = g.execute(s, "next_event", {"batches": 0})
        if s["projects"][0]["status"] == "problem":
            return s
    raise AssertionError("没造出可补正的失败")


def add(s, key, **extra):
    s["heroes"].append({**make_hero(key), "joined": 0, **extra})


def test_every_stage_and_stat_has_a_cause():
    from drugstory.career.content import STAGES, STATS

    assert set(incidents.GROUP) == set(STAGES)
    for key in STAGES:
        for stat in STATS:
            assert incidents.pool(key, stat), (key, stat)


def test_same_failure_draws_same_cause():
    s = problem()
    p = s["projects"][0]
    card = p["incident"]
    assert card["key"] == "formulation" and card["stat"] == "quality"
    assert card["title"] in p["feedback"]
    again = incidents.draw(json.loads(dumps(s)), json.loads(dumps(p)), p["results"][-1])
    assert again == card


def test_options_follow_who_is_free():
    s = problem()
    p = s["projects"][0]
    kinds = [o["kind"] for o in incidents.options(s, p)]
    assert kinds[-1] == "stop" and "rework" in kinds and "switch" in kinds
    talent = p["incident"]["talent"]
    if talent and talent not in {h["id"] for h in s["heroes"]}:
        assert "talent" not in kinds
        add(s, talent)
        assert incidents.options(s, p)[0]["kind"] == "talent"
    add(s, "wizard")
    stop = incidents.options(s, p)[-1]
    assert "会记住这次" in stop["note"]
    before = dumps(s)
    v = snapshot(s)
    assert dumps(s) == before
    assert v["projects"][0]["incident"]["options"]


def with_cause(s, title):
    """把卡换成指定原因（构造状态，只为覆盖每种补正）。"""
    p = s["projects"][0]
    cause = next(c for c in incidents.pool("formulation", "quality") if c["title"] == title)
    p["incident"] = {**p["incident"], **cause}
    return p


def finish(s):
    while s["projects"][0]["status"] == "running":
        s = g.execute(s, "next_event", {"batches": 0})
    return s


def test_expert_rework_is_six_weeks_plus_nine():
    s = problem()
    p = with_cause(s, "辅料换了批次")
    add(s, "forge")
    h = s["heroes"][-1]
    assert incidents.gain(p, h) == incidents.EXPERT["gain"]
    assert any(o["kind"] == "expert" and o["args"]["hero"] == "forge" for o in incidents.options(s, p))
    q = sc.selected(p)["truth"]["quality"]
    s = g.execute(s, "rework_expert", {"project": p["id"], "hero": "forge"})
    assert s["projects"][0]["left"] == 6 and s["projects"][0]["team"] == ["forge"]
    s = finish(s)
    assert sc.selected(s["projects"][0])["truth"]["quality"] == pytest.approx(min(98, q + 9))


def test_talent_rework_is_plus_twelve():
    s = problem()
    p = with_cause(s, "放大后晶型转变")
    add(s, "crystal")
    assert incidents.options(s, p)[0]["kind"] == "talent"
    q = sc.selected(p)["truth"]["quality"]
    s = g.execute(s, "rework_expert", {"project": p["id"], "hero": "crystal"})
    assert any(e["type"] == "talent_triggered" for e in s["events"][-5:])
    s = finish(s)
    assert sc.selected(s["projects"][0])["truth"]["quality"] == pytest.approx(min(98, q + 12))


def test_unrelated_hero_is_refused():
    s = problem()
    p = s["projects"][0]
    add(s, "sprout")
    with pytest.raises(ValueError, match="不对口"):
        g.execute(s, "rework_expert", {"project": p["id"], "hero": "sprout"})


def test_stop_matches_terminate():
    s = problem()
    pid = s["projects"][0]["id"]
    stop = next(o for o in incidents.options(s, s["projects"][0]) if o["kind"] == "stop")
    a = g.execute(s, stop["command"], stop["args"])
    b = g.execute(s, "terminate", {"project": pid})
    assert dumps(a) == dumps(b)
    assert a["projects"][0]["status"] == "terminated"


def test_autopilot_hands_back_with_the_card():
    s = problem()
    p = s["projects"][0]
    p["autopilot"] = "standard"
    g.autopilot_step(s)
    assert p["autopilot"] == "" and p["incident"]["title"] in s["journal"][-1]["text"]
