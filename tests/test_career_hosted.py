"""The HTTPS mount protects the shared save and keeps requests inside its prefix."""

import base64
import json
import threading
from contextlib import closing
from http.client import HTTPConnection

from drugstory.career.server import GameSession, create_server


def test_hosted_game_assets_and_shared_save(tmp_path):
    save = tmp_path / "hosted.json"
    server = create_server(
        GameSession(save), 0, public_url="https://example.test/game/", credentials="user:pass\npeer:example"
    )
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
        peer_auth = auth | {"Authorization": "Basic " + base64.b64encode(b"peer:example").decode()}
        peer = json.loads(request("GET", "/game/api/state", peer_auth)[2])
        assert peer["week"] == first["week"] and peer["token"] != first["token"]
        peer_mutation = mutation | peer_auth
        assert request("POST", "/game/api/action", peer_mutation, body)[0] == 403
        peer_mutation["X-Game-Token"] = peer["token"]
        peer_body = json.dumps({"name": "advance", "args": {"weeks": 4}, "revision": peer["revision"]})
        assert request("POST", "/game/api/action", peer_mutation, peer_body)[0] == 200
        peer_save = GameSession(tmp_path / "hosted-accounts" / "peer.json").state
        assert peer_save["week"] == 4 and GameSession(save).state["week"] == 1
        assert json.loads(request("GET", "/game/api/save", peer_auth)[2])["week"] == 4
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_hosted_v8_saves_continue_in_v11_files_across_restarts(tmp_path):
    """线上服务每次都用同一个 --save-path 启动：v8 原档不改写，重启后接着 v11 的进度。"""
    from drugstory.career.model import dumps, new_game

    def v8(seed):
        s = json.loads(dumps(new_game(seed)))
        s["version"] = 8
        for key in ("term", "final", "nominations"):
            s.pop(key)
        return json.dumps(s, ensure_ascii=False)

    save = tmp_path / "hosted.json"
    peer_save = tmp_path / "hosted-accounts" / "peer.json"
    peer_save.parent.mkdir()
    save.write_text(v8(3))
    peer_save.write_text(v8(4))
    originals = save.read_text(), peer_save.read_text()

    def start():
        session = GameSession(save)
        server = create_server(session, 0, public_url="https://example.test/game/", credentials="user:pass\npeer:pw")
        server.server_close()
        return session, server.RequestHandlerClass

    def accounts(handler):
        return [cell.cell_contents for cell in handler.route.__closure__ if isinstance(cell.cell_contents, dict)][0]

    first, handler = start()
    peer = accounts(handler)[base64.b64encode(b"peer:pw")]
    assert first.path.name == "hosted-v11.json" and peer.path == tmp_path / "hosted-accounts" / "peer-v11.json"
    assert peer.state["seed"] == 4, "其他账号读回自己的 v8 进度，不是新开一局"
    first.execute({"name": "advance", "args": {"weeks": 4}, "revision": 0})
    peer.execute({"name": "advance", "args": {"weeks": 1}, "revision": 0})

    second, handler = start()
    peer = accounts(handler)[base64.b64encode(b"peer:pw")]
    assert second.state["week"] == 4 and peer.state["week"] == 1, "重启后接着 v11 存档"
    second.execute({"name": "advance", "args": {"weeks": 4}, "revision": 0})
    assert GameSession(save).state["week"] == 8
    assert (save.read_text(), peer_save.read_text()) == originals, "v8 原档不被改写"
    assert not (tmp_path / "hosted-v11-v11.json").exists()
