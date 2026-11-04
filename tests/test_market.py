import pytest

from drugstory.engine.game import new_game
from drugstory.engine.loop import advance
from drugstory.engine.state import Drug, PhaseResult, Project
from drugstory.engine.systems import market


def approved_project(target="tnf", modality="mab", composite=80.0, manufacturability=6):
    p = Project(id=1, target=target, modality=modality, stage="naming", team_ids=[], rd_weeks=1, composite=composite)
    p.results = [
        PhaseResult(
            phase="NDA",
            scores={"efficacy": 8, "druggability": 8, "safety": 8, "manufacturability": manufacturability},
            passed=True,
            text="",
        )
    ]
    return p


def test_curve_ramps_holds_then_declines(quiet):
    assert market.curve(0, quiet) == pytest.approx(1 / 24)
    assert market.curve(23, quiet) == 1.0
    assert market.curve(24 + 95, quiet) == 1.0
    assert market.curve(24 + 96, quiet) == pytest.approx(0.98)
    assert market.curve(24 + 96 + 9, quiet) == pytest.approx(0.98**10)


def test_peak_and_margin(quiet):
    s = new_game(1, quiet)
    s.reputation = 20.0
    p = approved_project(composite=80.0, manufacturability=6)
    assert market.peak_sales(s, p, quiet) == pytest.approx(200 * 0.8**2 * (1 + 20 / 200))
    assert market.margin(p, quiet) == pytest.approx(0.40 + 0.045 * 6)
    # 长期用药的病用口服药，卖得更好
    oral = approved_project(target="jak", modality="small_molecule", composite=80.0)
    assert market.peak_sales(s, oral, quiet) == pytest.approx(120 * 0.8**2 * 1.1 * 1.2)


def test_launch_sets_reputation_and_hall_of_fame(quiet):
    s = new_game(1, quiet)
    p = approved_project(composite=92.0)
    s.projects.append(p)
    drug = market.launch(s, p, "Testimab", quiet)
    assert drug.hall_of_fame
    assert s.reputation == pytest.approx((92 - 50) / 5)
    assert s.modality_proficiency["mab"] == 1


def test_drugs_on_the_same_target_share_the_market(quiet):
    s = new_game(1, quiet)
    for i in (1, 2):
        s.drugs.append(
            Drug(
                id=i,
                project_id=0,
                name=f"D{i}",
                target="tnf",
                modality="mab",
                composite=80,
                peak=100.0,
                margin=0.5,
                launched_week=0,
                weeks_on_market=30,
            )
        )
    income = sum(s.income.values())
    market.step(s, quiet)
    assert sum(s.income.values()) - income == 2 * round(100 * 0.5 / 2)
    assert s.drugs[0].revenue_total == 50


def test_drugs_retire_when_sales_fade(quiet):
    s = new_game(1, quiet)
    weeks = 24 + 96 + 113  # 0.98 ^ 114 < 10%
    s.drugs.append(
        Drug(
            id=1,
            project_id=0,
            name="Old",
            target="tnf",
            modality="mab",
            composite=80,
            peak=100.0,
            margin=0.5,
            launched_week=0,
            weeks_on_market=weeks,
        )
    )
    advance(s, quiet, 1)
    assert not s.drugs[0].active
