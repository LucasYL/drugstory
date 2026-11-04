"""v7 rule boundaries; constructed lab fixtures are distinct from full economy playtests."""

import copy
import json
import math
import statistics

import pytest

from drugstory.career import api, development, readouts, talents
from drugstory.career import economy as e
from drugstory.career import engine as g
from drugstory.career import science as sc
from drugstory.career.content import BUILD, CATALOG, PATHS
from drugstory.career.model import busy, committed, dumps, loads, new_game, rand
from drugstory.career.server import Conflict, GameSession
from drugstory.career.view import phase_preview, snapshot
from tests.test_career import complete_phase, ready
from tests.test_career_v06 import checkpoint, quest_ready


def test_specialized_work_tier_members_and_equipment_improve_candidate_with_finite_budget():
    s = ready("innovative")
    p = s["projects"][0]
    ids = ["sprout", "beaker", "pill"]
    original = copy.deepcopy(sc.selected(p)["truth"])
    base = development.packages(s, p, ids, "optimize")
    for h in s["heroes"]:
        h.update(rank=4, training=60, members=6)
    strong = development.packages(s, p, ids, "optimize")
    assert sum(sum(x["amounts"].values()) for x in strong) > 2 * sum(sum(x["amounts"].values()) for x in base)
    assert all(abs(v) <= 24 for x in strong for v in x["amounts"].values())
    for h in s["heroes"]:
        h["members"] = 0
    solo = development.packages(s, p, ids, "optimize")
    assert sum(sum(x["amounts"].values()) for x in solo) < sum(sum(x["amounts"].values()) for x in strong)
    assert development.packages(s, p, ["ruler"], "optimize") == []
    before = dumps(s)
    preview = phase_preview(s, {"project": "1", "heroes": ids})
    assert dumps(s) == before and preview["work"]
    s = complete_phase(s, ids)
    assert sc.selected(s["projects"][0])["truth"]["effect"] > original["effect"]
    after = copy.deepcopy(sc.selected(s["projects"][0])["truth"])
    development.tick(s, s["projects"][0])
    assert sc.selected(s["projects"][0])["truth"] == after
    assert sc.selected(s["projects"][0])["build_plans"]["optimize"]["completed"] == 3


def test_development_tradeoff_is_visible_and_cannot_be_repeated_by_switching():
    s = ready("innovative")
    p = s["projects"][0]
    p["work_focus"] = "potency"
    x = development.packages(s, p, ["sprout"], "optimize")[0]["amounts"]
    assert x["effect"] > 0 > x["safety"]
    s = complete_phase(s, ["sprout"])
    p = s["projects"][0]
    frozen = copy.deepcopy(sc.selected(p)["build_plans"]["optimize"])
    if s["projects"][0]["status"] == "result":
        s = g.execute(s, "continue_project", {"project": "1"})
    s = g.execute(s, "switch_candidate", {"project": "1", "candidate": 1})
    with pytest.raises(ValueError, match="来回切换"):
        g.execute(s, "switch_candidate", {"project": "1", "candidate": 0})
    assert s["projects"][0]["candidates"][0]["build_plans"]["optimize"] == frozen


def test_clinical_batches_never_improve_truth_and_are_counted_once():
    s = checkpoint("II")
    p = s["projects"][0]
    assert len(p["execution"]["batches"]) == 2
    truth = copy.deepcopy(sc.selected(p)["truth"])
    observations = sc.selected(p)["belief"]["effect"]["observations"]
    noise = copy.deepcopy(p["execution"]["noise_by_stat"])
    partial = copy.deepcopy(p["execution"]["batches"])
    assert readouts.forecast(p) is not None
    with pytest.raises(ValueError):
        g.execute(s, "trial_decision", {"project": "1", "choice": "representative"})
    s = g.execute(s, "trial_decision", {"project": "1", "choice": "keep"})
    s = g.execute(s, "advance", {"weeks": 48})
    p = s["projects"][0]
    assert p["execution"]["noise_by_stat"] == noise
    assert p["execution"]["batches"][:2] == partial
    assert sc.selected(p)["truth"] == truth
    assert sc.selected(p)["belief"]["effect"]["observations"] == observations + 2
    assert p["results"][-1]["values"] == {k: round(v, 1) for k, v in readouts.aggregate(p).items()}
    assert loads(dumps(s)) == s


