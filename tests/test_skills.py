"""v0.11 角色：潜力上限、改变规则的专长、传奇退休与传承、天赋角色李天天。

这些是边界单测，会直接构造人物阶位和训练值，与正常经营的模拟记录分开说明。
"""

import pytest

from drugstory.career import engine as g
from drugstory.career import science as sc
from drugstory.career import talents
from drugstory.career.content import CATALOG
from drugstory.career.model import ability, make_hero, new_game
from drugstory.career.view import snapshot
from tests.test_career import ready


def maxed(key, rank=4):
    h = make_hero(key)
    h.update(rank=rank, training=80, xp=500)
    return h


def test_potential_caps_by_origin_and_prodigy_is_highest():
    assert ability(maxed("beaker")) == 88
    assert ability(maxed("catalyst")) == 91
    assert ability(maxed("wizard")) == 94
    assert ability(maxed("alchemist")) == 97
    assert ability(maxed("prodigy")) == 99
    assert ability(maxed("beaker", rank=2)) == 66, "阶位仍然限制当前能力"


def test_prodigy_joins_by_letter_and_learns_faster():
    s = new_game(5)
    row = next(r for r in snapshot(s)["roster"] if r["key"] == "prodigy")
    assert not row["unlocked"] and row["potential"] == 99
    s["week"] = 96
    s["heroes"][0]["rank"] = 2
    row = next(r for r in snapshot(s)["roster"] if r["key"] == "prodigy")
    assert row["unlocked"]
    s = g.execute(s, "hire", {"character": "prodigy"})
    tian = next(h for h in s["heroes"] if h["id"] == "prodigy")
    assert tian["prodigy"] and tian["joined"] == 96
    from drugstory.career.model import gain_work

    gain_work(s, ["prodigy", "beaker"], "test", 10)
    assert tian["xp"] == 15 and s["heroes"][0]["xp"] == 10


def test_legends_retire_after_eight_years_and_cannot_be_rehired():
    s = new_game(6)
    s["cash"] = 1e6
    s["heroes"].append(make_hero("guardian"))
    s["heroes"][-1]["joined"] = 0
    while s["week"] < 7 * 48:
        s = g.execute(s, "advance", {"weeks": 48})
    assert s["heroes"][-1].get("retire_notice") and s["heroes"][-1]["employed"]
    while s["week"] < 8 * 48 + 4:
        s = g.execute(s, "advance", {"weeks": 4})
    h = s["heroes"][-1]
    assert not h["employed"] and h["retired"]
    row = next(r for r in snapshot(s)["roster"] if r["key"] == "guardian")
    assert not row["unlocked"]


def test_inheritance_passes_a_skill_once_and_prodigy_can_take_two_professions():
    s = new_game(7)
    s["cash"] = 1e6
    s["heroes"] += [make_hero("guardian"), make_hero("bubble"), make_hero("prodigy"), make_hero("oracle")]
    assert g.inherit_options(s, "guardian") == ["bubble"], "同专业弟子；未觉醒的李天天不能跨专业"
    s = g.execute(s, "inherit", {"teacher": "guardian", "pupil": "bubble"})
    for _ in range(3):
        s = g.execute(s, "advance", {"weeks": 4})
    pupil = next(h for h in s["heroes"] if h["id"] == "bubble")
    assert pupil["inherited"] == ["shield"] and talents.has(s, "shield") == 1
    assert s["inheritances"][0]["teacher"] == "guardian"
    assert g.inherit_options(s, "guardian") == [], "每位传奇只传承一次"
    tian = next(h for h in s["heroes"] if h["id"] == "prodigy")
    tian.update(rank=3, personal={"choice": "practice"})
    assert "prodigy" in g.inherit_options(s, "oracle")
    s = g.execute(s, "inherit", {"teacher": "oracle", "pupil": "prodigy"})
    for _ in range(3):
        s = g.execute(s, "advance", {"weeks": 4})
    assert next(h for h in s["heroes"] if h["id"] == "prodigy")["inherited"] == ["oracle"], "学传奇本人的专长"


def test_sprint_shortens_optimization_and_multicentre_adds_a_slot():
    s = ready("innovative")
    p = s["projects"][0]
    fast = sc.plan_phase(s, p, ["beaker", "sprout"])
    slow = sc.plan_phase(s, p, ["sprout"])
    assert fast["weeks"] < slow["weeks"]
    before = g.clinical_slots(s)
    s["heroes"].append(make_hero("strategist"))
    assert g.clinical_slots(s) == before + 1


def test_scout_and_star_reveal_route_information_before_screening():
    s = new_game(8)
    key = "n_abeta__mab"
    row = next(c for c in snapshot(s)["catalog"] if c["key"] == key)
    assert row["discovery"] is None
    s["heroes"].append(make_hero("scout"))
    row = next(c for c in snapshot(s)["catalog"] if c["key"] == key)
    assert row["discovery"]["tier"] == CATALOG[key]["combo_tier"] and row["discovery"]["scouted"]
    s["heroes"].append(make_hero("star"))
    row = next(c for c in snapshot(s)["catalog"] if c["key"] == key)
    assert isinstance(row["discovery"]["mechanism"], int)
    assert s["mechanisms"] == {}, "只读，不写入机制表"


