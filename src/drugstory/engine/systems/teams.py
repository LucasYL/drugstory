"""团队：周产出、工资、经验与升级（design/game-design.md 5.1、5.2、5.5 节）。"""

from __future__ import annotations

from drugstory.content import ATTR_OF_STAT, ATTRS, Content
from drugstory.engine.book import say
from drugstory.engine.state import GameState, Lead, Team


def size_factor(team: Team, content: Content) -> float:
    """规模系数 = 1 + 0.7 × √有效人数；带队能力以内的成员算 1 个，超出的算半个。"""
    t = content.balance.team
    within = min(team.members, team.lead.leadership)
    beyond = max(0, team.members - team.lead.leadership)
    return 1 + t.member_weight * (within + t.overflow_weight * beyond) ** t.member_exponent


def weekly_output(team: Team, stat: str, content: Content) -> float:
    """这个团队每周给药的某一项属性贡献多少点（还没乘组合系数、熟练度和随机波动）。"""
    return team.lead.attr(ATTR_OF_STAT[stat]) * size_factor(team, content) / content.balance.team.output_divisor


def lead_salary(lead: Lead, content: Content) -> float:
    t = content.balance.team
    return t.lead_salary_base + t.lead_salary_per_point * lead.attr(lead.specialty)


def team_salary(team: Team, content: Content) -> float:
    return lead_salary(team.lead, content) + team.members * content.balance.team.member_salary


def payroll(state: GameState, content: Content) -> float:
    return sum(team_salary(t, content) for t in state.teams)


def capacity(state: GameState, content: Content) -> int:
    return content.facility(state.facility).capacity


def exp_to_next(lead: Lead, content: Content) -> int:
    return content.balance.growth.exp_per_level * lead.level


def gain_exp(state: GameState, team: Team, content: Content, amount: int = 1) -> None:
    g = content.balance.growth
    lead = team.lead
    if lead.level >= g.max_level:
        return
    lead.exp += amount
    while lead.level < g.max_level and lead.exp >= exp_to_next(lead, content):
        lead.exp -= exp_to_next(lead, content)
        _level_up(state, lead, content)


def _level_up(state: GameState, lead: Lead, content: Content) -> None:
    g = content.balance.growth
    cap = content.balance.team.max_attr
    specialty = lead.specialty
    lead.level += 1
    for a in ATTRS:
        gain = g.level_up_specialty if a == specialty else g.level_up_other
        setattr(lead, a, min(cap, lead.attr(a) + gain))
    if (lead.level - 1) % g.leadership_every_levels == 0:
        lead.leadership = min(content.balance.team.max_leadership, lead.leadership + 1)
    if lead.level == g.max_level:
        lead.exp = 0
    say(state, f"{lead.name}升到 {lead.level} 级")


def training_cost(lead: Lead, attr: str, content: Content) -> tuple[float, int]:
    """培训一次的花费：(钱, 研究数据)。"""
    g = content.balance.growth
    value = lead.attr(attr)
    money = g.training_base_cost + g.training_cost_per_point * value
    return money, g.training_base_data + value // g.training_data_divisor
