import copy
import json

import pytest

from drugstory.career import economy as e
from drugstory.career import engine as g
from drugstory.career import science as sc
from drugstory.career.content import CATALOG, PATHS, ROSTER, STATS
from drugstory.career.model import ability, busy, committed, dumps, loads, make_hero, new_game
from drugstory.career.server import Conflict, GameSession
from drugstory.career.view import phase_preview, snapshot


def ready(kind="generic", seed=42, strong=False):
    s = new_game(seed)
    if kind != "generic":
        s["heroes"] += [make_hero("sprout"), make_hero("bubble"), make_hero("ruler")]
        s["knowledge"] = dict.fromkeys(s["knowledge"], 50)
        s["heroes"][1]["training"] = 20
        s["heroes"][1]["rank"] = 2
        s["capital"] = s["cash"] = 20000
    key = {"generic": "g_pressure", "innovative": "n_lung", "improved": "i_long"}[kind]
    s = g.execute(s, "start_project", {"catalog": key, "heroes": ["beaker", "pill"]})
    s = g.execute(s, "advance", {"weeks": 48})
    s = g.execute(s, "choose_candidate", {"project": "1", "candidate": 0})
    if strong:
        for c in s["projects"][0]["candidates"]:
            c["truth"] = dict.fromkeys(STATS, 97.0)
            for b in c["belief"].values():
                b.update(mean=94.0, variance=4.0)
    return s


def complete_phase(s, ids=None, mode="internal", plan="standard"):
    p = s["projects"][0]
    if ids is None:
        ids = ["beaker", "pill"] if sc.stage_key(p) not in ("I", "II", "III", "bridge", "confirm", "be") else []
        mode = "cro" if not ids else mode
    s = g.execute(s, "run_phase", {"project": "1", "heroes": ids, "mode": mode, "plan": plan})
    while s["projects"][0]["status"] in ("running", "checkpoint"):
        if s["projects"][0]["status"] == "checkpoint":
            s = g.execute(s, "trial_decision", {"project": "1", "choice": "keep"})
        else:
            s = g.execute(s, "advance", {"weeks": 48})
    return s


def preclinical_result():
    s = ready("innovative", strong=True)
    s = complete_phase(s)
    s = g.execute(s, "continue_project", {"project": "1"})
    return complete_phase(s, ["bubble", "pill"])


@pytest.mark.parametrize("scenario", ["foundation", "independent", "licensing", "platform"])
def test_ordinary_start_and_public_character_ladder(scenario):
    s = new_game(12, scenario)
    assert all(h["rank"] == 1 for h in s["heroes"])
    view = snapshot(s)
    assert all(not c["unlocked"] for c in view["roster"] if c["tier"] > 1)
    assert {c["tier"] for c in view["roster"]} >= {2, 3, 4}
    assert {v["tier"] for v in ROSTER.values()} == {1, 2, 3, 4}


def test_three_actual_paths_and_no_innovation_trials_on_generics():
    assert len([p for p in CATALOG.values() if p["kind"] == "generic"]) == 6
    assert "be" in PATHS["generic"] and "II" not in PATHS["generic"]
    assert "bridge" in PATHS["improved"] and "confirm" in PATHS["improved"]
    assert PATHS["innovative"] == ["optimize", "preclinical", "I", "II", "III", "review"]


def test_candidate_pool_fixed_saveable_and_hidden_from_view():
    a, b = ready(), ready()
    assert a == b
    assert loads(dumps(a)) == a
    view = json.dumps(snapshot(a), ensure_ascii=False)
    assert '"truth"' not in view and '"subgroup"' not in view and '"mechanisms"' not in view
    assert len(a["projects"][0]["candidates"]) == 3
    assert len({c["truth"]["quality"] for c in a["projects"][0]["candidates"]}) == 3


@pytest.mark.parametrize(
    "command,args",
    [
        ("choose_candidate", {"project": "1", "candidate": True}),
        ("run_phase", {"project": "1", "heroes": ["pill", "pill"]}),
        ("run_phase", {"project": "1", "heroes": ["missing"]}),
        ("hire", {"character": "star"}),
        ("resize", {"character": "pill", "members": -3}),
        ("advance", {"weeks": 999}),
        ("new_game", {"scenario": []}),
        ("nonsense", {}),
    ],
)
def test_invalid_actions_are_atomic(command, args):
    s = ready()
    before = dumps(s)
    with pytest.raises((ValueError, TypeError)):
        g.execute(s, command, args)
    assert dumps(s) == before