def test_impossible_molecule_lifts_a_minus_one_route():
    hard = next(k for k, c in CATALOG.items() if c["kind"] == "innovative" and c.get("combo_tier") == -1)
    s = new_game(9)
    spec = CATALOG[hard]
    assert sc.combo_tier(s, spec, ["beaker"]) == -1
    s["heroes"].append(make_hero("alchemist"))
    assert sc.combo_tier(s, spec, ["alchemist"]) == 0


def test_mine_clearing_turns_an_i_phase_safety_failure_into_a_repair():
    s = ready("innovative", seed=4, strong=True)
    p = s["projects"][0]
    p["index"] = 2  # 边界单测：直接到 I 期
    for c in p["candidates"]:
        c["truth"]["safety"] = 50.0
    s["heroes"].append(make_hero("shield"))
    s = g.execute(s, "run_phase", {"project": "1", "heroes": ["shield"], "mode": "cro"})
    while s["projects"][0]["status"] in ("running", "checkpoint"):
        if s["projects"][0]["status"] == "checkpoint":
            s = g.execute(s, "trial_decision", {"project": "1", "choice": "keep"})
        else:
            s = g.execute(s, "advance", {"weeks": 4})
    p = s["projects"][0]
    assert p["results"][-1]["failures"] == ["safety"]
    assert p["status"] == "problem"


def test_recheck_halves_validation_cost_and_allows_a_third_check():
    from drugstory.career.content import EXPERIMENTS

    s = ready("innovative")  # 娜迪亚（bubble）已在团队里
    p = s["projects"][0]
    nadia = sc.experiment_plan(s, p, "validate", "safety", ["bubble"])
    assert nadia["cost"] == pytest.approx(EXPERIMENTS["validate"]["cost"] / 2)
    sc.selected(p)["checks"]["validatesafety"] = 2
    assert sc.experiment_plan(s, p, "validate", "safety", ["bubble"]), "第三次复核"
    sc.selected(p)["checks"]["validatesafety"] = 3
    with pytest.raises(ValueError):
        sc.experiment_plan(s, p, "validate", "safety", ["bubble"])


# ---- 阿尔茨海默四道关（边界单测：直接构造在职人物） ----


def test_alzheimer_card_lists_four_gates_and_who_can_solve_them():
    from drugstory.career import gates

    s = new_game(10)
    card = next(c for c in snapshot(s)["catalog"] if c["key"] == "n_abeta__mab")["gates"]
    assert [g["name"] for g in card] == ["入脑", "选对人", "脑水肿", "长终点"]
    assert all(g["state"] == "none" and g["full"] and g["partial"] for g in card)
    assert next(c for c in snapshot(s)["catalog"] if c["key"] == "n_lung")["gates"] is None
    forge = make_hero("forge")
    forge.update(rank=3, personal={"choice": "practice"})
    s["heroes"] += [forge, make_hero("guardian"), make_hero("strategist")]
    rows = gates.status(s, "n_abeta__mab")
    assert rows["bbb"]["state"] == "full" and rows["aria"]["state"] == "full"
    assert rows["endpoint"]["state"] == "partial" and rows["endpoint"]["people"] == ["欧阳岚"]
    assert gates.status(s, "n_abeta__aso")["bbb"]["state"] == "partial"


def test_gate_penalties_reach_thresholds_noise_and_weeks():
    from drugstory.career import gates

    s = new_game(11)
    p = {"catalog": "n_abeta__mab", "population": "standard", "gates": {"bbb": "none"}}
    ii = gates.effects(s, p, "II")
    assert ii["limits"]["effect"] == 15 + 12
    iii = gates.effects(s, p, "III")
    assert iii["limits"]["safety"] == 18 and iii["noise"] == 2.4 and iii["weeks"] == 1.4
    assert gates.effects(s, {**p, "catalog": "n_lung"}, "III") == {"limits": {}, "noise": 1.0, "weeks": 1.0}
    s["heroes"].append(make_hero("bridge"))
    focused = gates.effects(s, {**p, "population": "focused"}, "II")["limits"]["effect"]
    assert focused == 15, "沈墨言 + 分层入组：选对人完全解决"


def test_impossible_combinations_cannot_pass_phase_two_on_luck():
    s = new_game(12)
    s["knowledge"] = dict.fromkeys(s["knowledge"], 100)
    s.update(facility=3, cash=1e6)
    s["heroes"] = [make_hero("bridge"), make_hero("wizard")]
    for h in s["heroes"]:
        h["rank"] = 3
    s = g.execute(s, "start_project", {"catalog": "n_abeta__small_molecule", "heroes": ["bridge", "wizard"]})
    gate = sc.STAGES["II"]["limits"]["effect"]
    assert all(c["truth"]["effect"] <= gate - 8 for c in s["projects"][0]["candidates"])
