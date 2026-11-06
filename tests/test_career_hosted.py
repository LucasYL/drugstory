"""The HTTPS mount protects the shared save and keeps requests inside its prefix."""

import json
import threading
from contextlib import closing
from http.client import HTTPConnection

from drugstory.career.server import GameSession, create_server


def test_hosted_game_assets_and_shared_save(tmp_path):
    save = tmp_path / "hosted.json"
    server = create_server(GameSession(save), 0, public_url="https://example.test/game/", credentials="user:pass")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    auth = {"Host": "example.test", "Authorization": "Basic dXNlcjpwYXNz"}

    def request(method, path, headers, body=None):
        with closing(HTTPConnection("127.0.0.1", server.server_port)) as client:
            client.request(method, path, body, headers)
            response = client.getresponse()
            return response.status, response.headers, response.read()

    try:
        status, headers, _ = request("GET", "/game", {"Host": "example.test"})
        assert status == 308 and headers["Location"] == "/game/"
        for path in ("/game/", "/game/api/state", "/game/api/save", "/game/scene/figures.js"):
            assert request("GET", path, {"Host": "example.test"})[0] == 401
        assert request("POST", "/game/api/action", {"Host": "example.test"})[0] == 401
        assert request("GET", "/api/state", auth)[0] == 404
        assert request("GET", "/game-other/api/state", auth)[0] == 404
        assert request("GET", "/game/", auth | {"Host": "wrong.test"})[0] == 403
        status, headers, page = request("GET", "/game/", auth)
        assert status == 200 and b'<base href="/game/" />' in page and b'id="scene-canvas"' in page
        assert headers["Cache-Control"] == "no-store"
        assert b'<base href="/game/" />' in request("GET", "/game/text", auth)[2]
        assert request("GET", "/game/scene/figures.js", auth)[0] == 200
        first = json.loads(request("GET", "/game/api/state", auth)[2])
        mutation = auth | {"Content-Type": "application/json", "X-Game-Token": first["token"]}
        body = json.dumps({"name": "advance", "args": {"weeks": 1}, "revision": first["revision"]})
        assert request("POST", "/game/api/action", mutation | {"Origin": "https://wrong.test"}, body)[0] == 403
        assert request("POST", "/game/api/action", mutation | {"Origin": "https://example.test"}, body)[0] == 200
        second = json.loads(request("GET", "/game/api/state", auth)[2])
        assert second["week"] == GameSession(save).state["week"] == first["week"] + 1
        assert request("POST", "/game/api/action", mutation, body)[0] == 409
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