def test_idle_time_does_not_improve_drug_and_waiting_preserves_business():
    s = ready()
    original = copy.deepcopy(s["projects"][0]["candidates"])
    with pytest.raises(ValueError):
        g.execute(s, "advance", {"weeks": 4})
    s = g.execute(s, "defer", {"project": "1"})
    s = g.execute(s, "advance", {"weeks": 48})
    assert s["week"] == 56 and s["projects"][0]["candidates"] == original
    s = g.execute(s, "run_phase", {"project": "1", "heroes": ["pill"]})
    assert not s["projects"][0]["deferred"]


def test_phase_preview_readonly_matches_cost_and_time():
    s = ready()
    args = {"project": "1", "heroes": ["pill", "beaker"], "plan": "expanded", "mode": "internal"}
    before = dumps(s)
    v = phase_preview(s, args)
    actual = g.execute(s, "run_phase", args)
    p = actual["projects"][0]
    assert dumps(s) == before
    assert (v["weeks"], v["cost"]) == (p["left"], p["execution"]["cost"])
    assert committed(actual) == pytest.approx(v["cost"])


def test_members_change_duration_and_cost_but_not_true_drug():
    s = ready()
    truth = copy.deepcopy(sc.selected(s["projects"][0])["truth"])
    old = sc.plan_phase(s, s["projects"][0], ["pill"])
    s = g.execute(s, "resize", {"character": "pill", "members": 6})
    new = sc.plan_phase(s, s["projects"][0], ["pill"])
    assert new["weeks"] < old["weeks"]
    assert truth == sc.selected(s["projects"][0])["truth"]


def test_validation_learns_without_improving_candidate():
    s = ready()
    c = copy.deepcopy(sc.selected(s["projects"][0]))
    s = g.execute(s, "experiment", {"project": "1", "method": "validate", "stat": "quality", "heroes": ["pill"]})
    s = g.execute(s, "advance", {"weeks": 48})
    result = sc.selected(s["projects"][0])
    assert result["truth"] == c["truth"]
    assert result["belief"]["quality"]["variance"] < c["belief"]["quality"]["variance"]


def test_optimization_has_tradeoff_and_limit():
    s = ready()
    before = copy.deepcopy(sc.selected(s["projects"][0])["truth"])
    for stat, role in [("quality", "pill"), ("exposure", "beaker")]:
        s = g.execute(s, "experiment", {"project": "1", "method": "refine", "stat": stat, "heroes": [role]})
        s = g.execute(s, "advance", {"weeks": 48})
        if stat == "quality":
            after = sc.selected(s["projects"][0])["truth"]
            assert after["quality"] > before["quality"] and after["exposure"] < before["exposure"]
    with pytest.raises(ValueError):
        g.execute(s, "experiment", {"project": "1", "method": "refine", "stat": "quality", "heroes": ["pill"]})


def test_large_trial_does_not_rescue_ineffective_candidate():
    standard = expanded = 0
    for seed in range(150):
        s = ready("innovative", seed, strong=True)
        p = s["projects"][0]
        p["index"] = 4
        sc.selected(p)["truth"]["effect"] = 70
        for plan in ("standard", "expanded"):
            result = sc.evaluate(copy.deepcopy(s), copy.deepcopy(p), sc.plan_phase(s, p, [], plan, partner=True))
            if plan == "standard":
                standard += result["passed"]
            else:
                expanded += result["passed"]
    assert 0 < expanded < standard < 100


def test_phase_observation_persistent_and_correlated_to_same_drug():
    s = ready("innovative")
    p = s["projects"][0]
    execution = sc.plan_phase(s, p, ["beaker"])
    a = sc.evaluate(copy.deepcopy(s), copy.deepcopy(p), execution)
    b = sc.evaluate(loads(dumps(s)), copy.deepcopy(p), execution)
    assert a == b
    sc.selected(p)["truth"]["effect"] -= 30
    c = sc.evaluate(s, p, execution)
    assert c["values"]["effect"] == pytest.approx(a["values"]["effect"] - 30, abs=0.11)


