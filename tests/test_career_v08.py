"""v0.8 boundaries: display points, scene data, patents, commercial costs, diminishing development, milestones."""

import copy
import json

import pytest

from drugstory.career import api, development, patents
from drugstory.career import economy as e
from drugstory.career import engine as g
from drugstory.career import science as sc
from drugstory.career.content import COMMERCIAL, PATENT, PROFESSION_ROOM, ROOMS, ROSTER, STAGES
from drugstory.career.model import dumps, loads, new_game
from drugstory.career.units import pts
from drugstory.career.view import snapshot
from tests.test_career import complete_phase, preclinical_result, ready


def test_player_facing_research_numbers_are_points():
    s = ready("innovative")
    view = snapshot(s)["projects"][0]
    c = sc.selected(s["projects"][0])
    shown = {row["key"]: row for row in view["candidates"][0]["evidence"]}
    assert shown["effect"]["mean"] == pts(c["belief"]["effect"]["mean"])
    assert all(isinstance(row["low"], int) and isinstance(row["high"], int) for row in shown.values())
    s = complete_phase(s, ["sprout", "beaker", "pill"])
    view = snapshot(s)["projects"][0]
    result = view["results"][-1]
    raw = s["projects"][0]["results"][-1]
    assert result["limits"] == {k: pts(v) for k, v in raw["limits"].items()}
    work = [ev for ev in s["events"] if ev["type"] == "work_completed"]
    assert work and all(isinstance(v, int) for ev in work for v in ev["data"]["amounts"].values())


def test_rooms_table_and_events_point_at_real_rooms():
    content = api.content()
    ids = {room["id"] for room in content["rooms"]}
    assert ids == set(ROOMS) and content["display_scale"] == 10
    assert all(stage["room"] in ids for stage in STAGES.values())
    s = ready("innovative")
    s = complete_phase(s, ["sprout", "beaker", "pill"])
    for ev in s["events"]:
        assert ev["room"] is None or ev["room"] in ids
    started = next(ev for ev in s["events"] if ev["type"] == "phase_started")
    assert started["room"] == STAGES["optimize"]["room"]
    for ev in s["events"]:
        if ev["type"] == "work_completed":
            hero = next(h for h in s["heroes"] if h["id"] == ev["actors"][0])
            assert ev["room"] == PROFESSION_ROOM[hero["profession"]]


def test_cro_stage_is_marked_and_has_no_actors():
    s = preclinical_result()
    s = g.execute(s, "continue_project", {"project": "1"})
    s = g.execute(s, "run_phase", {"project": "1", "heroes": [], "mode": "cro"})
    started = [ev for ev in s["transition_events"] if ev["type"] == "phase_started"][0]
    assert started["actors"] == [] and started["data"]["executor"] == "cro" and "CRO" in started["data"]["note"]
    assert started["room"] == "room_clinical"


def test_cash_changed_carries_a_breakdown():
    s = new_game(42)
    s = g.execute(s, "advance", {"weeks": 4})
    cash = [ev for ev in s["transition_events"] if ev["type"] == "cash_changed"][0]["data"]
    assert cash["expense"]["payroll"] > 0 and cash["expense"]["rent"] > 0
    total = sum(cash["income"].values()) - sum(cash["expense"].values())
    assert abs(total - cash["amount"]) < 0.05


def test_patent_is_filed_granted_and_sales_fall_after_expiry():
    s = preclinical_result()
    p = s["projects"][0]
    assert p["patent"]["expires"] == p["patent"]["filed"] + PATENT["term"]["innovative"]
    filed = [ev for ev in s["events"] if ev["type"] == "patent_filed"]
    assert len(filed) == 1 and filed[0]["data"]["expires_year"] == p["patent"]["expires"] // 48 + 1
    reputation = s["reputation"]
    s["week"] = p["patent"]["filed"] + PATENT["grant_delay"] - 1
    patents.tick(s)
    assert p["patent"]["granted"] is None
    s["week"] += 1
    patents.tick(s)
    assert p["patent"]["granted"] == s["week"] and s["reputation"] == reputation + 2
    assert [ev["type"] for ev in s["events"]].count("patent_granted") == 1
    d = e.make_product(s, p)
    assert d["exclusive_until"] == p["patent"]["expires"]
    d["launched"] = d["exclusive_until"] - 300
    s["week"] = d["exclusive_until"] - 1
    before = e.base_sales(s, d)[0]
    s["week"] = d["exclusive_until"] + PATENT["erosion_weeks"]
    after = e.base_sales(s, d)[0]
    assert before > 0 and after == pytest.approx(before * PATENT["floor"]["innovative"], rel=0.02)


def test_failed_projects_do_not_get_a_patent_ceremony():
    s = preclinical_result()
    p = s["projects"][0]
    p["status"] = "failed"
    s["week"] = p["patent"]["filed"] + PATENT["grant_delay"]
    patents.tick(s)
    assert p["patent"]["granted"] is False and not any(ev["type"] == "patent_granted" for ev in s["events"])
    assert patents.view(s) == []


