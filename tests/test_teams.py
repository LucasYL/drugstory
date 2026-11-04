import pytest

from drugstory.engine.state import Lead, Team
from drugstory.engine.systems.teams import (
    exp_to_next,
    gain_exp,
    lead_salary,
    size_factor,
    team_salary,
    training_cost,
    weekly_output,
)


def team(members=0, leadership=4, **attrs):
    values = {"bio": 10, "chem": 10, "tox": 10, "proc": 10, **attrs}
    return Team(id=1, lead=Lead(name="测试", leadership=leadership, **values), members=members)


@pytest.mark.parametrize(
    ("members", "leadership", "expected"),
    [
        (0, 4, 1.0),
        (4, 6, 1 + 0.7 * 4**0.5),  # 都在带队能力以内
        (12, 6, 1 + 0.7 * 9**0.5),  # 超出的 6 个人只算 3 个
    ],
)
def test_size_factor(content, members, leadership, expected):
    assert size_factor(team(members, leadership), content) == pytest.approx(expected)


def test_weekly_output_uses_the_matching_attribute(content):
    t = team(members=4, leadership=6, chem=60)
    assert weekly_output(t, "druggability", content) == pytest.approx(60 * (1 + 0.7 * 2) / 40)
    assert weekly_output(t, "efficacy", content) == pytest.approx(10 * (1 + 0.7 * 2) / 40)


def test_specialty_and_salary(content):
    t = team(members=3, chem=60, tox=60)
    assert t.lead.specialty == "chem"  # 一样高时按 生物、化学、毒理、工艺 的顺序
    assert lead_salary(t.lead, content) == pytest.approx(2 + 60 / 10)
    assert team_salary(t, content) == pytest.approx(8 + 3 * 1.5)


def test_level_up_raises_attributes_and_leadership(content, fresh):
    t = team(bio=50, leadership=4)
    gain_exp(fresh, t, content, exp_to_next(t.lead, content))  # 1 → 2 级
    assert (t.lead.level, t.lead.bio, t.lead.chem, t.lead.leadership) == (2, 53, 11, 4)
    gain_exp(fresh, t, content, exp_to_next(t.lead, content))  # 2 → 3 级：每升两级带队能力 +1
    assert (t.lead.level, t.lead.bio, t.lead.leadership) == (3, 56, 5)
    assert t.lead.exp == 0


def test_level_is_capped(content, fresh):
    t = team(bio=50)
    gain_exp(fresh, t, content, 100_000)
    assert t.lead.level == content.balance.growth.max_level
    assert t.lead.bio <= content.balance.team.max_attr


def test_training_cost_grows_with_the_attribute(content):
    t = team(tox=50)
    assert training_cost(t.lead, "tox", content) == (pytest.approx(20 + 0.6 * 50), 10 + 50 // 5)
