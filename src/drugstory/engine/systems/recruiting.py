"""招聘负责人：发起招聘，2 周后出候选人（design/game-design.md 5.4 节）。"""

from __future__ import annotations

import random

from drugstory.content import ATTRS, Content
from drugstory.engine import decisions, rng
from drugstory.engine.book import say
from drugstory.engine.state import GameState, Lead


def step(state: GameState, content: Content) -> None:
    recruitment = state.recruitment
    if recruitment is None or recruitment.candidates or state.week + 1 < recruitment.ready_week:
        return
    random_ = rng.stream(state, "recruiting")
    taken = {t.lead.name for t in state.teams}
    for _ in range(content.balance.recruiting.candidates):
        lead = generate(state, random_, recruitment.channel, recruitment.specialty, taken, content)
        taken.add(lead.name)
        recruitment.candidates.append(lead)
    decisions.add(state, decisions.CANDIDATES)
    say(state, f"{content.channel(recruitment.channel).name}招聘出结果了：{len(recruitment.candidates)} 位候选人")


def generate(
    state: GameState, random_: random.Random, channel: str, specialty: str, taken: set[str], content: Content
) -> Lead:
    ch = content.channel(channel)
    cap = content.balance.team.max_attr
    bonus = int(state.reputation / content.balance.recruiting.reputation_divisor)
    main = min(cap, random_.randint(*ch.specialty) + bonus)
    attrs = {a: min(main - 1, random_.randint(*ch.other)) for a in ATTRS}
    attrs[specialty] = main
    return Lead(name=_unique_name(random_, taken, content), leadership=random_.randint(*ch.leadership), **attrs)


def _unique_name(random_: random.Random, taken: set[str], content: Content) -> str:
    people = content.texts.people
    name = ""
    for _ in range(200):
        name = random_.choice(people.surnames) + random_.choice(people.given)
        if name not in taken:
            return name
    return f"{name}{len(taken)}"
