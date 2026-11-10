"""存档 v10：旧版本的文件只读不改，新进度写到本版本的文件；重启后接着新文件玩。"""

import json

import pytest

from drugstory.career.model import SUFFIX, VERSION, dumps, load, new_game, resolve_save
from drugstory.career.server import GameSession, create_server

CUR = SUFFIX[VERSION]  # 本版本写的文件后缀


def old_save(seed, version):
    s = json.loads(dumps(new_game(seed)))
    s["version"] = version
    for key in ("tips_seen", "chronicle"):
        s.pop(key)
    for p in s["projects"]:
        p.pop("autopilot", None)
        p.pop("pace", None)
    if version == 8:
        for key in ("term", "final", "nominations"):
            s.pop(key)
    return json.dumps(s, ensure_ascii=False)


def test_only_v8_reads_original_and_writes_new_file(tmp_path):
    base = tmp_path / "game.json"
    base.write_text(old_save(1, 8))
    before = base.read_bytes()
    session = GameSession(base)
    assert session.path == tmp_path / f"game{CUR}.json" and session.upgraded_from == 8
    assert session.state["version"] == VERSION and session.state["tips_seen"] == []
    session.execute({"name": "advance", "args": {"weeks": 1}, "revision": 0})
    assert base.read_bytes() == before
    assert load(session.path)["week"] == 1


def test_v11_progress_wins_over_v8_and_both_stay_untouched(tmp_path):
    base, v11 = tmp_path / "game.json", tmp_path / "game-v11.json"
    base.write_text(old_save(1, 8))
    v11.write_text(old_save(2, 9))
    originals = base.read_bytes(), v11.read_bytes()
    session = GameSession(base)
    assert session.source == v11 and session.state["seed"] == 2
    session.execute({"name": "advance", "args": {"weeks": 4}, "revision": 0})
    assert (base.read_bytes(), v11.read_bytes()) == originals
    again = GameSession(base)
    assert again.source == tmp_path / f"game{CUR}.json" and again.state["week"] == 4
    assert again.path == again.source


def test_suffixed_path_does_not_stack_suffixes(tmp_path):
    v11 = tmp_path / "game-v11.json"
    v11.write_text(old_save(3, 9))
    found, write = resolve_save(v11)
    assert found == v11 and write == tmp_path / f"game{CUR}.json"
    assert resolve_save(tmp_path / "fresh-v11.json") == (None, tmp_path / f"fresh{CUR}.json")
    assert resolve_save(tmp_path / "fresh.json") == (None, tmp_path / "fresh.json")


def test_current_version_file_is_written_in_place(tmp_path):
    path = tmp_path / "game.json"
    session = GameSession(path)
    session.execute({"name": "advance", "args": {"weeks": 1}, "revision": 0})
    assert session.path == path and resolve_save(path) == (path, path)


def test_hosted_accounts_follow_the_same_rule(tmp_path):
    save = tmp_path / "hosted.json"
    peer_dir = tmp_path / "hosted-accounts"
    peer_dir.mkdir()
    save.write_text(old_save(4, 8))
    (peer_dir / "peer-v11.json").write_text(old_save(5, 9))
    server = create_server(GameSession(save), 0, public_url="https://example.test/game/", credentials="a:b\npeer:c")
    server.server_close()
    accounts = next(
        c.cell_contents for c in server.RequestHandlerClass.route.__closure__ if isinstance(c.cell_contents, dict)
    )
    peer = next(a for a in accounts.values() if a.state["seed"] == 5)
    assert peer.path == peer_dir / f"peer{CUR}.json"


def test_playlog_records_actions(tmp_path):
    log = tmp_path / "play.jsonl"
    session = GameSession(tmp_path / "g.json", playlog=log)
    session.execute({"name": "advance", "args": {"weeks": 1}, "revision": 0})
    with pytest.raises(ValueError):
        session.execute({"name": "promote", "args": {"character": "beaker"}, "revision": 1})
    lines = [json.loads(x) for x in log.read_text().splitlines()]
    assert [x["ok"] for x in lines] == [True, False]
    assert lines[1]["args"] == {"character": "beaker"} and lines[1]["error"]


def test_chronicle_records_launch_and_promotion():
    from drugstory.career import bot

    s = bot.play(1, weeks=200)
    kinds = {e["kind"] for e in s["chronicle"]}
    assert "launch" in kinds
    assert all(set(e) == {"week", "kind", "text", "actors"} for e in s["chronicle"])
