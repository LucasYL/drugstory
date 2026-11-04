"""长局试玩发现的属性膨胀、预算漏项和已揭晓风险的回归检查。"""

import pytest

from drugstory.content import STATS
from drugstory.engine import actions as A
from drugstory.engine.game import new_game
from drugstory.engine.state import PHASE_REVIEW, Drug, Hazard, PhaseResult, Project
from drugstory.engine.systems.research import quality_gain
from drugstory.ui.web_view import forecasts, snapshot


def test_quality_keeps_early_progress_but_diminishes_at_high_values(content):
    target = content.targets["egfr"]
    base = content.balance.scoring.base_standard * target.difficulty
    assert quality_gain(0, 100, target, content) == pytest.approx(100)
    assert 0 < quality_gain(base, 100, target, content) < 100
    assert quality_gain(base + 80, 100, target, content) < quality_gain(base, 100, target, content)
    assert base + quality_gain(base, 10_000, target, content) == pytest.approx(
        base * content.balance.research.quality_ceiling
    )
    assert quality_gain(1063, 100, target, content) == 0  # 不清零、不下调旧属性


def test_quality_does_not_depend_on_team_or_week_order(content):
    target = content.targets["egfr"]
    start = 310
    together = start + quality_gain(start, 120, target, content)
    split = start
    for effort in (10, 70, 40):
        split += quality_gain(split, effort, target, content)
    assert split == pytest.approx(together)


def test_budget_accounts_for_payroll_and_other_commitments(content):
    s = new_game(42, content)
    A.start_project(s, content, target="egfr", modality="small_molecule", team_ids=[1])
    v = snapshot(s, content)
    e = v["estimates"]["pd1|mab"]
    assert e["operating_reserve"] == pytest.approx(
        (e["rd_weeks"] + e["clinical_weeks"]) * v["monthly_overhead"] / 4
    )
    assert e["cash_after_reserve"] == pytest.approx(
        s.cash - v["committed"] - e["rd_cost"] - e["clinical_cost"] - e["operating_reserve"]
    )
    s.cash = 1000
    assert snapshot(s, content)["estimates"]["pd1|mab"]["cash_after_reserve"] < 0


def test_only_active_drugs_are_counted_for_competition(content, fresh):
    for i, active in enumerate((True, False)):
        fresh.drugs.append(Drug(id=100+i, project_id=0, name=f"药{i}", target="egfr", modality="small_molecule",
                                composite=80, peak=100, margin=.6, launched_week=0, active=active))
    v = snapshot(fresh, content)
    assert v["estimates"]["egfr|small_molecule"]["same_target_drugs"] == ["药0"]
    assert v["estimates"]["pd1|mab"]["same_target_drugs"] == []


def test_revealed_hazard_does_not_warn_again_about_future_trials(content, fresh):
    p = Project(id=100, target="egfr", modality="small_molecule", stage=PHASE_REVIEW, team_ids=[],
                rd_weeks=27, phase="I", stats={k: 500 for k in STATS},
                hazards=[Hazard(id=101, stat="safety", severity=1, text="已揭晓风险", phase="I")],
                results=[PhaseResult(phase="I", scores={"safety": 9, "druggability": 10}, passed=True,
                                     text="通过", hazard_texts=["I 期安全性扣 1 分"])])
    fresh.projects.append(p)
    assert all(f["margin_ok"] for f in forecasts(fresh, p, content))
    v = snapshot(fresh, content)["projects"][0]
    assert not v["hazards"]
    assert v["results"][0]["hazard_texts"]  # 历史风险记录仍可查看
    p.hazards.append(Hazard(id=102, stat="safety", severity=1, text="尚未揭晓风险", phase="III"))
    assert not any(f["margin_ok"] for f in forecasts(fresh, p, content))
    assert "phase" not in snapshot(fresh, content)["projects"][0]["hazards"][0]
