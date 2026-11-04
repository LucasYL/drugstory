import pytest

from drugstory.engine import actions as A
from drugstory.engine import decisions as D
from drugstory.engine.game import new_game
from drugstory.engine.loop import advance
from drugstory.engine.rules.scoring import composite, expert_score, standard
from drugstory.engine.state import APPROVED, CLINICAL, FAILED, NAMING, PHASE_REVIEW, TERMINATED, Drug, Hazard, Project
from drugstory.engine.systems import clinical


def in_clinic(state, content, target="egfr", modality="small_molecule", level=1.0, hazards=()):
    """直接造一个刚进入 I 期的项目，四项属性都是 level × 当年审评标准。"""
    t = content.targets[target]
    project = Project(id=state.new_id(), target=target, modality=modality, stage=CLINICAL, team_ids=[], rd_weeks=1)
    base = standard(t, "NDA", "efficacy", state.week, content)
    project.stats = {s: level * base for s in ("efficacy", "druggability", "safety", "manufacturability")}
    project.hazards = list(hazards)
    state.projects.append(project)
    clinical.start_phase(state, project, "I", content)
    return project


def finish_phase(state, content, project):
    while not state.pending:
        advance(state, content, 1)
    return state.pending[0]


def test_phase_plan_uses_the_disease_and_modality_factors(quiet):
    p = Project(id=1, target="tnf", modality="mab", stage="", team_ids=[], rd_weeks=1)
    weeks, cost = clinical.phase_plan(p, "III", quiet)
    assert weeks == round(24 * 1.0)
    assert cost == pytest.approx(450 * 1.0 * 1.3)


def test_costs_are_paid_every_week(quiet):
    s = new_game(1, quiet)
    p = in_clinic(s, quiet)
    weekly = p.phase_weekly_cost
    cash = s.cash
    advance(s, quiet, 2)
    assert cash - s.cash == round(weekly) * 2 or cash - s.cash == pytest.approx(2 * weekly, abs=1)


def test_scores_follow_the_formula(quiet):
    s = new_game(1, quiet)
    p = in_clinic(s, quiet, level=1.0)
    d = finish_phase(s, quiet, p)
    result = p.results[-1]
    t = quiet.targets["egfr"]
    for stat, score in result.scores.items():
        std = standard(t, "I", stat, s.week - 1, quiet)
        assert score == expert_score(p.stats[stat], std, 0, quiet)
    # 属性等于审评标准，I 期的标准只有 0.8 倍：7 ÷ 0.8 ≈ 8.75 → 9 分
    assert result.scores == {"safety": 9, "druggability": 9}
    assert d.kind == D.PHASE_RESULT and d.data == {"phase": "I", "passed": True, "next": "II"}
    assert p.stage == PHASE_REVIEW


def test_a_strong_drug_goes_all_the_way(quiet):
    s = new_game(1, quiet)
    p = in_clinic(s, quiet, level=1.1)
    for phase in ("I", "II", "III"):
        d = finish_phase(s, quiet, p)
        assert d.data["phase"] == phase and d.data["passed"]
        A.resolve_phase(s, quiet, decision_id=d.id, choice="continue")
    d = finish_phase(s, quiet, p)
    assert d.kind == D.APPROVAL and p.stage == NAMING
    assert p.composite == composite(p.results, quiet)
    drug_id = A.name_drug(s, quiet, decision_id=d.id, name=d.data["suggested"])
    assert p.stage == APPROVED
    drug = s.drug(drug_id)
    assert drug.name == d.data["suggested"] and drug.name.endswith("tinib")
    assert s.reputation > 0 and s.current_year.approvals == 1


def test_a_weak_drug_fails_and_loses_reputation(quiet):
    s = new_game(1, quiet)
    s.reputation = 10.0
    p = in_clinic(s, quiet, level=0.3)
    d = finish_phase(s, quiet, p)
    assert d.data == {"phase": "I", "passed": False}
    assert p.stage == FAILED
    assert s.reputation == 9.0
    assert s.modality_proficiency["small_molecule"] == 1
    with pytest.raises(A.ActionError):
        A.resolve_phase(s, quiet, decision_id=d.id, choice="continue")
    A.resolve_phase(s, quiet, decision_id=d.id, choice="ack")
    assert not s.pending


def test_hazards_explode_in_their_phase(quiet):
    s = new_game(1, quiet)
    hazard = Hazard(id=99, stat="safety", severity=2, text="代谢产物有肝毒性", phase="I")
    p = in_clinic(s, quiet, level=1.0, hazards=[hazard])
    finish_phase(s, quiet, p)
    result = p.results[-1]
    assert result.scores["safety"] == 9 - 2
    assert result.hazard_texts == ["I 期出现「代谢产物有肝毒性」，安全性专家扣 2 分"]


def test_terminating_between_phases(quiet):
    s = new_game(1, quiet)
    p = in_clinic(s, quiet)
    d = finish_phase(s, quiet, p)
    A.resolve_phase(s, quiet, decision_id=d.id, choice="terminate")
    assert p.stage == TERMINATED and not s.pending


def test_approvals_do_not_move_the_clinical_goalposts(quiet):
    s = new_game(1, quiet)
    t = quiet.targets["tnf"]
    base = standard(t, "III", "efficacy", 0, quiet)
    s.drugs.append(
        Drug(
            id=1,
            project_id=0,
            name="Old",
            target="tnf",
            modality="mab",
            composite=80,
            peak=1,
            margin=0.5,
            launched_week=0,
        )
    )
    assert clinical.prior_approvals(s, "tnf") == 1
    assert standard(t, "III", "efficacy", 0, quiet, 1) == pytest.approx(base)
    # 同类药竞争由市场系统处理
    assert standard(t, "III", "safety", 0, quiet, 1) == standard(t, "III", "safety", 0, quiet)
    assert standard(t, "NDA", "efficacy", 0, quiet, 1) == standard(t, "NDA", "efficacy", 0, quiet)


def test_standards_stay_fixed_over_twenty_years(quiet):
    t = quiet.targets["egfr"]
    year1 = standard(t, "II", "efficacy", 0, quiet)
    year20 = standard(t, "II", "efficacy", 19 * 48, quiet)
    assert year20 == pytest.approx(year1)
