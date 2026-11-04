"""Regression cases for the year-19 dead end and the first-drug learning loop."""

import json

import pytest

from drugstory.content import ATTRS, STATS
from drugstory.engine import actions as A
from drugstory.engine.game import new_game
from drugstory.engine.loop import advance
from drugstory.engine.save import from_json, to_json
from drugstory.engine.state import RD_REVIEW, Project
from drugstory.engine.systems.research import best_team, extensions_used
from drugstory.engine.systems.teams import gain_exp, training_cap
from drugstory.ui.web_view import forecasts, snapshot


@pytest.mark.parametrize("seed", [0, 1, 5, 19, 42, 101, 2026])
def test_first_drug_can_launch_with_normal_funding(content, seed):
    s = new_game(seed, content)
    for t in s.teams:
        A.add_members(s, content, team_id=t.id, count=2)
    A.start_recruitment(s, content, channel="conference", specialty="tox")
    advance(s, content, 2)
    candidates = s.recruitment.candidates
    index = max(range(len(candidates)), key=lambda i: candidates[i].tox)
    A.hire_candidate(s, content, decision_id=s.pending[0].id, index=index, members=3)
    pid = A.start_project(s, content, target="egfr", modality="small_molecule", team_ids=[t.id for t in s.teams])
    p = s.project(pid)
    for _ in range(200):
        if not p.active or s.game_over:
            break
        if not s.pending:
            advance(s, content, 1)
            continue
        d = s.pending[0]
        if d.kind == "milestone":
            A.choose_milestone_team(s, content, decision_id=d.id, team_id=best_team(s, p, d.data["stat"], content).id)
        elif d.kind == "rd_end":
            ready = all(f["margin_ok"] for f in forecasts(s, p, content))
            capped = extensions_used(p, content) >= content.balance.research.max_extensions
            choice = "proceed" if ready or capped else "extend"
            if p.hazards and p.validation_count < content.balance.research.max_validations:
                choice = "validate"
            A.resolve_rd_end(s, content, decision_id=d.id, choice=choice)
        elif d.kind == "phase_result":
            A.resolve_phase(s, content, decision_id=d.id, choice="continue" if d.data["passed"] else "ack")
        elif d.kind == "approval":
            A.name_drug(s, content, decision_id=d.id, name="初晴替尼")
        else:
            A.acknowledge(s, content, decision_id=d.id)
    assert p.stage == "approved"
    assert s.cash > 1000
    assert s.week <= 120


def test_year19_legacy_drug_is_not_trapped_by_moving_standards(content):
    s = new_game(42, content)
    s.week = 871
    p = Project(id=s.new_id(), target="pd1", modality="small_molecule", stage=RD_REVIEW,
                team_ids=[t.id for t in s.teams], rd_weeks=258, rd_done=258,
                stats=dict(zip(STATS, [1063, 969, 1054, 839], strict=True)))
    s.projects.append(p)
    from drugstory.engine import decisions
    decisions.add(s, decisions.RD_END, p.id)
    assert all(f["margin_ok"] for f in forecasts(s, p, content))
    view = snapshot(s, content)["projects"][0]
    assert view["polish"]["remaining"] == 0
    before = to_json(s)
    with pytest.raises(A.ActionError, match="上限"):
        A.resolve_rd_end(s, content, decision_id=s.pending[0].id, choice="extend")
    assert to_json(s) == before
    A.resolve_rd_end(s, content, decision_id=s.pending[0].id, choice="proceed")
    assert p.stage == "clinical"


def test_bad_route_is_explained_before_spending(content, fresh):
    route = snapshot(fresh, content)["estimates"]["pd1|small_molecule"]["route"]
    assert not route["allowed"] and "口袋" in route["reason"]
    before = to_json(fresh)
    with pytest.raises(A.ActionError, match="不可立项"):
        A.start_project(fresh, content, target="pd1", modality="small_molecule", team_ids=[1, 2])
    assert to_json(fresh) == before


def test_profession_is_fixed_and_cross_training_is_limited(content, fresh):
    t = fresh.teams[0]
    primary, secondary = t.lead.specialty, t.lead.secondary
    other = next(a for a in ATTRS if a not in (primary, secondary))
    setattr(t.lead, other, 45)
    fresh.data = 1000
    before = to_json(fresh)
    with pytest.raises(A.ActionError, match="培养上限 45"):
        A.train_lead(fresh, content, team_id=t.id, attr=other)
    assert to_json(fresh) == before
    assert training_cap(t.lead, primary, content) == 100
    assert training_cap(t.lead, secondary, content) == 70
    setattr(t.lead, other, 99)  # 老存档超过新上限的属性保留
    gain_exp(fresh, t, content, 1000)
    assert getattr(t.lead, other) == 99 and t.lead.specialty == primary


def test_legacy_save_infers_professions_without_losing_progress(fresh):
    data = json.loads(to_json(fresh))
    for t in data["teams"]:
        t["lead"].pop("profession")
        t["lead"].pop("secondary")
    s = from_json(json.dumps(data))
    assert s.cash == fresh.cash and s.week == fresh.week
    assert [t.lead.specialty for t in s.teams] == ["bio", "chem"]
    assert from_json(to_json(s)) == s


def test_hiring_with_members_checks_full_cost_and_capacity(content, fresh):
    A.start_recruitment(fresh, content, channel="conference", specialty="tox")
    advance(fresh, content, 2)
    before = to_json(fresh)
    with pytest.raises(A.ActionError, match="坐不下"):
        A.hire_candidate(fresh, content, decision_id=fresh.pending[0].id, index=0, members=20)
    assert to_json(fresh) == before
    tid = A.hire_candidate(fresh, content, decision_id=fresh.pending[0].id, index=0, members=3)
    t = fresh.team(tid)
    assert t.members == 3
    view = next(t for t in snapshot(fresh, content)["teams"] if t["id"] == tid)
    assert view["size_factor"] > 2
