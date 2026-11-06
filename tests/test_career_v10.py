"""v0.10 smart defaults: one-click plans, service picks and a faster "next thing"."""

import json
from pathlib import Path

import jsonschema

from drugstory.career import api, assist
from drugstory.career import economy as e
from drugstory.career import engine as g
from drugstory.career.model import ability, dumps, make_hero, new_game
from drugstory.career.view import snapshot
from tests.test_career import complete_phase, ready

SCHEMA = json.loads((Path(__file__).parents[1] / "design/api/state-v2.schema.json").read_text())


def public(s):
    return api.state({**snapshot(s), "revision": 0, "token": "test", "saved_at": None})


def test_service_pick_is_weakest_qualified_free_hero_and_never_doubles_up():
    s = new_game(7)
    s["heroes"] += [make_hero("crystal"), make_hero("catalyst")]
    picks = assist.service_picks(s)
    chosen = [p["hero"] for p in picks.values() if p["hero"]]
    assert len(chosen) == len(set(chosen))
    heroes = {h["id"]: h for h in s["heroes"]}
    for order in e.orders(s):
        pick = picks[order["id"]]
        qualified = [
            h for h in s["heroes"] if h["profession"] == order["profession"] and ability(h) >= order["requirement"]
        ]
        if not pick["hero"]:
            assert all(h["id"] in chosen for h in qualified) and pick["note"]
            continue
        spare = [h for h in qualified if h["id"] not in chosen]
        assert all(ability(heroes[pick["hero"]]) <= ability(h) for h in spare)


def test_service_pick_executes_and_skips_people_without_matching_skill():
    s = new_game(3)
    view = snapshot(s)
    picks = view["assist"]["services"]
    assignments = [{"order": k, "character": v["hero"]} for k, v in picks.items() if v["hero"]]
    assert assignments, "a fresh studio always has one accessible order"
    s = g.execute(s, "take_services", {"assignments": assignments})
    assert s["services_done"] == 0 and len(s["jobs"]) == len(assignments)
    after = snapshot(s)["assist"]["services"]
    assert all(v["hero"] is None and v["note"] for v in after.values())


def test_services_avoid_the_person_a_waiting_project_needs():
    s = ready()
    s["heroes"].append(make_hero("crystal"))
    held = assist.reserved(s)
    assert held, "the ready project wants its leads"
    proc_orders = [o["id"] for o in e.orders(s) if o["profession"] == "proc" and not o["taken"]]
    assert proc_orders, "early quarters always offer a formulation order"
    pick = assist.service_picks(s)[proc_orders[0]]
    assert pick["hero"] and pick["hero"] not in held and pick["note"] is None


def test_quick_plan_is_what_the_engine_runs_and_snapshot_stays_read_only():
    s = ready()
    before = dumps(s)
    quick = snapshot(s)["projects"][0]["quick"]
    assert dumps(s) == before
    assert quick["ok"] and quick["command"] == "run_phase" and quick["weeks"] and quick["cost"]
    after = g.execute(s, quick["command"], quick["args"])
    p = after["projects"][0]
    assert p["status"] == "running" and p["execution"]["weeks"] == quick["weeks"]
    assert p["execution"]["cost"] == quick["cost"]


def test_quick_continue_launch_and_unavailable_reason():
    s = complete_phase(ready())
    quick = snapshot(s)["projects"][0]["quick"]
    assert quick["command"] == "continue_and_run" and quick["ok"] and quick["label"].startswith("继续")
    while (shown := snapshot(s)["projects"][0])["status"] == "result" and shown["key"] != "review":
        s = g.execute(s, shown["quick"]["command"], shown["quick"]["args"])
        while s["projects"][0]["status"] in ("running", "checkpoint"):
            s = g.execute(s, "advance", {"weeks": 48})
    p = snapshot(s)["projects"][0]
    if p["status"] == "result":
        assert p["quick"]["command"] == "launch" and p["quick"]["ok"]
        assert "上市" in p["feedback"] and "后续阶段" not in p["feedback"]
        s = g.execute(s, p["quick"]["command"], p["quick"]["args"])
        assert s["products"]
    busy_team = ready()
    busy_team["jobs"].append({"kind": "train", "name": "培训", "heroes": ["beaker", "pill"], "left": 6})
    blocked = snapshot(busy_team)["projects"][0]["quick"]
    assert blocked["ok"] is False and blocked["error"]


