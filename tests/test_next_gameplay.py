import random

import pytest

from drugstory.content import STATS
from drugstory.engine import actions as A
from drugstory.engine import decisions as D
from drugstory.engine.loop import advance
from drugstory.engine.save import from_json, to_json
from drugstory.engine.state import CLINICAL, ON_PROJECT, PHASE_REVIEW, QUEUED, RD_REVIEW, Hazard, Project
from drugstory.engine.systems import clinical, research
from drugstory.ui.web_view import snapshot


def ready(s, c, team_ids=()):
    p = Project(id=s.new_id(), target="egfr", modality="small_molecule", stage=RD_REVIEW,
                team_ids=list(team_ids), rd_weeks=27, base_rd_weeks=27, rd_done=27, milestones_done=4,
                extension_count=0, stats={k: 500.0 for k in STATS})
    s.projects.append(p)
    for tid in team_ids:
        s.team(tid).task, s.team(tid).task_id = ON_PROJECT, p.id
    d = D.add(s, D.RD_END, p.id)
    return p, d


def enter(s, c, mode="proceed", team_ids=()):
    p, d = ready(s, c, team_ids)
    A.resolve_rd_end(s, c, decision_id=d.id, choice=mode)
    return p


def node(s, c):
    pid = A.start_project(s, c, target="egfr", modality="small_molecule", team_ids=[1, 2])
    while not s.pending:
        advance(s, c, 1)
    return s.project(pid), s.pending[0]


def test_queue_frees_researchers_and_does_not_stop_time_or_charge_trials(quiet, fresh):
    p1 = enter(fresh, quiet, team_ids=[1])
    p2 = enter(fresh, quiet, team_ids=[2])
    assert p1.stage == CLINICAL and p2.stage == QUEUED
    assert all(t.idle for t in fresh.teams) and not fresh.pending
    advance(fresh, quiet, 1)
    assert fresh.week == 1 and p1.spent > 0 and p2.spent == 0
    assert clinical.operations(fresh, quiet)["queue"] == [p2.id]
    v = snapshot(fresh, quiet)
    assert v["projects"][1]["queue_position"] == 1
    assert v["projects"][1]["forecasts"][0]["finish"] == "排队时间未计入"
    assert from_json(to_json(fresh)) == fresh


def test_queue_is_fifo_and_starts_after_a_slot_is_freed(quiet, fresh):
    p1 = enter(fresh, quiet)
    p2 = enter(fresh, quiet)
    p3 = enter(fresh, quiet)
    p1.phase, p1.phase_weeks_left = "NDA", 1
    clinical.step(fresh, quiet)
    assert p2.stage == CLINICAL and p3.stage == QUEUED
    assert p2.phase_weeks_left == clinical.phase_plan(p2, "I", quiet)[0]
    assert clinical.operations(fresh, quiet)["used"] == 1


def test_upgrade_and_termination_promote_waiting_projects(quiet, fresh):
    p1, p2, p3 = [enter(fresh, quiet) for _ in range(3)]
    A.build_facility(fresh, quiet)
    assert p2.stage == CLINICAL and p3.stage == QUEUED
    p1.stage = PHASE_REVIEW
    d = D.add(fresh, D.PHASE_RESULT, p1.id, passed=True, next="II")
    A.resolve_phase(fresh, quiet, decision_id=d.id, choice="terminate")
    assert p3.stage == CLINICAL
    assert clinical.operations(fresh, quiet)["used"] == 2


def test_contract_clinical_costs_more_without_using_internal_slots(quiet, fresh):
    internal = enter(fresh, quiet)
    external = enter(fresh, quiet, "contract")
    assert external.stage == CLINICAL
    assert clinical.operations(fresh, quiet)["used"] == 1
    assert clinical.phase_plan(external, "III", quiet)[1] == pytest.approx(
        1.3 * clinical.phase_plan(internal, "III", quiet)[1]
    )
    wait = enter(fresh, quiet)
    A.outsource_clinical(fresh, quiet, project_id=wait.id)
    assert wait.stage == CLINICAL and wait.clinical_mode == "contract"
    before = to_json(fresh)
    with pytest.raises(A.ActionError):
        A.outsource_clinical(fresh, quiet, project_id=wait.id)
    assert to_json(fresh) == before


def test_cancelling_queue_is_possible_without_blocking_others(quiet, fresh):
    p1, p2, p3 = [enter(fresh, quiet) for _ in range(3)]
    A.cancel_project(fresh, quiet, project_id=p2.id)
    assert clinical.operations(fresh, quiet)["queue"] == [p3.id]
    assert p1.stage == CLINICAL and not fresh.pending