def test_focused_requires_real_marker_study_and_professional():
    s = ready("innovative", strong=True)
    p = s["projects"][0]
    p["index"] = 3
    with pytest.raises(ValueError):
        g.execute(s, "run_phase", {"project": "1", "heroes": ["ruler"], "plan": "focused"})
    marker = sc.selected(p)["marker"]
    marker.update(mean=10, variance=4, observations=1)
    h = next(h for h in s["heroes"] if h["id"] == "ruler")
    h.update(rank=3, training=15)
    assert sc.focused_available(s, p, ["ruler"])
    s = g.execute(s, "run_phase", {"project": "1", "heroes": ["ruler"], "plan": "focused"})
    assert s["projects"][0]["population"] == "focused"


def test_successful_generic_full_cycle_cash_and_no_fake_innovative_approval():
    s = ready(strong=True)
    for i in range(4):
        s = complete_phase(s)
        assert s["projects"][0]["status"] == "result"
        if i < 3:
            s = g.execute(s, "continue_project", {"project": "1"})
    s = g.execute(s, "launch", {"project": "1", "name": "稳稳小药丸"})
    s = g.execute(s, "advance", {"weeks": 48})
    assert s["income"]["sales"] > 0 and s["expense"]["manufacturing"] > 0
    assert s["cash"] == pytest.approx(s["capital"] + sum(s["income"].values()) - sum(s["expense"].values()))
    assert e.report(s)["approvals"] == {"generic": 1, "improved": 0, "innovative": 0}
    assert all(len(h["cases"]) == 1 for h in s["heroes"])


def test_failure_preserves_learning_but_empty_cancel_does_not():
    s = ready("innovative", strong=True)
    sc.selected(s["projects"][0])["truth"]["effect"] = 10
    s = complete_phase(s)
    assert s["projects"][0]["status"] == "failed"
    assert s["heroes"][0]["cases"] == ["1"] and s["heroes"][0]["xp"] > 0
    s = new_game()
    s = g.execute(s, "start_project", {"catalog": "g_pressure", "heroes": ["pill"]})
    s = g.execute(s, "terminate", {"project": "1"})
    assert all(not h["cases"] and h["xp"] == 0 for h in s["heroes"])
    assert s["reputation"] == 0


def test_quote_uses_evidence_not_hidden_values_and_terms_have_tradeoffs():
    s = preclinical_result()
    p = s["projects"][0]
    cash, royalties, joint = [e.quote(s, p, key) for key in ("cash", "royalty", "codevelop")]
    sc.selected(p)["truth"] = dict.fromkeys(STATS, 5)
    assert e.quote(s, p, "cash") == cash
    assert cash["upfront"] > royalties["upfront"] > joint["upfront"]
    assert cash["royalty"] < royalties["royalty"] < joint["royalty"]
    assert joint["owner_commitment"] > 0 and royalties["owner_commitment"] == 0


@pytest.mark.parametrize("terms", ["cash", "royalty", "codevelop"])
def test_partner_real_success_milestones_once_and_royalties(terms):
    s = preclinical_result()
    s = g.execute(s, "license_project", {"project": "1", "terms": terms})
    assert not busy(s) and s["income"]["upfront"] > 0
    while s["deals"][0]["status"] == "developing":
        s = g.execute(s, "advance", {"weeks": 48})
    d = s["deals"][0]
    assert d["status"] == "approved" and len(d["paid"]) == 3
    milestones = s["income"]["milestones"]
    s = g.execute(s, "advance", {"weeks": 48})
    assert s["income"]["milestones"] == milestones and s["income"]["royalties"] > 0
    assert e.report(s)["approvals"]["innovative"] == 0
    assert (s["expense"]["codevelopment"] > 0) == (terms == "codevelop")
    assert s["cash"] == pytest.approx(s["capital"] + sum(s["income"].values()) - sum(s["expense"].values()))


def test_partner_can_fail_without_losing_upfront_or_fake_milestone():
    s = preclinical_result()
    sc.selected(s["projects"][0])["truth"]["safety"] = 5
    s = g.execute(s, "license_project", {"project": "1", "terms": "cash"})
    upfront = s["income"]["upfront"]
    s = g.execute(s, "advance", {"weeks": 48})
    assert s["deals"][0]["status"] == "failed" and s["income"]["upfront"] == upfront
    assert not s["income"].get("milestones") and not s["income"].get("royalties")


def test_recruit_gate_cannot_be_bought_and_starter_can_promote():
    s = new_game()
    s["capital"] = s["cash"] = 1000000
    with pytest.raises(ValueError):
        g.execute(s, "hire", {"character": "architect"})
    h = s["heroes"][1]
    h.update(xp=28, cases=["a", "b"])
    s["knowledge"]["proc"] = 8
    old = ability(h)
    s = g.execute(s, "promote", {"character": "pill"})
    assert s["heroes"][1]["rank"] == 2 and ability(s["heroes"][1]) > old
    assert s["first_rank2"] == 0


