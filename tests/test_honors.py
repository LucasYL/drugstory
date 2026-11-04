"""v0.5 boundaries; crafted fixtures here are separate from resource-free play studies."""

import copy
import json

import pytest

from drugstory.career import competition as rivals
from drugstory.career import engine as g
from drugstory.career import honors as h
from drugstory.career import science as sc
from drugstory.career.model import busy, dumps, make_hero, new_game
from drugstory.career.view import snapshot
from tests.test_career import complete_phase, ready


def breakthrough():
    s = ready("innovative", seed=4, strong=True)
    p = s["projects"][0]
    p["catalog"] = "n_resistance"
    for hero in s["heroes"]:
        hero["rank"] = 3
        hero["training"] = 30
    s["facility"] = 2
    s["cash"] = s["capital"] = 100000
    for index in range(6):
        s = complete_phase(s)
        assert s["projects"][0]["status"] == "result"
        if index < 5:
            s = g.execute(s, "continue_project", {"project": "1"})
    return g.execute(s, "launch", {"project": "1"})


def advance_until(s, week):
    while s["week"] < week:
        s = g.execute(s, "advance", {"weeks": 4 if week - s["week"] >= 4 else 1})
    return s


def test_empty_company_cannot_buy_recognition_or_get_first_year_award():
    s = new_game()
    s["cash"] = 1e8
    with pytest.raises(ValueError):
        g.execute(s, "nominate", {"category": "quality"})
    s = g.execute(s, "next_event")
    assert s["week"] == 48 and len(s["festivals"]) == 1 and not s["awards"]
    assert all(r["winner"] == "本届空缺" for r in s["festivals"][0]["results"])
    assert not any(c["eligible"] for c in h.categories(s))


def test_annual_nomination_result_accounting_and_no_duplicate_reward():
    s = breakthrough()
    s = g.execute(s, "nominate", {"category": "innovation"})
    deadline = s["season"]["year"] * 48
    s = advance_until(s, deadline)
    award = s["awards"][-1]
    assert award["category"] == "innovation" and award["prize"] == 300
    assert s["income"]["awards"] == 300
    assert any(r["won"] for r in s["festivals"][-1]["results"])
    before = dumps(s)
    h.annual(s)
    assert dumps(s) == before
    assert not s["season"]["entry"]
    with pytest.raises(ValueError):
        g.execute(s, "nominate", {"category": "innovation"})


def test_nomination_deadline_is_enforced_and_readonly_scores_use_public_evidence():
    s = breakthrough()
    a = h.categories(s)
    sc.selected(s["projects"][0])["truth"]["effect"] = 5
    assert h.categories(s) == a
    s = advance_until(s, s["season"]["year"] * 48 - 1)
    with pytest.raises(ValueError, match="截止"):
        g.execute(s, "nominate", {"category": "innovation"})


def test_declining_awards_do_not_mint_cash_without_an_entry():
    s = breakthrough()
    s = advance_until(s, s["season"]["year"] * 48)
    assert not s["awards"] and not s["income"].get("awards")
    assert all(r["reason"] == "未报名" for r in s["festivals"][-1]["results"])


def test_specialization_requires_elite_is_once_and_keeps_hidden_properties():
    s = ready()
    before = copy.deepcopy(sc.selected(s["projects"][0])["truth"])
    with pytest.raises(ValueError):
        g.execute(s, "specialize", {"character": "pill", "track": "precision"})
    s["heroes"][1]["rank"] = 2
    old = sc.plan_phase(s, s["projects"][0], ["pill"])
    s = g.execute(s, "specialize", {"character": "pill", "track": "precision"})
    new = sc.plan_phase(s, s["projects"][0], ["pill"])
    assert new["noise_by_stat"]["quality"] < old["noise_by_stat"]["quality"]
    assert sc.selected(s["projects"][0])["truth"] == before
    with pytest.raises(ValueError):
        g.execute(s, "specialize", {"character": "pill", "track": "efficiency"})


def test_personal_traits_are_real_and_do_not_stack_unrelated_stars():
    s = ready()
    p = s["projects"][0]
    solo = sc.plan_phase(s, p, ["pill"])
    team = sc.plan_phase(s, p, ["pill", "beaker"])
    assert team["cost"] < solo["cost"]  # Beaker's thrift.
    s["heroes"].append(make_hero("strategist"))
    irrelevant = sc.plan_phase(s, p, ["pill", "strategist"])
    assert irrelevant["weeks"] == solo["weeks"]  # Clinical speed cannot accelerate formulation.