def test_traits_change_milestone_tradeoffs_and_do_not_change_profession(quiet, fresh):
    p, _ = node(fresh, quiet)
    t = fresh.teams[1]
    t.lead.trait = "iterative"
    quick = research.milestone_plan(fresh, p, t, "boost", quiet)
    t.lead.trait = "optimizer"
    deep = research.milestone_plan(fresh, p, t, "boost", quiet)
    assert deep["bonus"] > quick["bonus"] and deep["weeks"] > quick["weeks"]
    assert deep["cost"] > quick["cost"] and t.lead.specialty == "chem"


def test_fast_choice_gives_up_bonus_without_using_polish_allowance(quiet, fresh):
    p, d = node(fresh, quiet)
    old_stats, old_weeks, old_cash = dict(p.stats), p.rd_weeks, fresh.cash
    A.choose_milestone_team(fresh, quiet, decision_id=d.id, team_id=2, plan="fast")
    assert p.stats == old_stats and p.rd_weeks < old_weeks and fresh.cash == old_cash
    assert research.extensions_used(p, quiet) == 0
    assert p.milestones_done == 2


def test_no_cash_still_allows_free_fast_choice(quiet, fresh):
    p, d = node(fresh, quiet)
    fresh.cash = -10
    A.choose_milestone_team(fresh, quiet, decision_id=d.id, team_id=2, plan="fast")
    assert fresh.cash == -10 and not fresh.pending


def test_invalid_or_unfunded_choice_is_atomic(quiet, fresh):
    p, d = node(fresh, quiet)
    before = to_json(fresh)
    with pytest.raises(A.ActionError, match="隐患"):
        A.choose_milestone_team(fresh, quiet, decision_id=d.id, team_id=1, plan="validate")
    assert to_json(fresh) == before
    fresh.cash = 0
    before = to_json(fresh)
    with pytest.raises(A.ActionError, match="现金"):
        A.choose_milestone_team(fresh, quiet, decision_id=d.id, team_id=1, plan="boost")
    assert to_json(fresh) == before
    with pytest.raises(A.ActionError, match="方案"):
        A.choose_milestone_team(fresh, quiet, decision_id=d.id, team_id=1, plan="routine")
    assert to_json(fresh) == before


def test_serious_hazards_need_validation_and_matching_expertise(quiet, fresh):
    p, d = node(fresh, quiet)
    p.hazards = [Hazard(id=fresh.new_id(), stat="safety", severity=2, text="严重风险"),
                 Hazard(id=fresh.new_id(), stat="safety", severity=1, text="轻微风险")]
    draws = random.Random(1)
    for _ in range(100):
        research._clear_hazards(fresh, p, fresh.teams, draws, quiet)
    assert len(p.hazards) == 1 and p.hazards[0].severity == 2
    assert research.milestone_plan(fresh, p, fresh.teams[0], "validate", quiet)["problem"]
    fresh.teams[0].lead.tox = 40
    old = dict(p.stats)
    A.choose_milestone_team(fresh, quiet, decision_id=d.id, team_id=1, plan="validate")
    assert not p.hazards and p.stats == old


def test_final_validation_has_time_cost_without_point_farming(quiet, fresh):
    p, d = ready(fresh, quiet, [1, 2])
    p.hazards = [Hazard(id=fresh.new_id(), stat="safety", severity=2, text="严重风险")]
    old = dict(p.stats)
    A.resolve_rd_end(fresh, quiet, decision_id=d.id, choice="validate")
    assert p.validation_weeks_left == 2 and not fresh.pending and p.stage != RD_REVIEW
    advance(fresh, quiet, 2)
    assert p.stage == RD_REVIEW and not p.hazards and p.stats == old
    assert research.extensions_used(p, quiet) == 0
    assert p.validation_count == 1


def test_v1_save_migrates_forward_and_current_version_is_marked(fresh):
    import json
    data = json.loads(to_json(fresh))
    data["version"] = 1
    for team in data["teams"]:
        team["lead"].pop("trait")
    loaded = from_json(json.dumps(data))
    assert loaded.version == 3 and all(t.lead.trait for t in loaded.teams)
    assert loaded.cash == fresh.cash and loaded.week == fresh.week


def test_old_active_project_keeps_milestone_dates_after_plan_choice(quiet, fresh):
    p, d = node(fresh, quiet)
    p.base_rd_weeks = 0  # v1 saves have no frozen base duration
    expected = research.milestone_week(p, 2, quiet)
    A.choose_milestone_team(fresh, quiet, decision_id=d.id, team_id=2, plan="boost")
    assert research.milestone_week(p, 2, quiet) == expected


def test_failure_screen_names_actual_unmet_requirement(quiet, fresh):
    p = enter(fresh, quiet)
    p.phase, p.phase_weeks_left = "III", 1
    p.stats["efficacy"] = 0
    clinical.step(fresh, quiet)
    decision = snapshot(fresh, quiet)["pending"][0]
    assert any("疗效" in line and "≥6" in line for line in decision["failure_reasons"])
