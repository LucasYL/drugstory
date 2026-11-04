import pytest

from drugstory.content import default_content, load_content
from drugstory.engine import actions as A
from drugstory.engine import decisions as D
from drugstory.engine.game import new_game
from drugstory.engine.loop import advance
from drugstory.engine.systems.research import best_team


@pytest.fixture(scope="session")
def content():
    return default_content()


@pytest.fixture(scope="session")
def quiet():
    """没有随机波动、没有隐患的内容：结果完全可以手算。"""
    return load_content(
        balance_overrides={
            "research.noise": 0,
            "scoring.noise": 0,
            "research.hazard_rate": {"low": 0, "medium": 0, "high": 0},
        }
    )


def resolve_all(state, content, rd_choice="proceed", phase_choice="continue"):
    """按默认的方式处理掉所有待决定的事。"""
    while state.pending:
        d = state.pending[0]
        if d.kind == D.MILESTONE:
            team = best_team(state, state.project(d.project_id), d.data["stat"], content)
            A.choose_milestone_team(state, content, decision_id=d.id, team_id=team.id)
        elif d.kind == D.RD_END:
            A.resolve_rd_end(state, content, decision_id=d.id, choice=rd_choice)
        elif d.kind == D.PHASE_RESULT:
            A.resolve_phase(state, content, decision_id=d.id, choice=phase_choice if d.data["passed"] else "ack")
        elif d.kind == D.APPROVAL:
            A.name_drug(state, content, decision_id=d.id, name=d.data["suggested"])
        elif d.kind == D.CANDIDATES:
            A.hire_candidate(state, content, decision_id=d.id, index=-1)
        else:
            A.acknowledge(state, content, decision_id=d.id)


def run_until(state, content, predicate, max_weeks=2000, **resolve):
    """一周一周推进并按默认方式处理决定，直到 predicate(state) 为真。"""
    for _ in range(max_weeks):
        if predicate(state):
            return state
        advance(state, content, 1)
        resolve_all(state, content, **resolve)
    raise AssertionError("推进了很久也没等到想要的状态")


@pytest.fixture
def fresh(content):
    return new_game(1, content)