def test_patent_expiry_event_fires_once_on_the_expiry_week():
    s = preclinical_result()
    d = e.make_product(s, s["projects"][0])
    s["week"] = d["exclusive_until"]
    patents.tick(s)
    patents.tick(s)
    assert sum(ev["type"] == "patent_expired" for ev in s["events"]) == 1


def test_commercial_cost_applies_to_own_products_only():
    s = preclinical_result()
    d = e.make_product(s, s["projects"][0])
    d["launched"] = s["week"] - 60
    before = s["expense"].get("commercial", 0)
    e.market_step(s)
    revenue = d["last_revenue"]
    assert revenue > 0
    assert s["expense"]["commercial"] - before == pytest.approx(revenue * COMMERCIAL["innovative"])
    assert d["last_profit"] == pytest.approx(revenue * (min(0.9, d["margin"]) - COMMERCIAL["innovative"]))
    d["partner"] = True
    assert e.commercial_rate(d) == 0


def test_development_has_diminishing_returns_without_reading_hidden_truth():
    assert development.efficiency(0) == 1 and development.efficiency(development.FREE) == 1
    assert development.efficiency(development.FREE + development.KNEE) == pytest.approx(0.5)
    s = ready("innovative")
    c = copy.deepcopy(sc.selected(s["projects"][0]))
    twin = copy.deepcopy(c)
    twin["truth"] = {k: v + 20 for k, v in c["truth"].items()}
    first = [development.step(c, "effect", 8) for _ in range(3)]
    second = [development.step(twin, "effect", 8) for _ in range(3)]
    assert first == second  # same public tally, same increments: the batch size never reveals the truth
    assert first[0] == 8 and first[1] < first[0] and first[2] < first[1]
    assert c["developed"]["effect"] == pytest.approx(sum(first))


def test_heavy_development_shrinks_more_than_junior_work():
    s = ready("innovative")
    p = s["projects"][0]

    def kept(ids):
        packages = development.packages(s, p, ids, "optimize")
        planned = sum(sum(x["amounts"].values()) for x in packages)
        shown = development.expected(p, "optimize", packages)
        return sum(sum(x["amounts"].values()) for x in shown) / pts(planned)

    junior = kept(["sprout"])
    for h in s["heroes"]:
        h.update(rank=4, training=60, members=4)
    senior = kept(["sprout", "beaker", "pill"])
    assert junior >= 0.9 and senior < 0.85 and senior < junior


def test_equipment_and_rent_are_weekly_costs():
    s = new_game(42)
    s["equipment"]["chem"] = 2
    s = g.execute(s, "advance", {"weeks": 1})
    assert s["expense"]["equipment_upkeep"] == pytest.approx(development.upkeep(s))
    assert development.upkeep(s) == pytest.approx(3.0)


def test_milestones_are_events_and_recorded_once():
    s = ready(strong=True)
    while s["projects"][0]["status"] != "result" or s["projects"][0]["results"][-1]["key"] != "review":
        p = s["projects"][0]
        if p["status"] == "result":
            s = g.execute(s, "continue_project", {"project": "1"})
        s = complete_phase(s)
    s = g.execute(s, "launch", {"project": "1", "name": "测试片"})
    events = [ev for ev in s["transition_events"] if ev["type"] in ("product_launched", "milestone_reached")]
    assert [ev["type"] for ev in events] == ["product_launched", "milestone_reached"]
    assert events[1]["data"]["key"] == "first_product"
    s = g.execute(s, "advance", {"weeks": 1})
    assert sum(a["key"] == "first_product" for a in s["achievements"]) == 1
    again = [ev for ev in s["transition_events"] if ev["type"] == "milestone_reached"]
    assert not any(ev["data"]["key"] == "first_product" for ev in again)


def test_cast_has_unique_names_and_scene_data():
    assert len({c["name"] for c in ROSTER.values()}) == 20
    for c in ROSTER.values():
        assert c["nickname"] and len(c["bio"]) > 20 and c["look"]["prop"]
    content = api.content()
    assert len(content["roster"]) == 20 and all("look" in c for c in content["roster"])
    s = ready("innovative")
    s = g.execute(s, "run_phase", {"project": "1", "heroes": ["sprout", "beaker", "pill"]})
    heroes = {h["id"]: h for h in snapshot(s)["heroes"]}
    assert heroes["sprout"]["room"] == "room_bio" and heroes["sprout"]["activity"] == "make"
    assert heroes["ruler"]["room"] is None and heroes["ruler"]["activity"] == "idle"


def test_v7_saves_are_refused_with_a_clear_message():
    s = new_game(1)
    old = json.loads(dumps(s))
    old["version"] = 7
    with pytest.raises(ValueError, match="v8"):
        loads(json.dumps(old))
