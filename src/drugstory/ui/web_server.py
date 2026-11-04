"""本地文字游戏网页：标准库 HTTP 服务、事务式操作、独立自动存档。"""

from __future__ import annotations

import argparse
import inspect
import json
import secrets
import tempfile
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import get_args, get_origin, get_type_hints
from urllib.parse import urlsplit

from drugstory.content import default_content
from drugstory.engine import actions
from drugstory.engine.game import new_game
from drugstory.engine.loop import advance
from drugstory.engine.save import SaveError, from_json, load, to_json
from drugstory.ui.web_view import snapshot

ASSETS = Path(__file__).with_name("web")
DEFAULT_SAVE = Path("saves/next-autosave.json")


class Conflict(ValueError):
    """另一个标签页已经推进了游戏；重读后让玩家重新决定。"""


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as f:
        temporary = Path(f.name)
        try:
            f.write(text)
            f.flush()
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def valid_type(value, hint) -> bool:
    if get_origin(hint) is list:
        return isinstance(value, list) and all(valid_type(v, get_args(hint)[0]) for v in value)
    return type(value) is hint


class GameSession:
    def __init__(self, save_path: Path, seed: int = 42, load_path: Path | None = None):
        self.content = default_content()
        self.path = save_path
        self.lock = threading.RLock()
        self.token = secrets.token_urlsafe(32)
        self.revision = 0
        source = load_path or (save_path if save_path.exists() else None)
        self.state = load(source) if source else new_game(seed, self.content)
        snapshot(self.state, self.content)  # 在改动任何存档前检查能否正常显示
        self.saved_at = None

    def view(self) -> dict:
        with self.lock:
            return {
                **snapshot(self.state, self.content), "revision": self.revision, "token": self.token,
                "saved_at": self.saved_at,
            }

    def execute(self, command: dict) -> dict:
        with self.lock:
            if command.get("revision") != self.revision:
                raise Conflict("进度已经变化，已刷新页面。请查看当前状态后再操作。")
            name, args = command.get("name"), command.get("args", {})
            if not isinstance(args, dict):
                raise ValueError("操作参数必须是一个对象")
            candidate = from_json(to_json(self.state))
            if name == "advance":
                weeks = args.get("weeks")
                if type(weeks) is not int or weeks not in (1, 4, 48):
                    raise ValueError("只能推进 1 周、4 周或快进到下一件事")
                if candidate.pending:
                    raise ValueError("先处理待决定的事情，再推进时间")
                if candidate.game_over:
                    raise ValueError("公司已破产，可以查看记录或开始新公司")
                advance(candidate, self.content, weeks)
            elif name == "save":
                pass
            elif name == "new_game":
                seed = args.get("seed", 42)
                if type(seed) is not int or not 0 <= seed <= 999999999:
                    raise ValueError("随机种子需要是 0–999999999 的整数")
                candidate = new_game(seed, self.content)
            elif isinstance(name, str) and name in actions.ACTIONS:
                fn = actions.ACTIONS[name]
                signature = inspect.signature(fn)
                signature.bind(candidate, self.content, **args)
                hints = get_type_hints(inspect.unwrap(fn))
                if any(not valid_type(value, hints[key]) for key, value in args.items()):
                    raise ValueError("操作参数的类型不正确")
                if "decision_id" in args and (
                    not candidate.pending or args["decision_id"] != candidate.pending[0].id
                ):
                    raise Conflict("这件事已经处理或排在后面，请先处理当前事件")
                actions.apply(candidate, self.content, name, args)
            else:
                raise ValueError("没有这个操作")
            result = snapshot(candidate, self.content)
            if name == "new_game":
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                backup = self.path.with_name(f"{self.path.stem}-before-new-{stamp}.json")
                atomic_write(backup, to_json(self.state))
            # 先成功落盘，再发布新状态。失败的操作不扣钱，也不消耗随机数。
            atomic_write(self.path, to_json(candidate))
            self.state = candidate
            self.revision += 1
            self.saved_at = datetime.now().astimezone().isoformat(timespec="seconds")
            return {**result, "revision": self.revision, "token": self.token, "saved_at": self.saved_at}


def create_server(session: GameSession, port: int = 8878) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            if args and str(args[1]) not in ("200", "304"):
                super().log_message(fmt, *args)

        def send_bytes(self, data: bytes, kind: str, status: int = 200, download: str | None = None):
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; object-src 'none'; "
                             "base-uri 'none'; frame-ancestors 'none'")
            if download:
                self.send_header("Content-Disposition", f'attachment; filename="{download}"')
            self.end_headers()
            self.wfile.write(data)

        def send_json(self, data, status=200):
            self.send_bytes(json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8", status)

        def local_request(self) -> bool:
            host = self.headers.get("Host", "")
            allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            return host in allowed and self.headers.get("Origin", f"http://{host}") == f"http://{host}"

        def do_GET(self):
            if not self.local_request():
                self.send_json({"error": "请从本地游戏地址打开页面"}, 403)
                return
            path = urlsplit(self.path).path
            if path == "/api/state":
                self.send_json(session.view())
            elif path == "/api/save":
                with session.lock:
                    self.send_bytes(to_json(session.state).encode(), "application/json; charset=utf-8",
                                    download=f"drugstory-week-{session.state.week}.json")
            elif path in ("/", "/app.js", "/style.css"):
                name = {"/": "index.html"}.get(path, path.lstrip("/"))
                kind = {".html": "text/html", ".js": "text/javascript", ".css": "text/css"}[Path(name).suffix]
                self.send_bytes((ASSETS / name).read_bytes(), f"{kind}; charset=utf-8")
            elif path == "/favicon.ico":
                self.send_bytes(b"", "image/x-icon", 204)
            else:
                self.send_json({"error": "页面不存在"}, 404)

        def do_POST(self):
            if not self.local_request() or self.headers.get("X-Game-Token") != session.token:
                self.send_json({"error": "连接已更新，请刷新页面后继续"}, 403)
                return
            if urlsplit(self.path).path != "/api/action":
                self.send_json({"error": "没有这个接口"}, 404)
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 65536 or self.headers.get("Content-Type") != "application/json":
                    raise ValueError("操作内容格式不正确或过大")
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError("操作内容必须是一个对象")
                self.send_json(session.execute(data))
            except Conflict as e:
                self.send_json({"error": str(e), "state": session.view()}, 409)
            except (actions.ActionError, ValueError, TypeError, KeyError) as e:
                self.send_json({"error": str(e)}, 400)
            except OSError:
                self.send_json({"error": "存档写入失败，本次操作未生效。请检查磁盘空间和存档目录权限。"}, 500)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="新药物语 · 本地鼠标操作界面")
    parser.add_argument("--port", type=int, default=8878)
    parser.add_argument("--seed", type=int, default=42, help="没有网页存档时的新局种子")
    parser.add_argument("--save-path", type=Path, default=DEFAULT_SAVE)
    parser.add_argument("--load", type=Path, help="从指定的文字版或网页版存档开始")
    args = parser.parse_args(argv)
    try:
        session = GameSession(args.save_path, args.seed, args.load)
        server = create_server(session, args.port)
    except (OSError, SaveError) as e:
        parser.exit(1, f"启动失败：{e}\n")
    print(f"新药物语：http://127.0.0.1:{server.server_port}", flush=True)
    print(f"每次操作自动保存到 {args.save_path.resolve()}；按 Ctrl+C 关闭服务。", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
