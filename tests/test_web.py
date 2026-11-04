"""网页适配层的持久化、并发保护、真实 HTTP 和面向玩家的预估。"""

import json
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from drugstory.engine import actions as A
from drugstory.engine.game import new_game
from drugstory.engine.save import load, to_json
from drugstory.engine.state import NAMING, Decision, Hazard, PhaseResult, Project
from drugstory.ui import web_server
from drugstory.ui.web_server import Conflict, GameSession, create_server
from drugstory.ui.web_view import forecasts, snapshot


@pytest.fixture
def session(tmp_path):
    return GameSession(tmp_path / "web.json", seed=42)


def command(session, name, **args):
    return session.execute({"revision": session.revision, "name": name, "args": args})


def test_actions_survive_restart_and_continue_deterministically(session):
    command(session, "start_project", target="egfr", modality="small_molecule", team_ids=[1, 2])
    command(session, "advance", weeks=4)
    restored = GameSession(session.path)
    assert to_json(restored.state) == to_json(session.state)
    command(session, "advance", weeks=4)
    command(restored, "advance", weeks=4)
    assert to_json(restored.state) == to_json(session.state)
    command(session, "advance", weeks=4)
    command(restored, "advance", weeks=4)
    assert to_json(restored.state) == to_json(session.state)
    assert session.state.pending[0].kind == "milestone"


def test_stale_click_cannot_advance_twice(session):
    view = session.view()
    request = {"name": "advance", "args": {"weeks": 1}, "revision": view["revision"]}
    session.execute(request)
    with pytest.raises(Conflict):
        session.execute(request)
    assert session.state.week == 1
    assert load(session.path).week == 1


@pytest.mark.parametrize("name,args", [
    ("add_members", {"team_id": 1, "count": -1}),
    ("add_members", {"team_id": 1, "count": True}),
    ("add_members", {"team_id": 1, "count": 1000}),
    ("start_project", {"target": "egfr", "modality": "small_molecule", "team_ids": [1, "2"]}),
    ("advance", {"weeks": 100000}),
    ("not_an_action", {}),
])
def test_bad_requests_leave_state_and_disk_unchanged(session, name, args):
    command(session, "save")
    before = to_json(session.state)
    revision = session.revision
    with pytest.raises((A.ActionError, ValueError)):
        command(session, name, **args)
    assert to_json(session.state) == before
    assert session.path.read_text() == before
    assert session.revision == revision


def test_failed_storage_does_not_publish_move_or_consume_randomness(session, monkeypatch):
    command(session, "save")
    before = to_json(session.state)

    def fail(*args):
        raise OSError("disk full")

    monkeypatch.setattr(web_server, "atomic_write", fail)
    with pytest.raises(OSError):
        command(session, "advance", weeks=4)
    assert to_json(session.state) == before
    assert session.path.read_text() == before
    assert session.revision == 1


def test_new_company_preserves_previous_game(session):
    command(session, "advance", weeks=4)
    before = to_json(session.state)
    command(session, "new_game", seed=8)
    backups = list(session.path.parent.glob("web-before-new-*.json"))
    assert len(backups) == 1 and backups[0].read_text() == before
    assert load(session.path).seed == 8
    assert session.state.week == 0


def test_pending_decision_blocks_time_and_future_decisions(session):
    command(session, "start_project", target="egfr", modality="small_molecule", team_ids=[1, 2])
    command(session, "advance", weeks=48)
    before = to_json(session.state)
    with pytest.raises(ValueError, match="待决定"):
        command(session, "advance", weeks=4)
    with pytest.raises(Conflict):
        command(session, "choose_milestone_team", decision_id=999, team_id=1)
    assert to_json(session.state) == before
    command(session, "choose_milestone_team", decision_id=session.state.pending[0].id, team_id=1)
    assert not session.state.pending


