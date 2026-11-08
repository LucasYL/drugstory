"""Scene transport: published timing, persistence and shared-rule boundaries."""

import json
import threading
from http.client import HTTPConnection
from pathlib import Path

import jsonschema
import pytest

from drugstory.career import api
from drugstory.career import engine as g
from drugstory.career.content import CLINICAL
from drugstory.career.model import dumps
from drugstory.career.server import GameSession, create_server
from drugstory.career.view import snapshot
from tests.test_career import complete_phase, preclinical_result, ready


def test_public_scene_is_observational_and_has_real_timing():
    s = g.execute(ready(), "run_phase", {"project": "1", "heroes": ["pill"]})
    p = s["projects"][0]
    saved = dumps(s)
    shown = snapshot(s)["projects"][0]["scene"]
    assert shown["total"] == p["execution"]["weeks"]
    assert shown["elapsed"] == 0 and shown["activity"] == "make"
    assert shown["limits"] and all(isinstance(v, int) for v in shown["limits"].values())
    assert dumps(s) == saved
    schema = json.loads((Path(__file__).parents[1] / "design/api/state-v2.schema.json").read_text())
    view = {**snapshot(s), "revision": 0, "token": "test", "saved_at": None}
    jsonschema.validate(api.state(view), schema)
    s = g.execute(s, "advance", {"weeks": 1})
    assert snapshot(s)["projects"][0]["scene"]["elapsed"] == 1


def test_cro_flag_is_current_execution_and_does_not_leak_to_following_phase():
    s = g.execute(preclinical_result(), "continue_project", {"project": "1"})
    s = g.execute(s, "run_phase", {"project": "1", "heroes": [], "mode": "cro"})
    p = snapshot(s)["projects"][0]
    assert p["scene"]["executor"] == "cro" and p["scene"]["activity"] == "test"
    assert p["key"] in CLINICAL
    # Constructed boundary: a formerly outsourced project at review must not animate CRO.
    s["projects"][0]["index"] = 5
    s["projects"][0]["status"] = "result"
    assert snapshot(s)["projects"][0]["scene"]["executor"] == "internal"


def test_one_week_clock_reaches_identical_gameplay_as_manual_time(tmp_path):
    initial = ready()
    initial = g.execute(initial, "run_phase", {"project": "1", "heroes": ["pill"]})
    batch = complete_phase(ready(), ["pill"])
    session = GameSession(tmp_path / "scene.json")
    session.state = initial
    while session.state["projects"][0]["status"] == "running":
        session.execute(
            {"name": "advance", "args": {"weeks": 1}, "revision": session.revision, "request_id": str(session.revision)}
        )
    assert session.state["projects"] == batch["projects"]
    assert session.state["cash"] == pytest.approx(batch["cash"])
    assert GameSession(session.path).state == session.state


def test_scene_assets_same_origin_and_save_roundtrip(tmp_path):
    session = GameSession(tmp_path / "save.json")
    server = create_server(session, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = HTTPConnection("127.0.0.1", server.server_port)
    try:
        for path in (
            "/scene",
            "/scene/",
            "/scene/renderer.js",
            "/scene/world.js",
            "/scene/ui.js",
            "/api-driver.js",
            "/",
        ):
            client.request("GET", path)
            result = client.getresponse()
            assert result.status == 200
            assert "script-src 'unsafe-inline'" not in result.getheader("Content-Security-Policy")
            result.read()
        for path in ("/scene/../../model.py", "/scene/sim.js"):
            client.request("GET", path)
            result = client.getresponse()
            assert result.status == 404
            result.read()
        before = dumps(session.state)
        client.request("GET", "/api/state")
        data = json.loads(client.getresponse().read())
        assert dumps(session.state) == before
        headers = {"Content-Type": "application/json", "X-Game-Token": data["token"]}
        body = {"name": "advance", "args": {"weeks": 1}, "revision": data["revision"], "request_id": "same-week"}
        for _ in range(2):
            client.request("POST", "/api/action", json.dumps(body), headers)
            response = client.getresponse()
            assert response.status == 200
            assert json.loads(response.read())["week"] == 1
        assert GameSession(session.path).state["week"] == 1
    finally:
        client.close()
        server.shutdown()
        server.server_close()
        thread.join()


def test_additional_experiments_distinguish_developing_from_measuring():
    s = g.execute(ready(), "experiment", {"project": "1", "method": "validate", "stat": "quality", "heroes": ["pill"]})
    view = snapshot(s)
    p = view["projects"][0]
    assert p["scene"]["activity"] == "test" and p["scene"]["total"] == 6
    assert next(h for h in view["heroes"] if h["id"] == "pill")["activity"] == "test"
    s["projects"][0]["experiment"] = {"kind": "rework", "stat": "quality"}
    s["projects"][0]["left"] = 5
    scene = snapshot(s)["projects"][0]["scene"]
    assert scene["activity"] == "make" and scene["total"] == 8 and scene["elapsed"] == 3


def test_hero_view_shows_potential_and_awakening():
    view = snapshot(ready("innovative"))
    heroes = {h["id"]: h for h in view["heroes"]}
    assert heroes["pill"]["potential"] == 88 and heroes["pill"]["awakened"] is False
    assert heroes["ruler"]["trait"]["name"] == "期中嗅觉" and heroes["ruler"]["retire_in"] is None
