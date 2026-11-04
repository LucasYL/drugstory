"""外包：每月刷新外包单，团队做完拿钱（design/game-design.md 第 10 节）。"""

from __future__ import annotations

from drugstory.content import Content, Contract
from drugstory.engine import rng
from drugstory.engine.book import earn, round_half_up, say
from drugstory.engine.state import IDLE, ContractOffer, GameState, Team
from drugstory.engine.systems.teams import gain_exp, size_factor


def refresh_offers(state: GameState, content: Content) -> None:
    random_ = rng.stream(state, "contracts")
    kinds = list(content.contracts)
    count = content.balance.contracts.offers_per_month
    state.offers = [ContractOffer(id=state.new_id(), kind=random_.choice(kinds)) for _ in range(count)]


def duration(team: Team, contract: Contract, content: Content) -> int:
    c = content.balance.contracts
    return max(c.min_weeks, round_half_up(contract.weeks * c.duration_factor / size_factor(team, content)))


def reward(team: Team, contract: Contract, content: Content) -> int:
    over = max(0, team.lead.attr(contract.attr) - contract.requirement)
    return round_half_up(contract.reward * (1 + content.balance.contracts.bonus_per_10 * (over // 10)))


def step(state: GameState, content: Content) -> None:
    for contract in list(state.contracts):
        team = state.team(contract.team_id)
        gain_exp(state, team, content)
        contract.weeks_left -= 1
        if contract.weeks_left > 0:
            continue
        earn(state, contract.reward, "contracts")
        state.data += contract.data
        team.task, team.task_id = IDLE, 0
        state.contracts.remove(contract)
        name = content.contracts[contract.kind].name
        say(state, f"{team.lead.name}的团队做完外包「{name}」：+¥{contract.reward:,} 万，+{contract.data} 研究数据")
