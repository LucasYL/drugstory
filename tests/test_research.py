import math

import pytest

from drugstory.content import STATS
from drugstory.engine import actions as A
from drugstory.engine import decisions as D
from drugstory.engine.game import new_game
from drugstory.engine.loop import advance
from drugstory.engine.state import CLINICAL, ON_PROJECT, RD_REVIEW, RESEARCH, TERMINATED, Hazard
from drugstory.engine.systems.research import milestone_plan, point_multiplier, project_teams
from drugstory.engine.systems.teams import weekly_output


def start(state, content, target="egfr", modality="small_molecule"):
    return state.project(
        A.start_project(state, content, target=target, modality=modality, team_ids=[t.id for t in state.teams])
    )


def test_starting_a_project_takes_the_teams(quiet):
    s = new_game(1, quiet)
    p = start(s, quiet)
    assert p.stage == RESEARCH
    assert p.rd_weeks == round(30 * 0.9)
    assert all(t.task == ON_PROJECT and t.task_id == p.id for t in s.teams)


def test_one_week_of_points_matches_the_formula(quiet):
    s = new_game(1, quiet)
    p = start(s, quiet)
    expected = {
        stat: sum(weekly_output(t, stat, quiet) for t in project_teams(s, p)) * point_multiplier(s, p, quiet)
        for stat in STATS
    }
    cash, data = s.cash, s.data
    advance(s, quiet, 1)
    assert p.stats == pytest.approx(expected)
    assert cash - s.cash == quiet.modalities["small_molecule"].weekly_cost
    assert s.data - data == 2  # 两个团队各 +1


def test_noise_stays_within_twenty_percent(content):
    s = new_game(3, content)
    p = start(s, content)
    expected = sum(weekly_output(t, "efficacy", content) for t in project_teams(s, p)) * point_multiplier(s, p, content)
    advance(s, content, 1)
    assert 0.8 * expected <= p.stats["efficacy"] <= 1.2 * expected


def test_milestones_come_at_twenty_forty_sixty_eighty_percent(quiet):
    s = new_game(1, quiet)
    p = start(s, quiet)
    seen = []
    while p.stage == RESEARCH:
        advance(s, quiet, 1)
        for d in list(s.pending):
            if d.kind == D.RD_END:
                continue
            assert d.kind == D.MILESTONE
            seen.append((p.rd_done, d.data["stat"]))
            team = max(project_teams(s, p), key=lambda t: weekly_output(t, d.data["stat"], quiet))
            bonus = milestone_plan(s, p, team, "boost", quiet)["bonus"]
            before = p.stats[d.data["stat"]]
            A.choose_milestone_team(s, quiet, decision_id=d.id, team_id=team.id)
            assert p.stats[d.data["stat"]] == pytest.approx(before + bonus)
    indices = quiet.balance.research.decision_milestones
    assert seen == [(math.ceil(quiet.balance.research.milestones[i] * p.base_rd_weeks), STATS[i]) for i in indices]
    assert p.milestones_done == 4
    assert p.stage == RD_REVIEW
    assert [d.kind for d in s.pending] == [D.RD_END]


def test_project_pauses_without_teams(quiet):
    s = new_game(1, quiet)
    p = start(s, quiet)
    A.set_project_teams(s, quiet, project_id=p.id, team_ids=[])
    cash = s.cash
    advance(s, quiet, 3)
    assert p.rd_done == 0
    assert s.cash == cash  # 第 3 周还没到月底，也没有研发花费


def finish_research(s, content, p):
    while p.stage == RESEARCH:
        advance(s, content, 1)
        for d in list(s.pending):
            if d.kind == D.MILESTONE:
                A.choose_milestone_team(s, content, decision_id=d.id, team_id=p.team_ids[0])
    return next(d for d in s.pending if d.kind == D.RD_END)


def test_extend_adds_four_weeks(quiet):
    s = new_game(1, quiet)
    p = start(s, quiet)
    d = finish_research(s, quiet, p)
    weeks = p.rd_weeks
    A.resolve_rd_end(s, quiet, decision_id=d.id, choice="extend")
    assert p.stage == RESEARCH and p.rd_weeks == weeks + 4
    advance(s, quiet, 4)
    assert p.stage == RD_REVIEW and s.pending[0].kind == D.RD_END


def test_proceed_frees_teams_records_notebook_and_assigns_hazards(quiet):
    s = new_game(1, quiet)
    p = start(s, quiet)
    d = finish_research(s, quiet, p)
    p.hazards.append(Hazard(id=999, stat="manufacturability", severity=1, text="杂质超标"))
    A.resolve_rd_end(s, quiet, decision_id=d.id, choice="proceed")
    assert p.stage == CLINICAL and p.phase == "I"
    assert all(t.idle for t in s.teams) and p.team_ids == []
    assert s.notebook["egfr|small_molecule"].tier == 2
    assert p.hazards[0].phase == "NDA"  # 可生产性的隐患只会在审评爆雷


def test_terminate_after_research_counts_for_proficiency(quiet):
    s = new_game(1, quiet)
    p = start(s, quiet)
    d = finish_research(s, quiet, p)
    A.resolve_rd_end(s, quiet, decision_id=d.id, choice="terminate")
    assert p.stage == TERMINATED
    assert s.modality_proficiency == {"small_molecule": 1}
    assert s.target_proficiency == {"egfr": 1}


def test_hazards_appear_and_get_cleared(content):
    s = new_game(5, content)
    s.unlocked_targets.append("kras")
    p = start(s, content, "kras", "small_molecule")  # 难度高，隐患多
    spawned = cleared = 0
    while p.stage == RESEARCH:
        before = len(p.hazards)
        advance(s, content, 1)
        for d in list(s.pending):
            if d.kind == D.MILESTONE:
                A.choose_milestone_team(s, content, decision_id=d.id, team_id=p.team_ids[0])
        spawned += any("冒出隐患" in m.text for m in s.messages if m.week == s.week - 1)
        cleared += len(p.hazards) < before
    assert spawned > 0
    assert cleared > 0
    assert all(h.stat in ("safety", "druggability", "manufacturability") for h in p.hazards)
