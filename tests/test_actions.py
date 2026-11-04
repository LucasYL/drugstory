import pytest

from drugstory.engine import actions as A
from drugstory.engine import decisions as D
from drugstory.engine.game import new_game
from drugstory.engine.loop import advance
from drugstory.engine.state import CANCELLED, IDLE, ON_CONTRACT, Lead, Team
from drugstory.engine.systems.contracts import duration
from drugstory.engine.systems.teams import capacity, lead_salary

ActionError = A.ActionError


def ids(state):
    return [t.id for t in state.teams]


def test_actions_are_logged_with_their_week(content, fresh):
    advance(fresh, content, 2)
    A.start_project(fresh, content, target="egfr", modality="small_molecule", team_ids=ids(fresh))
    entry = fresh.action_log[-1]
    assert (entry.week, entry.name) == (2, "start_project")
    assert entry.args == {"target": "egfr", "modality": "small_molecule", "team_ids": ids(fresh)}


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"target": "kras", "modality": "small_molecule"}, "靶点还没解锁"),
        ({"target": "egfr", "modality": "adc"}, "分子类型还没解锁"),
        ({"target": "egfr", "modality": "small_molecule", "team_ids": []}, "至少要配一个团队"),
    ],
)
def test_start_project_checks(content, fresh, kwargs, message):
    kwargs.setdefault("team_ids", ids(fresh))
    with pytest.raises(ActionError, match=message):
        A.start_project(fresh, content, **kwargs)
    assert fresh.action_log == []  # 失败的操作不记日志


def test_busy_teams_and_the_team_limit(content, fresh):
    A.start_project(fresh, content, target="egfr", modality="small_molecule", team_ids=ids(fresh))
    with pytest.raises(ActionError, match="正忙"):
        A.start_project(fresh, content, target="pd1", modality="mab", team_ids=ids(fresh)[:1])
    for i in range(5):
        fresh.teams.append(Team(id=100 + i, lead=Lead(name=f"人{i}", bio=30, chem=30, tox=30, proc=30, leadership=3)))
    with pytest.raises(ActionError, match="最多配 4 个团队"):
        A.start_project(fresh, content, target="pd1", modality="mab", team_ids=[100, 101, 102, 103, 104])


def test_cancel_project_frees_teams(content, fresh):
    pid = A.start_project(fresh, content, target="egfr", modality="small_molecule", team_ids=ids(fresh))
    A.cancel_project(fresh, content, project_id=pid)
    assert fresh.project(pid).stage == CANCELLED
    assert all(t.task == IDLE for t in fresh.teams)
    with pytest.raises(ActionError, match="只能取消研发中的项目"):
        A.cancel_project(fresh, content, project_id=pid)


def test_recruitment_flow(content, fresh):
    cash = fresh.cash
    A.start_recruitment(fresh, content, channel="web", specialty="tox")
    assert fresh.cash == cash - content.channel("web").cost
    with pytest.raises(ActionError, match="已经有一次招聘"):
        A.start_recruitment(fresh, content, channel="web", specialty="tox")
    advance(fresh, content, 5)
    d = fresh.pending[0]
    assert d.kind == D.CANDIDATES and fresh.week == 2
    candidates = fresh.recruitment.candidates
    assert len(candidates) == 3
    assert all(c.specialty == "tox" for c in candidates)
    assert len({c.name for c in candidates} | {t.lead.name for t in fresh.teams}) == 5  # 没有重名
    fee = 3 * lead_salary(candidates[1], content)
    cash = fresh.cash
    team_id = A.hire_candidate(fresh, content, decision_id=d.id, index=1)
    assert fresh.team(team_id).lead is candidates[1]
    assert fresh.cash == cash - round(fee)
    assert fresh.recruitment is None and not fresh.pending


def test_members_respect_capacity(content, fresh):
    room = capacity(fresh, content) - fresh.headcount
    team = fresh.teams[0]
    with pytest.raises(ActionError, match="坐不下"):
        A.add_members(fresh, content, team_id=team.id, count=room + 1)
    A.add_members(fresh, content, team_id=team.id, count=room)
    assert fresh.headcount == capacity(fresh, content)
    A.remove_members(fresh, content, team_id=team.id, count=2)
    assert team.members == 2 + room - 2


def test_fire_lead_removes_the_team_from_its_work(content, fresh):
    pid = A.start_project(fresh, content, target="egfr", modality="small_molecule", team_ids=ids(fresh))
    first = fresh.teams[0]
    A.fire_lead(fresh, content, team_id=first.id)
    assert first not in fresh.teams
    assert fresh.project(pid).team_ids == [fresh.teams[0].id]


def test_training(content, fresh):
    team = fresh.teams[0]
    fresh.data = 100
    A.train_lead(fresh, content, team_id=team.id, attr="tox")
    assert team.lead.tox == 25 + 5
    assert fresh.data == 100 - (10 + 25 // 5)
    fresh.data = 0
    with pytest.raises(ActionError, match="研究数据不够"):
        A.train_lead(fresh, content, team_id=team.id, attr="tox")


def test_contract_flow(content, fresh):
    offer = fresh.offers[0]
    contract = content.contracts[offer.kind]
    team = next((t for t in fresh.teams if t.lead.attr(contract.attr) >= contract.requirement), None)
    if team is None:
        team = fresh.teams[0]
        setattr(team.lead, contract.attr, contract.requirement)
    weeks = duration(team, contract, content)
    cash = fresh.cash
    A.accept_contract(fresh, content, offer_id=offer.id, team_id=team.id)
    assert team.task == ON_CONTRACT and offer not in fresh.offers
    advance(fresh, content, weeks)
    assert team.task == IDLE
    paid = sum(fresh.income.values())
    assert paid >= contract.reward
    assert fresh.cash > cash - 50  # 外包报酬远大于这几周的开销


def test_unlocks(content, fresh):
    with pytest.raises(ActionError, match="需要 60 研究数据"):
        A.unlock_target(fresh, content, key="her2")
    fresh.data = 60
    A.unlock_target(fresh, content, key="her2")
    assert "her2" in fresh.unlocked_targets and fresh.data == 0
    fresh.data = 1000
    with pytest.raises(ActionError, match="需要单抗熟练度 2 级"):
        A.unlock_modality(fresh, content, key="adc")
    fresh.modality_proficiency["mab"] = 2
    A.unlock_modality(fresh, content, key="adc")
    assert "adc" in fresh.unlocked_modalities
    with pytest.raises(ActionError, match="需要场地达到研发中心"):
        A.unlock_modality(fresh, content, key="cart")


def test_build_facility(content, fresh):
    fresh.cash = 100
    with pytest.raises(ActionError, match="现金不够"):
        A.build_facility(fresh, content)
    fresh.cash = 5000
    A.build_facility(fresh, content)
    assert fresh.facility == "center" and fresh.cash == 3000


def test_nothing_works_after_game_over(content):
    s = new_game(1, content)
    s.game_over = True
    with pytest.raises(ActionError, match="游戏已经结束"):
        A.build_facility(s, content)
