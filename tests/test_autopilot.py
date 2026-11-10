"""第二款起的仿制药可以交给团队做完：自动选候选、开工、继续、上市；遇到补正交还给玩家。"""

import json

import pytest

from drugstory.career import assist, competition
from drugstory.career import engine as g
from drugstory.career import science as sc
from drugstory.career.model import blocking, busy, dumps, new_game


def finish_first_generic(s):
    """像只点推荐的玩家一样做完第一款仿制药。"""
    s = g.execute(s, "start_project", {"catalog": "g_pressure", "heroes": ["beaker", "pill"]})
    for _ in range(80):
        if s["products"]:
            return s
        p = next((p for p in s["projects"] if blocking(p)), None)
        if p is None:
            s = g.execute(s, "next_event", {"batches": 0})
        elif p["status"] == "selecting":
            s = g.execute(s, "choose_candidate", {"project": p["id"], "candidate": assist.steady_candidate(p)})
        else:
            q = assist.quick(s, p)
            s = g.execute(s, q["command"], q["args"])
    raise AssertionError("第一款仿制药没有做完")


@pytest.fixture(scope="module")
def veteran():
    return finish_first_generic(new_game(3))


def start(s, catalog="g_lipid", mode="standard"):
    team = assist.screening_team(s, "generic")
    return g.execute(s, "start_project", {"catalog": catalog, "heroes": team, "autopilot": mode})


def project(s, catalog):
    return next(p for p in s["projects"] if p["catalog"] == catalog)


def test_first_generic_must_be_done_by_hand():
    s = new_game(3)
    with pytest.raises(ValueError, match="第一款仿制药"):
        g.execute(s, "start_project", {"catalog": "g_pressure", "heroes": ["beaker", "pill"], "autopilot": "standard"})


def test_handed_over_generic_launches_without_blocking(veteran):
    s = start(veteran)
    for _ in range(60):
        p = project(s, "g_lipid")
        if p["status"] == "approved" or not p["autopilot"]:
            break
        assert not blocking(p), "交给团队的项目不让时间停下"
        s = g.execute(s, "next_event", {"batches": 0})
    p = project(s, "g_lipid")
    assert p["status"] == "approved" or (p["status"] == "problem" and p["autopilot"] == "")
    if p["status"] == "approved":
        assert any(d["catalog"] == "g_lipid" for d in s["products"])
    assert g.replay(s["seed"], s["scenario"], s["actions"]) == s


def test_candidate_choice_uses_public_evidence_only(veteran):
    s = start(veteran)
    while project(s, "g_lipid")["status"] == "screening":
        s = g.execute(s, "advance", {"weeks": 1})
    p = project(s, "g_lipid")
    probe = json.loads(json.dumps(p))
    for c in probe["candidates"]:
        c["truth"] = {k: 0 for k in c["truth"]}  # 换掉真值，选择不应改变
    assert p["chosen"] == assist.steady_candidate(probe)


def test_problem_hands_the_project_back(veteran):
    s = start(veteran)
    for _ in range(40):
        p = project(s, "g_lipid")
        if p["status"] == "running" and sc.stage_key(p) == "be":
            break
        s = g.execute(s, "next_event", {"batches": 0})
    p = project(s, "g_lipid")
    assert sc.stage_key(p) == "be"
    sc.selected(p)["truth"]["exposure"] = 55.5  # 门槛 64，差一点：可以补正
    for _ in range(10):
        s = g.execute(s, "next_event", {"batches": 0})
        p = project(s, "g_lipid")
        if p["status"] != "running":
            break
    assert p["status"] == "problem" and p["autopilot"] == "" and blocking(p)


def ready_again(s):
    """回到「准备开工」：交给团队的项目筛选完当周就会开工，这里退回一步来测试等待。"""
    while project(s, "g_lipid")["status"] == "screening":
        s = g.execute(s, "advance", {"weeks": 1})
    s = json.loads(dumps(s))
    p = project(s, "g_lipid")
    p.update(status="ready", left=0, cost_per_week=0)
    return s


def test_waiting_for_cash_changes_nothing_else(veteran):
    s = ready_again(start(veteran))
    s["cash"] = 50.0
    before = json.loads(dumps(s))
    g.autopilot_step(s)
    p = project(s, "g_lipid")
    assert p["status"] == "ready" and p["waiting"].startswith("等现金")
    p.pop("waiting")
    assert s == before


def test_waiting_for_people(veteran):
    s = ready_again(start(veteran))
    for h in s["heroes"]:
        if h["employed"] and h["id"] not in busy(s):
            s["jobs"].append({"kind": "train", "name": "培训", "heroes": [h["id"]], "left": 20})
    before = json.loads(dumps(s))
    g.autopilot_step(s)
    p = project(s, "g_lipid")
    assert p["status"] == "ready" and p["waiting"].startswith("等人")
    p.pop("waiting")
    assert s == before, "开工失败时状态不变（先检查后修改）"


def test_take_over_makes_it_a_normal_decision(veteran):
    s = start(veteran)
    s = g.execute(s, "set_autopilot", {"project": project(s, "g_lipid")["id"], "mode": ""})
    p = project(s, "g_lipid")
    assert p["autopilot"] == "" and p["pace"] == "standard"
    while p["status"] == "screening":
        s = g.execute(s, "advance", {"weeks": 1})
        p = project(s, "g_lipid")
    assert p["status"] == "selecting" and blocking(p)


def test_rush_shortens_build_stages_and_costs_more(veteran):
    s = start(veteran, mode="rush")
    p = json.loads(json.dumps(project(s, "g_lipid")))
    p["chosen"], p["status"] = 0, "ready"
    team = assist.screening_team(s, "generic")
    rush = sc.plan_phase(s, p, team, "standard", "internal", key="formulation")
    p["pace"] = "standard"
    plain = sc.plan_phase(s, p, team, "standard", "internal", key="formulation")
    assert rush["weeks"] < plain["weeks"] and rush["cost"] == pytest.approx(plain["cost"] * sc.RUSH["cost"])
    review_rush = sc.plan_phase(s, {**p, "pace": "rush"}, team, "standard", "internal", key="review")
    assert review_rush["cost"] == sc.plan_phase(s, p, team, "standard", "internal", key="review")["cost"]


def test_craft_uses_validated_design(veteran):
    s = start(veteran, mode="craft")
    p = project(s, "g_lipid")
    assert p["design"] == "validated" and p["pace"] == "craft"


def test_first_mover_softens_later_rivals():
    s = new_game(1)
    r = s["rivals"][0]
    r["portfolio"] = [{"market": "pressure", "active": True, "end": 999, "strength": 1.1, "launched": 100}]
    assert competition.pressure(s, "pressure") == pytest.approx(1.1)
    assert competition.pressure(s, "pressure", since=50) == pytest.approx(1.1 * competition.FIRST_MOVER)
    assert competition.pressure(s, "pressure", since=150) == pytest.approx(1.1)