def test_high_tier_requires_cooperation_before_hire():
    s = new_game()
    s.update(capital=10000, cash=10000.0, facility=2, milestones=20)
    s["knowledge"]["proc"] = 80
    s["heroes"][1].update(rank=3, training=12)
    with pytest.raises(ValueError):
        g.execute(s, "hire", {"character": "architect"})
    s = g.execute(s, "collaborate", {"character": "architect", "researcher": "pill"})
    assert busy(s)["pill"]
    s = g.execute(s, "advance", {"weeks": 48})
    s = g.execute(s, "hire", {"character": "architect"})
    assert s["heroes"][-1]["rank"] == 4 and s["heroes"][-1]["name"] == "药剂造物主"


def test_mentor_is_professional_once_only_and_no_fake_cases():
    s = new_game()
    s["heroes"].append(make_hero("crystal"))
    s = g.execute(s, "mentor", {"teacher": "crystal", "pupil": "pill"})
    assert {"pill", "crystal"} <= busy(s).keys()
    s = g.execute(s, "advance", {"weeks": 48})
    assert s["heroes"][1]["xp"] == 10 and not s["heroes"][1]["cases"]
    with pytest.raises(ValueError):
        g.execute(s, "mentor", {"teacher": "crystal", "pupil": "pill"})


def test_orders_limited_pay_on_completion_and_idle_hero_can_train():
    s = new_game()
    order = e.orders(s)[0]
    s = g.execute(s, "take_service", {"order": order["id"], "character": "pill"})
    assert not s["income"]
    with pytest.raises(ValueError):
        g.execute(s, "take_service", {"order": order["id"], "character": "beaker"})
    s = g.execute(s, "train", {"character": "beaker"})
    s = g.execute(s, "advance", {"weeks": 48})
    assert s["income"]["services"] == order["reward"] and s["services_done"] == 1


def test_competition_changes_sales_but_not_phase_requirements():
    s = ready("innovative", strong=True)
    p = s["projects"][0]
    d = e.make_product(s, p)
    s["week"] = d["launched"] + 48
    old = e.expected_sales(s, d)[0]
    limits = sc.limits(p, "III")
    next(r for r in s["rivals"] if r["market"] == "lung")["active"] = True
    assert e.expected_sales(s, d)[0] < old and sc.limits(p, "III") == limits


def test_replay_and_readonly_snapshot():
    s = ready()
    before = dumps(s)
    snapshot(s)
    assert dumps(s) == before
    assert g.replay(s["seed"], s["scenario"], s["actions"]) == s


def test_old_save_rejected_and_new_session_backups(tmp_path):
    with pytest.raises(ValueError, match="v7"):
        loads(json.dumps({"version": 3}))
    path = tmp_path / "career.json"
    session = GameSession(path)
    session.execute({"revision": 0, "name": "new_game", "args": {"seed": 7, "scenario": "platform"}})
    assert len(list(tmp_path.glob("career-before-new-*.json"))) == 1
    assert loads(path.read_text())["scenario"] == "platform"
    with pytest.raises(Conflict):
        session.execute({"revision": 0, "name": "advance", "args": {"weeks": 4}})