def test_fixed_plan_batch_mean_has_endpoint_noise_variance():
    # Distribution check, not a claim that adaptive stopping leaves selected rates unchanged.
    samples = [sum(rand(new_game(i), "math", j).gauss(0, 6 * math.sqrt(4)) for j in range(4)) / 4 for i in range(4000)]
    assert abs(statistics.mean(samples)) < 0.25
    assert 5.7 < statistics.stdev(samples) < 6.3


def test_interim_stop_releases_budget_and_is_separate_from_failure():
    s = checkpoint("I")
    p = s["projects"][0]
    assert committed(s) > 0 and busy(s)
    paid = p["spent"]
    out = g.execute(s, "trial_decision", {"project": "1", "choice": "stop"})
    assert not busy(out) and committed(out) == 0
    assert out["projects"][0]["spent"] == paid and out["projects"][0]["status"] == "terminated"
    assert e.report(out)["clinical_failed"] == 0
    assert e.report(out)["clinical_terminated"] == 1


def test_signature_replaces_stacked_traits_and_personal_project_upgrades_it():
    s = quest_ready()
    initial = talents.value(s["heroes"][0])
    s = g.execute(s, "personal_project", {"character": "beaker", "partner": "pill", "choice": "practice"})
    s = g.execute(s, "next_event")
    assert talents.value(s["heroes"][0]) > initial
    assert len(talents.ABILITIES) == 20
    assert not {"specialize", "platform_policy", "set_production"} & g.COMMANDS.keys()


def test_equipment_is_finite_upfront_investment_not_wealth_tax():
    s = new_game(3, difficulty="competition")
    s["cash"] = 50000
    s["facility"] = 3
    before = s["cash"]
    for _ in range(3):
        s = g.execute(s, "upgrade_equipment", {"profession": "bio"})
    assert before - s["cash"] == 12800
    with pytest.raises(ValueError):
        g.execute(s, "upgrade_equipment", {"profession": "bio"})
    cost = e.costs_per_week(s)
    s["cash"] *= 10
    assert e.costs_per_week(s) == cost


def test_all_combinations_have_source_ids_and_discovery_is_not_leaked_early():
    innovative = [c for c in CATALOG.values() if c["kind"] == "innovative"]
    assert len(innovative) == 288
    assert len({(c["target_id"], c["modality_id"]) for c in innovative}) == 288
    public = json.dumps(api.content()) + json.dumps(snapshot(new_game()))
    assert "combo_tier" not in public and "combo_reason" not in public
    s = ready("innovative")
    assert s["notebook"]["n_lung"]["tier"] == CATALOG["n_lung"]["combo_tier"]
    assert len(s["notebook"]) == 1
    assert BUILD.isdisjoint({"I", "II", "III", "be", "bridge", "confirm", "review", "preclinical"})
    assert all(k in PATHS["innovative"] for k in ("optimize", "preclinical", "I", "II", "III", "review"))


def test_public_events_replay_readonly_and_no_hidden_candidate_data():
    s = complete_phase(ready(), ["beaker", "pill"])
    events = s["events"]
    assert any(x["type"] == "work_completed" and x["actors"] and x["room"] for x in events)
    assert [x["id"] for x in events] == sorted({x["id"] for x in events})
    text = dumps(s)
    view = snapshot(s)
    assert dumps(s) == text
    public = json.dumps(api.state(view))
    for private in ('"truth"', '"subgroup"', '"build_plans"', '"seed"', '"mechanisms"'):
        assert private not in public
    assert g.replay(s["seed"], s["scenario"], s["actions"]) == s


