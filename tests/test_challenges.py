"""v0.13 三种难病的搭档关：每道关缺人、部分、全齐的效果，立项定下的关，合作方没有你的人。"""

import pytest

from drugstory.career import gates
from drugstory.career.content import CATALOG
from drugstory.career.model import make_hero, new_game


def team(*keys, seed=1):
    s = new_game(seed)
    s["heroes"] = [{**make_hero(k), "joined": 0} for k in keys]
    return s


def project(catalog, **extra):
    return {"catalog": catalog, "population": "focused", **extra}


@pytest.mark.parametrize(
    ("catalog", "target"),
    [("n_kras__small_molecule", "kras"), ("n_hbv__sirna", "hbv"), ("n_rna", "lpa"), ("n_abeta__mab", "abeta")],
)
def test_every_hard_disease_has_gates(catalog, target):
    assert CATALOG[catalog]["target_id"] == target
    assert gates.applies(catalog)
    rows = gates.view(team("beaker"), catalog)
    assert rows and all(r["title"] for r in rows)


def test_ordinary_targets_have_no_gates():
    p = project("g_pressure")
    assert not gates.applies("g_pressure")
    assert gates.effects(team("beaker"), p, "III") == {"limits": {}, "noise": 1.0, "weeks": 1.0}
    assert gates.peak_factor(team("beaker"), p) == 1.0


def test_kras_effects_by_team():
    p = project("n_kras__small_molecule")
    none = gates.effects(team("beaker"), p, "III")
    part = gates.effects(team("wizard", "star", "shield"), p, "III")
    full = gates.effects(team("alchemist", "bridge", "guardian"), p, "III")
    assert none["limits"]["effect"] > part["limits"]["effect"] > full["limits"].get("effect", 0) == 0
    assert none["noise"] > part["noise"] > full["noise"] == 1.0
    assert gates.effects(team("beaker"), p, "I")["limits"]["safety"] > 0


def test_resistance_needs_focused_population():
    s = team("bridge")
    focused = gates.status(s, "n_kras__small_molecule", project("n_kras__small_molecule"))
    broad = gates.status(s, "n_kras__small_molecule", project("n_kras__small_molecule", population="broad"))
    assert focused["resistance"]["state"] == "full"
    assert broad["resistance"]["state"] == "partial"


def test_hbv_cccdna_is_locked_by_design():
    small = team("star")
    p = project("n_hbv__small_molecule")
    gates.lock_design(small, p)
    assert p["gates"]["cccdna"] == "none", "小分子：请到谁也解决不了"

    p = project("n_hbv__sirna")
    gates.lock_design(team("beaker"), p)
    assert p["gates"]["cccdna"] == "partial"
    # 立项之后才请到叶清和，也改不了
    assert gates.status(team("star"), "n_hbv__sirna", p)["cccdna"]["state"] == "partial"

    p = project("n_hbv__sirna")
    gates.lock_design(team("star"), p)
    assert p["gates"]["cccdna"] == "full"
    assert gates.effects(team("beaker"), p, "II")["limits"].get("effect", 0) == 0


def test_hbv_liver_and_cure():
    p = project("n_hbv__sirna", gates={"cccdna": "full"})
    assert gates.effects(team("beaker"), p, "preclinical")["limits"]["safety"] > 0
    assert gates.effects(team("judge"), p, "preclinical")["limits"].get("safety", 0) == 0
    assert gates.effects(team("beaker"), p, "III")["noise"] > gates.effects(team("curve"), p, "III")["noise"] > 1


def test_lpa_outcome_dosing_people():
    p = project("n_rna")
    none = gates.effects(team("beaker"), p, "III")
    full = gates.effects(team("oracle", "bridge"), p, "III")
    part = gates.effects(team("strategist", "ruler"), p, "III")
    assert none["weeks"] > 1 and part["weeks"] == full["weeks"] == 1
    assert none["noise"] > part["noise"] > full["noise"] == 1
    assert gates.effects(team("beaker"), p, "review")["limits"]["quality"] > 0
    assert gates.peak_factor(team("beaker"), p) < gates.peak_factor(team("crystal"), p) < 1
    assert gates.peak_factor(team("forge"), p) == 1


def test_partner_has_none_of_your_people_except_locked():
    p = project("n_hbv__sirna")
    s = team("star", "oracle", "judge")
    gates.lock_design(s, p)
    own = gates.effects(s, p, "III")
    licensed = gates.effects(s, p, "III", partner=True)
    assert own["noise"] == 1 and licensed["noise"] > 1
    assert licensed["limits"].get("effect", 0) == 0, "立项定下的 cccDNA 关不随授权变化"

    q = project("n_rna")
    s = team("forge")
    assert gates.peak_factor(s, q) == 1 and gates.peak_factor(s, q, partner=True) < 1


def test_alzheimer_gates_unchanged():
    assert [g["key"] for g in gates.CHALLENGES["abeta"]["gates"]] == ["bbb", "population", "aria", "endpoint"]
    assert set(gates.GATES) == {"bbb", "population", "aria", "endpoint"}
