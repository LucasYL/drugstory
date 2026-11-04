"""开局（design/game-design.md 第 12 节）。"""

from __future__ import annotations

from drugstory.content import Content, default_content
from drugstory.engine.book import say
from drugstory.engine.state import GameState, Lead, Team, YearStats
from drugstory.engine.systems.contracts import refresh_offers


def new_game(seed: int, content: Content | None = None) -> GameState:
    content = content or default_content()
    start = content.balance.start
    state = GameState(seed=seed, week=0, cash=start.cash, data=0, reputation=0.0, facility=start.facility)
    state.years.append(YearStats(year=1))
    state.unlocked_targets = list(start.targets)
    state.unlocked_modalities = list(start.modalities)
    for t in start.teams:
        lead = Lead(name=t.name, bio=t.bio, chem=t.chem, tox=t.tox, proc=t.proc, leadership=t.leadership)
        state.teams.append(Team(id=state.new_id(), lead=lead, members=t.members))
    refresh_offers(state, content)
    names = content.texts.names.teams
    teams = "、".join(f"{names[t.lead.specialty]}（{t.lead.name}）" for t in state.teams)
    say(state, f"公司成立了！你有{teams}，还有 ¥{start.cash:,} 万启动资金")
    return state
