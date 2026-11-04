"""Boundary fixtures deliberately construct strong candidates; normal play lives in the script."""

import copy

import pytest

from drugstory.career import challenge, product_design, stories
from drugstory.career import economy as e
from drugstory.career import engine as g
from drugstory.career import science as sc
from drugstory.career.content import PATHS, ROSTER
from drugstory.career.model import busy, committed, dumps, loads, new_game
from drugstory.career.view import phase_preview, snapshot
from tests.test_career import complete_phase, ready


def checkpoint(key="II"):
    s = ready("innovative", strong=True)
    p = s["projects"][0]
    p["index"] = PATHS["innovative"].index(key)
    s = g.execute(s, "run_phase", {"project": "1", "heroes": ["ruler", "bubble"], "mode": "cro"})
    return g.execute(s, "advance", {"weeks": 48})


def quest_ready():
    s = new_game(13)
    s["week"] = 48
    s["heroes"][0]["training"] = 20
    s["heroes"][0]["work"]["g_pressure-quality"] = 3
    return s


def test_all_characters_have_a_unique_professional_story_and_valid_peer():
    assert set(stories.STORIES) == set(ROSTER)
    assert len({v[0] for v in stories.STORIES.values()}) == 20
    for key, (_, text, role) in stories.STORIES.items():
        assert len(text) > 20
        assert role != ROSTER[key]["profession"]
    assert not stories.options(new_game(), new_game()["heroes"][0])["unlocked"]


def test_personal_quest_occupies_two_people_grants_legacy_but_no_fake_cases():
    s = quest_ready()
    q = stories.options(s, s["heroes"][0])
    assert q["unlocked"] and q["partners"] == ["pill"]
    before_cases = list(s["heroes"][0]["cases"])
    s = g.execute(s, "personal_project", {"character": "beaker", "partner": "pill", "choice": "handoff"})
    assert set(busy(s)) == {"beaker", "pill"}
    assert s["jobs"][0]["left"] == 8
    s = g.execute(s, "next_event")
    assert s["heroes"][0]["personal"]["choice"] == "handoff"
    assert s["heroes"][0]["cases"] == before_cases
    assert not busy(s)
    with pytest.raises(ValueError):
        g.execute(s, "personal_project", {"character": "beaker", "partner": "pill", "choice": "verify"})
    assert loads(dumps(s)) == s


@pytest.mark.parametrize("choice", ["verify", "handoff"])
def test_cooperation_needs_partner_and_relevant_profession(choice):
    s = ready(strong=True)
    p = s["projects"][0]
    base = sc.plan_phase(s, p, ["beaker", "pill"])
    solo = sc.plan_phase(s, p, ["beaker"])
    truth = copy.deepcopy(sc.selected(p)["truth"])
    s["heroes"][0]["personal"] = {"choice": choice}
    assert sc.plan_phase(s, p, ["beaker"]) == solo
    paired = sc.plan_phase(s, p, ["beaker", "pill"])
    if choice == "handoff":
        assert paired["cost"] == round(base["cost"] * 0.95, 2)
    else:
        # Formulation is quality-focused; chemistry precision cannot boost it.
        assert paired["noise_by_stat"] == base["noise_by_stat"]
        a = sc.plan_phase(s, p, ["beaker", "pill"], key="be")
        s["heroes"][0].pop("personal")
        b = sc.plan_phase(s, p, ["beaker", "pill"], key="be")
        assert a["noise_by_stat"]["exposure"] == pytest.approx(b["noise_by_stat"]["exposure"] * 0.92)
    assert sc.selected(p)["truth"] == truth


def test_clinical_quest_improves_clinical_observation_not_lab_assays():
    s = ready("innovative", strong=True)
    ids = ["ruler", "sprout"]
    p = s["projects"][0]
    baseline = sc.plan_phase(s, p, ids, key="II")
    lab = sc.plan_phase(s, p, ids, key="preclinical")
    next(h for h in s["heroes"] if h["id"] == "ruler")["personal"] = {"choice": "verify"}
    clinical = sc.plan_phase(s, p, ids, key="II")
    assert clinical["noise"] == pytest.approx(baseline["noise"] * 0.92)
    assert sc.plan_phase(s, p, ids, key="preclinical") == lab


def test_checkpoint_is_persisted_readonly_and_pauses_without_releasing_staff_or_budget():
    s = checkpoint()
    p = s["projects"][0]
    assert p["status"] == "checkpoint"
    assert not p["results"]
    before = dumps(s)
    assert snapshot(s)["projects"][0]["trial_decision"]
    assert dumps(s) == before
    assert loads(before) == s
    reserve, left = committed(s), p["left"]
    with pytest.raises(ValueError):
        g.execute(s, "advance", {"weeks": 1})
    s = g.execute(s, "defer", {"project": "1", "waiting": 1})
    research_paid = s["expense"]["research"]
    s = g.execute(s, "advance", {"weeks": 4})
    assert s["projects"][0]["left"] == left
    assert committed(s) == reserve
    assert s["expense"]["research"] == research_paid
    assert {"ruler", "bubble"} <= busy(s).keys()


@pytest.mark.parametrize(
    "key,choice", [("I", "monitor"), ("II", "representative"), ("III", "audit"), ("III", "remote")]
)
def test_trial_choice_changes_operations_not_candidate_and_cannot_repeat(key, choice):
    s = checkpoint(key)
    p = s["projects"][0]
    before = copy.deepcopy(sc.selected(p))
    reserve = committed(s)
    old_cash = s["cash"]
    s = g.execute(s, "trial_decision", {"project": "1", "choice": choice})
    p = s["projects"][0]
    assert sc.selected(p) == before
    assert committed(s) == pytest.approx(reserve)
    assert s["cash"] < old_cash
    assert p["execution"]["probability"] == sc.phase_probability(
        p, key, p["execution"]["plan"], p["execution"]["noise_by_stat"]
    )
    with pytest.raises(ValueError):
        g.execute(s, "trial_decision", {"project": "1", "choice": choice})
    s = g.execute(s, "advance", {"weeks": 48})
    assert s["projects"][0]["status"] == "result"


