"""整局测试：用 bot 跑完整局，检查不变量、确定性、存档和回放。"""

import pytest

from drugstory.engine.game import new_game
from drugstory.engine.save import SaveError, from_json, load, replay, save, to_json
from drugstory.engine.state import ON_CONTRACT, ON_PROJECT, RD_REVIEW, RESEARCH
from drugstory.engine.systems.teams import capacity
from drugstory.sim.bots import STRATEGIES
from drugstory.sim.run import play


def check_invariants(state, content):
    start = content.balance.start.cash
    assert state.cash == start + sum(state.income.values()) - sum(state.expense.values())
    assert state.headcount <= capacity(state, content)
    contracts = {c.id: c for c in state.contracts}
    for team in state.teams:
        assert team.members >= 0
        if team.task == ON_PROJECT:
            project = state.project(team.task_id)
            assert project.stage in (RESEARCH, RD_REVIEW)
            assert team.id in project.team_ids
        elif team.task == ON_CONTRACT:
            assert contracts[team.task_id].team_id == team.id
    for project in state.projects:
        assert len(project.team_ids) <= content.balance.team.max_per_project
        for team_id in project.team_ids:
            team = state.team(team_id)
            assert (team.task, team.task_id) == (ON_PROJECT, project.id)
    for decision in state.pending:
        if decision.project_id:
            state.project(decision.project_id)
    if not state.game_over:  # 破产发生在年底时，不会再开新的一年
        assert len(state.years) == state.week // content.balance.time.weeks_per_year + 1
    assert 0 <= state.reputation <= content.balance.reputation.max


@pytest.mark.parametrize("strategy", list(STRATEGIES))
def test_invariants_hold_for_a_whole_game(content, strategy):
    state = play(11, STRATEGIES[strategy](), content, years=8, on_week=lambda s: check_invariants(s, content))
    assert state.week > 0


def test_a_steady_player_gets_drugs_approved(content):
    state = play(2, STRATEGIES["steady"](), content, years=6)
    assert not state.game_over
    assert state.drugs
    assert "first_approval" in state.achievements


def test_same_seed_same_game(content):
    a = play(5, STRATEGIES["steady"](), content, years=4)
    b = play(5, STRATEGIES["steady"](), content, years=4)
    assert to_json(a) == to_json(b)


def test_different_seeds_differ(content):
    a = play(5, STRATEGIES["steady"](), content, years=3)
    b = play(6, STRATEGIES["steady"](), content, years=3)
    assert to_json(a) != to_json(b)


def test_save_and_load_continue_identically(content, tmp_path):
    bot = STRATEGIES["steady"]()
    state = play(9, bot, content, years=3)
    path = tmp_path / "save.json"
    save(state, path)
    loaded = load(path)
    assert to_json(loaded) == to_json(state)

    from drugstory.engine.loop import advance

    def keep_playing(s):
        for _ in range(48):
            bot.manage(s, content)
            advance(s, content, 1)
            while s.pending:
                bot.resolve(s, content, s.pending[0])

    keep_playing(state)
    keep_playing(loaded)
    assert to_json(loaded) == to_json(state)


def test_replay_reproduces_the_game(content):
    original = play(4, STRATEGIES["steady"](), content, years=4)
    copy = replay(original.seed, original.action_log, content)
    from drugstory.engine.loop import advance

    advance(copy, content, original.week - copy.week)
    assert to_json(copy) == to_json(original)


def test_bad_saves_are_rejected(content):
    good = to_json(new_game(1, content))
    with pytest.raises(SaveError, match="版本"):
        from_json(good.replace('"version":3', '"version":99'))
    with pytest.raises(SaveError, match="存档坏了"):
        from_json("{not json")