def test_independent_validation_requires_relevant_team_and_locks_duplicate_work():
    s = breakthrough()
    d = s["products"][0]
    option = h.proof_options(s)[0]
    assert option["available"] and option["weeks"] == 52
    with pytest.raises(ValueError):
        g.execute(s, "independent_study", {"product": d["id"], "heroes": ["beaker", "pill"]})
    s = g.execute(s, "independent_study", {"product": d["id"], "heroes": ["sprout", "ruler"]})
    assert {"sprout", "ruler"} <= busy(s).keys()
    running = h.view(s)["studies"][0]
    assert not running["available"]
    assert running["running"] == {"left": 52, "heroes": ["sprout", "ruler"]}
    with pytest.raises(ValueError):
        g.execute(s, "independent_study", {"product": d["id"], "heroes": ["sprout", "ruler"]})
    week = s["week"]
    s = advance_until(s, week + 52)
    assert s["proofs"][0]["passed"] and h.proof_options(s)[0]["step"] == 1
    assert h.view(s)["studies"][0]["running"] is None
    s = g.execute(s, "independent_study", {"product": d["id"], "heroes": ["ruler", "bubble"]})
    s = advance_until(s, s["week"] + 48)
    assert len(s["proofs"]) == 2 and all(p["passed"] for p in s["proofs"])
    assert not h.proof_options(s)
    assert s["expense"]["independent_research"] == 2300


def test_negative_independent_result_is_persistent_and_cannot_reroll():
    s = breakthrough()
    d = s["products"][0]
    sc.selected(s["projects"][0])["truth"]["effect"] = 30
    s = g.execute(s, "independent_study", {"product": d["id"], "heroes": ["sprout", "ruler"]})
    s = advance_until(s, s["week"] + 52)
    assert not s["proofs"][0]["passed"] and not h.proof_options(s)
    with pytest.raises(ValueError):
        g.execute(s, "independent_study", {"product": d["id"], "heroes": ["sprout", "ruler"]})


def test_final_award_is_not_a_single_approval_and_is_granted_once_at_ceremony():
    s = breakthrough()
    d = s["products"][0]
    assert not all(c["ok"] for c in h.legacy_progress(s)[0]["checks"])
    for ids in (["sprout", "ruler"], ["ruler", "bubble"]):
        s = g.execute(s, "independent_study", {"product": d["id"], "heroes": ids})
        s = advance_until(s, s["week"] + 52)
    s["heroes"][0]["rank"] = 4
    s["heroes"][1]["mentored"] = ["forge", "architect"]
    s["awards"] = [{"category": "quality"}, {"category": "mentorship"}]
    s = advance_until(s, 432)
    assert sum(item["key"] == "science" for item in s["legacies"]) == 1
    s = advance_until(s, 480)
    assert sum(item["key"] == "science" for item in s["legacies"]) == 1


def test_rivals_are_reproducible_but_seeds_have_different_trajectories():
    outcomes = []
    for seed in range(8):
        s = new_game(seed)
        other = new_game(seed)
        for week in range(1, 961):
            s["week"] = other["week"] = week
            rivals.step(s)
            rivals.step(other)
        assert s["rivals"] == other["rivals"]
        outcomes.append(json.dumps(s["rivals"], sort_keys=True))
        assert any(r["history"] for r in s["rivals"])
        assert any(r["cycles"] for r in s["rivals"])
    assert len(set(outcomes)) == 8


def test_market_pressure_is_local_capped_and_does_not_change_clinical_limits():
    s = ready("innovative")
    p = s["projects"][0]
    before = sc.limits(p, "III")
    s["rivals"][0]["portfolio"] = [
        {"market": "lung", "active": True, "strength": 2, "end": 2000, "launched": 0} for _ in range(6)
    ]
    assert rivals.pressure(s, "lung") == 3 and rivals.pressure(s, "pain") == 0
    assert sc.limits(p, "III") == before


def test_public_new_systems_are_readonly_and_do_not_leak_candidate_truth():
    s = ready("innovative")
    before = dumps(s)
    view = snapshot(s)
    assert dumps(s) == before and len(view["honors"]["legacies"]) == 3
    assert len(view["honors"]["categories"]) == 4
    assert all(isinstance(r["history"], list) for r in view["rivals"])
    serialized = json.dumps(view)
    assert '"truth"' not in serialized and '"mechanisms"' not in serialized