def test_keep_works_with_no_uncommitted_money_and_regional_restriction_persists():
    s = checkpoint()
    s["cash"] = committed(s)
    free = g.execute(s, "trial_decision", {"project": "1", "choice": "keep"})
    assert free["cash"] == s["cash"]
    s = g.execute(s, "trial_decision", {"project": "1", "choice": "regional"})
    assert s["projects"][0]["trial_reach"] == 0.85
    s = g.execute(s, "advance", {"weeks": 48})
    s["cash"] = 20000
    s = g.execute(s, "continue_project", {"project": "1"})
    s = complete_phase(s)
    assert s["projects"][0]["trial_reach"] == 0.85


def test_continue_and_run_preview_uses_next_stage_without_mutation_and_is_atomic():
    s = complete_phase(ready(strong=True))
    before = dumps(s)
    public = snapshot(s)["projects"][0]
    assert public["next_stage"]["key"] == "quality"
    args = {"project": "1", "heroes": ["beaker", "pill"]}
    preview = phase_preview(s, args)
    assert dumps(s) == before
    result = g.execute(s, "continue_and_run", args)
    assert result["projects"][0]["execution"]["key"] == "quality"
    assert preview["cost"] == result["projects"][0]["execution"]["cost"]
    s["cash"] = 0
    before = dumps(s)
    with pytest.raises(ValueError):
        g.execute(s, "continue_and_run", args)
    assert dumps(s) == before and s["projects"][0]["status"] == "result"


def test_batch_services_roll_back_every_order_on_duplicate_worker():
    s = new_game(7)
    o = next(o for o in e.orders(s) if o["profession"] == "proc")
    before = dumps(s)
    item = {"order": o["id"], "character": "pill"}
    with pytest.raises(ValueError):
        g.execute(s, "take_services", {"assignments": [item, item]})
    assert dumps(s) == before
    assert len(g.execute(s, "take_services", {"assignments": [item]})["jobs"]) == 1


def test_challenge_upkeep_is_fixed_public_and_charged_as_forecast():
    s = new_game(9, difficulty="competition")
    s["facility"] = 2
    s = g.execute(s, "platform_policy", {"policy_name": "frontier"})
    assert challenge.upkeep(s) == 16 * 1.65
    cost = e.costs_per_week(s)
    out = g.execute(s, "advance", {"weeks": 1})
    assert s["cash"] - out["cash"] == pytest.approx(cost)
    assert out["expense"]["platform_maintenance"] == challenge.upkeep(s)
    s["cash"] *= 100
    assert challenge.upkeep(s) == 26.4
    normal = new_game(9)
    assert challenge.upkeep(normal) == 0
    with pytest.raises(ValueError):
        g.execute(normal, "platform_policy", {"policy_name": "lean"})


def test_market_capacity_bounds_aggregate_sales_and_never_touches_approval_limits():
    s = ready(strong=True)
    p = s["projects"][0]
    s["week"] = 100
    d = e.make_product(s, p)
    d.update(peak=10000, launched=70)
    limits = sc.limits(p, "review")
    normal_sales = e.expected_sales(s, d)[0]
    s["difficulty"] = "competition"
    assert 0 < e.expected_sales(s, d)[0] <= challenge.CAPACITY[d["market"]] < normal_sales
    assert sc.limits(p, "review") == limits


@pytest.mark.parametrize("catalog", list(product_design.PROFILES))
def test_profile_has_real_constraint_and_commercial_reward_requires_pass(catalog):
    info = product_design.profile(catalog)
    p = {"catalog": catalog, "design": "validated", "results": []}
    assert product_design.reward(p) is None
    assert product_design.adjust_limits(p, info["stage"], {})[info["stat"]] == info["limit"]
    p["results"] = [{"key": info["stage"], "passed": False}]
    assert product_design.reward(p) is None
    p["results"][0]["passed"] = True
    assert product_design.reward(p) == info["reward"]
    p["design"] = "standard"
    assert product_design.reward(p) is None


def test_enhanced_validation_changes_only_profile_stage_and_does_not_inflate_truth():
    s = ready(strong=True)
    p = s["projects"][0]
    original = copy.deepcopy(sc.selected(p))
    basic = sc.plan_phase(s, p, ["beaker", "pill"], key="review")
    first = sc.plan_phase(s, p, ["beaker", "pill"])
    p["design"] = "validated"
    strong = sc.plan_phase(s, p, ["beaker", "pill"], key="review")
    assert strong["cost"] == round(basic["cost"] * 1.25, 2)
    assert strong["weeks"] == basic["weeks"] + 2
    assert strong["noise"] == pytest.approx(basic["noise"] * 0.8)
    assert sc.plan_phase(s, p, ["beaker", "pill"]) == first
    assert sc.selected(p) == original


def test_v5_save_rejected_and_v6_challenge_replay_identical():
    with pytest.raises(ValueError, match="v6"):
        loads('{"version":5}')
    s = new_game(5, difficulty="competition")
    s = g.execute(s, "platform_policy", {"policy_name": "lean"})
    s = g.execute(s, "advance", {"weeks": 4})
    assert g.replay(5, "foundation", s["actions"], difficulty="competition") == s


def test_preview_unknown_project_returns_actionable_error():
    with pytest.raises(ValueError, match="没有这个研究项目"):
        phase_preview(new_game(), {"project": "missing", "heroes": []})