def test_request_id_retry_cannot_advance_time_twice_or_change_payload(tmp_path):
    session = GameSession(tmp_path / "test.json")
    command = {"name": "advance", "args": {"weeks": 1}, "revision": 0, "request_id": "once"}
    first = session.execute(command)
    assert session.execute(command)["week"] == first["week"] == 1
    with pytest.raises(Conflict):
        session.execute({**command, "args": {"weeks": 4}})
    assert session.state["week"] == 1


def test_v6_save_rejected_and_v7_difficulty_replay_identical():
    with pytest.raises(ValueError, match="v7"):
        loads('{"version":6}')
    s = new_game(5, difficulty="competition")
    s = g.execute(s, "upgrade_equipment", {"profession": "proc"})
    s = g.execute(s, "advance", {"weeks": 4})
    assert g.replay(5, "foundation", s["actions"], difficulty="competition") == s


def test_next_event_stops_at_visible_work_or_reading():
    s = ready()
    s = g.execute(s, "run_phase", {"project": "1", "heroes": ["pill"]})
    s = g.execute(s, "next_event")
    assert s["projects"][0]["status"] == "running"
    assert any(ev["type"] == "work_completed" for ev in s["transition_events"])


def test_wire_schema_type_generation_and_static_content_separation(tmp_path):
    import runpy
    from pathlib import Path

    import jsonschema

    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "design/api/state-v1.schema.json").read_text())
    session = GameSession(tmp_path / "contract.json")
    session.state = checkpoint()
    public = api.state(session.view())
    jsonschema.validate(public, schema)
    original = copy.deepcopy(public)
    public["projects"][0]["candidates"][0]["truth"] = {}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(public, schema)
    assert "description" not in original["catalog"][0]
    assert len(api.content()["catalog"]) == 297
    assert len(api.content()["catalog"][0]["requirement_labels"]) == len(original["catalog"][0]["requirements"])
    assert (
        runpy.run_path(str(root / "scripts/generate-api-types.py"))["render"]()
        == (root / "src/drugstory/career/web/api-types.d.ts").read_text()
    )


def test_retirement_stops_sales_with_single_production_path():
    s = ready(strong=True)
    e.make_product(s, s["projects"][0])
    s["week"] += 600
    e.market_step(s)
    assert not s["products"][0]["active"] and s["products"][0]["last_revenue"] == 0


def test_cli_does_not_publish_action_when_save_fails(monkeypatch, tmp_path, capsys):
    from drugstory.career import cli

    commands = iter(['train {"character":"beaker"}', "view", "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(commands))

    def fail(*args):
        raise OSError("test disk full")

    monkeypatch.setattr(cli, "atomic_write", fail)
    cli.main(["--save", str(tmp_path / "failed.json")])
    output = capsys.readouterr().out
    assert "test disk full" in output and '"cash": 2600' in output and '"jobs": []' in output


def test_live_wire_roundtrip_and_request_retry(tmp_path):
    import threading
    from http.client import HTTPConnection

    from drugstory.career.server import create_server

    session = GameSession(tmp_path / "http.json")
    server = create_server(session, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = HTTPConnection("127.0.0.1", server.server_port)
    try:
        client.request("GET", "/api/content")
        library = json.loads(client.getresponse().read())
        client.request("GET", "/api/state")
        state = json.loads(client.getresponse().read())
        assert len(library["catalog"]) == len(state["catalog"]) == 297
        assert library["catalog"][0]["requirement_labels"] and state["catalog"][0]["requirements"] == [True]
        body = {"name": "advance", "args": {"weeks": 1}, "revision": 0, "request_id": "retry-test"}
        headers = {"Content-Type": "application/json", "X-Game-Token": state["token"]}
        for _ in range(2):
            client.request("POST", "/api/action", json.dumps(body), headers)
            response = client.getresponse()
            assert response.status == 200 and json.loads(response.read())["week"] == 1
        assert loads(session.path.read_text())["week"] == 1
    finally:
        client.close()
        server.shutdown()
        server.server_close()
        thread.join()