def test_failed_disk_write_does_not_publish_state(tmp_path, monkeypatch):
    session = GameSession(tmp_path / "career.json")
    before = dumps(session.state)

    def fail(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("drugstory.career.server.atomic_write", fail)
    with pytest.raises(OSError):
        session.execute({"revision": 0, "name": "advance", "args": {"weeks": 4}})
    assert session.revision == 0 and dumps(session.state) == before


def test_pipeline_capacity_requires_cro_and_does_not_leave_clinical_unstaffed():
    s = ready("innovative", strong=True)
    p = s["projects"][0]
    p["index"] = 2
    with pytest.raises(ValueError, match="临床负责人"):
        g.execute(s, "run_phase", {"project": "1", "heroes": ["beaker"]})
    s = g.execute(s, "run_phase", {"project": "1", "heroes": ["ruler"]})
    assert g.internal_usage(s) == 1

    other = copy.deepcopy(s["projects"][0])
    other.update(id="2", status="ready", clinical_started=False)
    s["projects"].append(other)
    with pytest.raises(ValueError):
        g.execute(s, "run_phase", {"project": "2", "heroes": ["ruler"]})
    s = g.execute(s, "run_phase", {"project": "2", "heroes": [], "mode": "cro"})
    assert g.internal_usage(s) == 1


def test_specialists_improve_their_endpoint_without_changing_the_molecule():
    s = ready("innovative")
    p = s["projects"][0]
    p["index"] = 1
    before = copy.deepcopy(sc.selected(p)["truth"])
    solo = sc.plan_phase(s, p, ["pill"])
    team = sc.plan_phase(s, p, ["pill", "bubble"])
    assert team["noise_by_stat"]["safety"] < solo["noise_by_stat"]["safety"]
    assert team["noise_by_stat"]["quality"] == solo["noise_by_stat"]["quality"]
    assert sc.selected(p)["truth"] == before
    preview = phase_preview(s, {"project": "1", "heroes": ["pill", "bubble"]})
    from drugstory.career.view import chance_range

    assert preview["chance"] == chance_range(team["probability"])


def test_generic_cannot_buy_irrelevant_efficacy_or_nonclinical_cro():
    s = ready()
    for args in (
        {"method": "refine", "stat": "effect"},
        {"method": "translate", "stat": "quality"},
    ):
        with pytest.raises(ValueError, match="普通仿制药"):
            g.execute(s, "experiment", {"project": "1", "heroes": ["pill"], **args})
    with pytest.raises(ValueError, match="CRO"):
        g.execute(s, "run_phase", {"project": "1", "heroes": [], "mode": "cro"})


def test_renewal_window_opens_before_retirement_and_replacement_does_not_duplicate_sales():
    s = ready(strong=True)
    p = s["projects"][0]
    p["status"] = "approved"
    old = e.make_product(s, p)
    s["week"] = old["launched"] + e.product_life(old) - 97
    with pytest.raises(ValueError, match="换代窗口"):
        g.execute(s, "start_project", {"catalog": "g_pressure", "heroes": ["pill"]})
    s["week"] += 1
    e.market_step(s)
    assert old["renewal_notice"] and old["last_revenue"] > 0
    s = g.execute(s, "start_project", {"catalog": "g_pressure", "heroes": ["pill"]})
    replacement = copy.deepcopy(s["projects"][0])
    replacement["id"] = "replacement"
    e.make_product(s, replacement)
    assert not s["products"][0]["active"] and s["products"][-1]["active"]
    assert e.expected_sales(s, s["products"][0]) == (0, 0)


def test_http_preview_origin_revision_and_save_roundtrip(tmp_path):
    import threading
    from http.client import HTTPConnection

    from drugstory.career.server import create_server

    session = GameSession(tmp_path / "http.json")
    session.state = ready()
    server = create_server(session, 0)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    connection = HTTPConnection("127.0.0.1", server.server_port)
    headers = {"Content-Type": "application/json", "X-Game-Token": session.token}
    body = {"revision": 0, "args": {"project": "1", "heroes": ["pill"]}}
    try:
        before = dumps(session.state)
        connection.request("POST", "/api/preview", json.dumps(body), headers)
        response = connection.getresponse()
        assert response.status == 200 and json.loads(response.read())["cost"] > 0
        assert dumps(session.state) == before and not session.path.exists()
        connection.request("POST", "/api/action", json.dumps(body), {**headers, "Origin": "http://elsewhere.invalid"})
        response = connection.getresponse()
        assert response.status == 403
        response.read()
        connection.request("POST", "/api/action", json.dumps({**body, "name": "run_phase"}), headers)
        response = connection.getresponse()
        assert response.status == 200 and json.loads(response.read())["revision"] == 1
        assert loads(session.path.read_text()) == session.state
        connection.request("POST", "/api/action", json.dumps({**body, "name": "run_phase"}), headers)
        response = connection.getresponse()
        assert response.status == 409
        response.read()
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        worker.join()


def test_next_event_stops_for_training_then_service_delivery():
    s = new_game()
    s = g.execute(s, "take_service", {"order": e.orders(s)[0]["id"], "character": "pill"})
    s = g.execute(s, "train", {"character": "beaker"})
    s = g.execute(s, "next_event")
    assert s["week"] == 6 and "beaker" not in busy(s) and s["services_done"] == 0
    s = g.execute(s, "next_event")
    assert s["week"] == 10 and s["services_done"] == 1 and not busy(s)
    assert g.replay(s["seed"], s["scenario"], s["actions"]) == s
