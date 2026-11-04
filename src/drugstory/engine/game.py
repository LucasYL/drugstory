"""开局（design/game-design.md 第 12 节）。"""

from __future__ import annotations

from drugstory.content import Content, default_content
from drugstory.engine.book import say
from drugstory.engine.state import GameState, Lead, Team, YearStats
from drugstory.engine.systems.contracts import refresh_offers
from drugstory.engine.systems.world import ensure


def new_game(seed: int, content: Content | None = None, scenario: str = "independent") -> GameState:
    content = content or default_content()
    start = content.balance.start
    if not isinstance(scenario, str) or scenario not in content.balance.scenarios:
        raise ValueError("不认识的开局路线")
    opening = content.balance.scenarios[scenario]
    cash = start.cash if scenario == "independent" else opening.cash
    state = GameState(seed=seed, week=0, cash=cash, data=opening.data, reputation=0.0,
                      facility=start.facility, scenario=scenario)
    state.years.append(YearStats(year=1))
    state.unlocked_targets = list(start.targets)
    state.unlocked_modalities = list(dict.fromkeys([*start.modalities, *opening.extra_modalities]))
    for t in start.teams:
        lead = Lead(name=t.name, bio=t.bio, chem=t.chem, tox=t.tox, proc=t.proc, leadership=t.leadership)
        state.teams.append(Team(id=state.new_id(), lead=lead, members=t.members))
    refresh_offers(state, content)
    ensure(state, content)
    names = content.texts.names.teams
    teams = "、".join(f"{names[t.lead.specialty]}（{t.lead.name}）" for t in state.teams)
    say(state, f"公司成立了！你有{teams}，还有 ¥{cash:,} 万启动资金")
    return state