def test_deferred_project_keeps_a_plan_but_finished_one_does_not():
    s = ready()
    s = g.execute(s, "defer", {"project": "1"})
    quick = snapshot(s)["projects"][0]["quick"]
    assert quick["ok"] and set(quick["roles"]) <= {"proc", "chem", "bio", "tox", "clinical"}
    resumed = g.execute(s, quick["command"], quick["args"])
    assert resumed["projects"][0]["status"] == "running" and not resumed["projects"][0]["deferred"]
    s = g.execute(s, "terminate", {"project": "1"})
    assert snapshot(s)["projects"][0]["quick"] is None


def test_next_event_can_skip_batches_but_default_keeps_v07_pace():
    start = g.execute(ready(), "run_phase", {"project": "1", "heroes": ["beaker", "pill"]})
    slow = g.execute(start, "next_event")
    fast = g.execute(start, "next_event", {"batches": 0})
    assert slow["week"] < fast["week"]
    assert fast["projects"][0]["status"] in ("result", "problem", "failed")
    assert g.replay(fast["seed"], fast["scenario"], fast["actions"]) == fast


def test_screening_team_matches_route_and_starts():
    s = new_game(11)
    team = snapshot(s)["assist"]["screen"]
    assert team["generic"] and set(team["generic"]) <= {"beaker", "pill"}
    s = g.execute(s, "start_project", {"catalog": "g_pressure", "heroes": team["generic"]})
    assert s["projects"][0]["status"] == "screening"


def test_public_state_with_assist_matches_schema():
    for s in (new_game(), ready(), complete_phase(ready())):
        jsonschema.validate(public(s), SCHEMA)


def test_next_thing_stops_for_new_orders_when_someone_is_idle():
    s = g.execute(new_game(4), "next_event", {"batches": 0})
    assert s["week"] == 12, "with nothing running, the next batch of service orders is the next thing"
    assert g.execute(new_game(4), "next_event")["week"] == 48, "the original pace is unchanged"


def test_next_thing_stops_when_cash_turns_negative_and_warns():
    s = new_game(5)
    s["cash"] = 30.0
    s = g.execute(s, "next_event", {"batches": 0})
    assert s["cash"] < 0 and s["week"] < 12 and not s["game_over"]
    months = s["negative_months"]
    s = g.execute(s, "next_event", {"batches": 0})
    assert s["week"] % 4 == 0 and s["negative_months"] == months + 1, "while negative, next stops at each month end"
    assert any("连续三个月为负会停业" in j["text"] for j in s["journal"])
    assert snapshot(s)["negative_months"] == s["negative_months"] and not s["game_over"]


def test_new_scene_assets_are_served_same_origin(tmp_path):
    import threading
    from http.client import HTTPConnection

    from drugstory.career.server import GameSession, create_server

    session = GameSession(tmp_path / "assets.json")
    server = create_server(session, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = HTTPConnection("127.0.0.1", server.server_port)
    try:
        for path in ("/scene/panels.js", "/scene/figures.js"):
            client.request("GET", path)
            result = client.getresponse()
            assert result.status == 200 and "javascript" in result.getheader("Content-Type")
            result.read()
        client.request("GET", "/scene")
        page = client.getresponse().read().decode()
        assert "/scene/figures.js" in page and "/scene/panels.js" in page and 'data-style="calm"' not in page
    finally:
        client.close()
        server.shutdown()
        server.server_close()
        thread.join()