def test_forecast_accounts_for_year_in_which_trial_finishes(content):
    s = new_game(42, content)
    s.week = 47
    p = Project(id=100, target="egfr", modality="small_molecule", stage="rd_review", team_ids=[], rd_weeks=27,
                rd_done=27, stats={k: 300.0 for k in ("efficacy", "druggability", "safety", "manufacturability")})
    forecast = forecasts(s, p, content)[0]
    assert "第 2 年" in forecast["finish"]
    # 跨年仍显示实际完成日期，但门槛不再上涨。
    assert forecast["scores"]["safety"] == 8


def test_view_preserves_unknown_combos_and_hides_hazard_assignment(session):
    command(session, "start_project", target="egfr", modality="small_molecule", team_ids=[1, 2])
    p = session.state.projects[0]
    p.hazards = [Hazard(id=999, stat="safety", severity=2, text="肝毒性", phase="III")]
    view = session.view()
    assert view["estimates"]["egfr|small_molecule"]["known_tier"] == "没做过"
    assert "phase" not in view["projects"][0]["hazards"][0]


def test_first_approval_achievement_is_immediate(content):
    s = new_game(42, content)
    p = Project(id=s.new_id(), target="egfr", modality="small_molecule", stage=NAMING, team_ids=[], rd_weeks=27,
                composite=79, results=[PhaseResult("NDA", {"manufacturability": 5}, True, "审评通过")])
    s.projects.append(p)
    d = Decision(s.new_id(), "approval", p.id, {"suggested": "试验替尼"})
    s.pending.append(d)
    A.name_drug(s, content, decision_id=d.id, name="初晴替尼")
    assert "first_approval" in s.achievements
    assert s.week == 0
    view = snapshot(s, content)
    assert next(a for a in view["achievements"] if a["key"] == "first_approval")["earned"]


@pytest.fixture
def http_game(session):
    server = create_server(session, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", session
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_http_actions_export_and_static_assets(http_game):
    url, session = http_game
    with urlopen(url + "/api/state") as response:
        view = json.load(response)
    payload = json.dumps({"name": "advance", "args": {"weeks": 4}, "revision": view["revision"]}).encode()
    request = Request(url + "/api/action", data=payload, headers={
        "Content-Type": "application/json", "X-Game-Token": view["token"], "Origin": url,
    })
    with urlopen(request) as response:
        result = json.load(response)
    assert result["week"] == 4
    with urlopen(url + "/api/save") as response:
        assert "attachment" in response.headers["Content-Disposition"]
        assert json.load(response)["week"] == 4
    for asset in ("/", "/app.js", "/style.css"):
        with urlopen(url + asset) as response:
            assert response.status == 200 and len(response.read()) > 100
    assert load(session.path).week == 4


@pytest.mark.parametrize("headers", [
    {}, {"Origin": "https://other.example"}, {"Host": "other.example"},
])
def test_foreign_or_untrusted_http_requests_cannot_write(http_game, headers):
    url, session = http_game
    security_headers = {"Content-Type": "application/json"}
    if headers:
        security_headers["X-Game-Token"] = session.token
    request = Request(url + "/api/action", data=b'{"name":"advance","args":{"weeks":4},"revision":0}',
                      headers={**security_headers, **headers})
    with pytest.raises(HTTPError) as error:
        urlopen(request)
    assert error.value.code == 403
    assert session.state.week == 0


def test_all_web_mutations_use_engine_and_data_remains_serializable(session):
    command(session, "start_recruitment", channel="conference", specialty="tox")
    command(session, "advance", weeks=4)
    d = session.state.pending[0]
    command(session, "hire_candidate", decision_id=d.id, index=0)
    team = session.state.teams[-1]
    view = command(session, "add_members", team_id=team.id, count=3)
    assert view["teams"][-1]["members"] == 3
    assert [x.name for x in session.state.action_log] == ["start_recruitment", "hire_candidate", "add_members"]
    assert isinstance(json.dumps(view, ensure_ascii=False), str)
    assert Path(session.path).is_file()
