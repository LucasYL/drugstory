"""本地文字游戏网页：标准库 HTTP 服务、事务式操作、独立自动存档。"""

from __future__ import annotations

import argparse
import base64
import hmac
import json
import re
import secrets
import tempfile
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from drugstory.career import api, engine
from drugstory.career.content import SCENARIOS
from drugstory.career.model import dumps as to_json
from drugstory.career.model import load, new_game
from drugstory.career.view import phase_preview, snapshot

ASSETS = Path(__file__).with_name("web")
DEFAULT_SAVE = Path("saves/scene-autosave.json")


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


class GameSession:
    def __init__(self, save_path: Path, seed=42, load_path=None, scenario="foundation", difficulty="standard"):
        self.path = save_path
        self.lock = threading.RLock()
        self.token = secrets.token_urlsafe(32)
        self.revision = 0
        self.requests = {}
        source = load_path or (save_path if save_path.exists() else None)
        self.state = load(source) if source else new_game(seed, scenario, difficulty)
        snapshot(self.state)
        self.saved_at = None

    def view(self):
        with self.lock:
            return {**snapshot(self.state), "revision": self.revision, "token": self.token, "saved_at": self.saved_at}

    def execute(self, command):
        with self.lock:
            request_id = command.get("request_id")
            if request_id is not None:
                if not isinstance(request_id, str) or not 1 <= len(request_id) <= 100:
                    raise ValueError("请求编号格式错误")
                if request_id in self.requests:
                    if self.requests[request_id] != command:
                        raise Conflict("同一请求编号不能用于不同操作")
                    return self.view()
            if command.get("revision") != self.revision:
                raise Conflict("进度已经变化，请查看最新状态后再操作。")
            candidate = engine.execute(self.state, command.get("name"), command.get("args", {}))
            result = snapshot(candidate)
            if command.get("name") == "new_game":
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                backup = self.path.with_name(f"{self.path.stem}-before-new-{stamp}.json")
                atomic_write(backup, to_json(self.state))
            atomic_write(self.path, to_json(candidate))
            if request_id:
                self.requests[request_id] = dict(command)
                if len(self.requests) > 256:
                    del self.requests[next(iter(self.requests))]
            self.state = candidate
            self.revision += 1
            self.saved_at = datetime.now().astimezone().isoformat(timespec="seconds")
            return {**result, "revision": self.revision, "token": self.token, "saved_at": self.saved_at}


def create_server(
    session: GameSession, port: int = 8885, *, public_url: str = "", credentials: str = ""
) -> ThreadingHTTPServer:
    public = urlsplit(public_url)
    prefix = public.path.rstrip("/")
    accounts: dict[bytes, GameSession] = {}
    if public_url:
        if (
            public.scheme != "https"
            or not re.fullmatch(r"[a-zA-Z0-9.-]+(?::[0-9]+)?", public.netloc)
            or not re.fullmatch(r"(?:/[a-zA-Z0-9_-]+)+", prefix)
            or public.query
            or public.fragment
        ):
            raise ValueError("线上模式需要 HTTPS 子路径")
        lines = [line for line in credentials.splitlines() if line]
        if not lines:
            raise ValueError("线上模式需要至少一个账号")
        usernames = set()
        for i, line in enumerate(lines):
            username, _, _ = line.partition(":")
            if (
                not re.fullmatch(r"[!-9;-~]+:[!-~]+", line)
                or (i and not re.fullmatch(r"[a-zA-Z0-9_-]+", username))
                or username.casefold() in usernames
            ):
                raise ValueError("账号格式错误或用户名重复")
            usernames.add(username.casefold())
        save_dir = session.path.with_name(f"{session.path.stem}-accounts")
        for i, line in enumerate(lines):
            username = line.split(":", 1)[0]
            account = session
            if i:
                account = GameSession(
                    save_dir / f"{username}.json",
                    seed=session.state["seed"],
                    scenario=session.state["scenario"],
                    difficulty=session.state["difficulty"],
                )
            accounts[base64.b64encode(line.encode("ascii"))] = account

    class Handler(BaseHTTPRequestHandler):
        timeout = 20

        def log_message(self, fmt, *args):
            if args and str(args[1]) not in ("200", "304"):
                super().log_message(fmt, *args)

        def send_bytes(self, data: bytes, kind: str, status: int = 200, download: str | None = None):
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'self'; style-src-attr 'unsafe-inline'; "
                "object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
            )
            if download:
                self.send_header("Content-Disposition", f'attachment; filename="{download}"')
            self.end_headers()
            self.wfile.write(data)

        def send_json(self, data, status=200):
            self.send_bytes(json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8", status)

        def route(self) -> tuple[str, GameSession] | None:
            host = self.headers.get("Host", "")
            allowed = (
                {public.netloc}
                if public_url
                else {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            )
            origin = f"{'https' if public_url else 'http'}://{host}"
            if host not in allowed or self.headers.get("Origin", origin) != origin:
                self.send_json({"error": "请从游戏地址打开页面"}, 403)
                return None
            path = urlsplit(self.path).path
            if prefix and path == prefix and self.command == "GET":
                self.send_response(308)
                self.send_header("Location", f"{prefix}/")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return None
            if prefix and not path.startswith(f"{prefix}/"):
                self.send_json({"error": "页面不存在"}, 404)
                return None
            account = session
            if public_url:
                scheme, _, value = self.headers.get("Authorization", "").partition(" ")
                key = value.encode("latin-1") if scheme.lower() == "basic" else b""
                account = next((owner for auth, owner in accounts.items() if hmac.compare_digest(key, auth)), None)
                if account is None:
                    self.send_response(401)
                    self.send_header("WWW-Authenticate", 'Basic realm="Drugstory", charset="UTF-8"')
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return None
            return path[len(prefix) :], account

        def asset(self, name: str):
            path = ASSETS / name
            data = path.read_bytes()
            kind = {".html": "text/html", ".js": "text/javascript", ".css": "text/css"}[path.suffix]
            if path.suffix == ".html" and prefix:
                data = data.replace(b'<base href="/" />', f'<base href="{prefix}/" />'.encode(), 1)
            self.send_bytes(data, f"{kind}; charset=utf-8")

        def do_GET(self):
            route = self.route()
            if route is None:
                return
            path, session = route
            if path == "/api/state":
                self.send_json(api.state(session.view()))
            elif path == "/api/content":
                self.send_json(api.content())
            elif path == "/api/save":
                with session.lock:
                    self.send_bytes(
                        to_json(session.state).encode(),
                        "application/json; charset=utf-8",
                        download=f"drugstory-week-{session.state['week']}.json",
                    )
            elif path in (
                "/scene",
                "/scene/",
                "/scene/index.html",
                "/scene/renderer.js",
                "/scene/figures.js",
                "/scene/world.js",
                "/scene/ui.js",
                "/scene/panels.js",
                "/scene/style.css",
            ):
                self.asset("scene/index.html" if path in ("/scene", "/scene/") else path.lstrip("/"))
            elif path == "/" and public_url:
                self.asset("scene/index.html")
            elif path in ("/", "/text", "/app.js", "/honors.js", "/projects.js", "/style.css", "/api-driver.js"):
                self.asset("index.html" if path in ("/", "/text") else path.lstrip("/"))
            elif path == "/favicon.ico":
                self.send_bytes(b"", "image/x-icon", 204)
            else:
                self.send_json({"error": "页面不存在"}, 404)

        def do_POST(self):
            route = self.route()
            if route is None:
                return
            path, session = route
            if self.headers.get("X-Game-Token") != session.token:
                self.send_json({"error": "连接已更新，请刷新页面后继续"}, 403)
                return
            if path not in ("/api/action", "/api/preview"):
                self.send_json({"error": "没有这个接口"}, 404)
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 65536 or self.headers.get("Content-Type") != "application/json":
                    raise ValueError("操作内容格式不正确或过大")
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError("操作内容必须是一个对象")
                if path == "/api/preview":
                    with session.lock:
                        if data.get("revision") != session.revision:
                            raise Conflict("进度已经变化，请重新选择方案。")
                        self.send_json(phase_preview(session.state, data.get("args", {})))
                else:
                    self.send_json(api.state(session.execute(data)))
            except Conflict as e:
                self.send_json({"error": str(e), "state": api.state(session.view())}, 409)
            except (ValueError, TypeError, KeyError) as e:
                self.send_json({"error": str(e)}, 400)
            except OSError:
                self.send_json({"error": "存档写入失败，本次操作未生效。请检查磁盘空间和存档目录权限。"}, 500)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="新药物语 · 一屏研究所 v0.10")
    parser.add_argument("--port", type=int, default=8885)
    parser.add_argument("--seed", type=int, default=42, help="没有网页存档时的新局种子")
    parser.add_argument("--scenario", choices=list(SCENARIOS), default="foundation")
    parser.add_argument("--difficulty", choices=["standard", "competition"], default="standard")
    parser.add_argument("--save-path", type=Path, default=DEFAULT_SAVE)
    parser.add_argument("--load", type=Path, help="从指定的文字版或网页版存档开始")
    parser.add_argument("--public-url", default="", help="HTTPS 反代入口，例如 https://example.com/game/")
    parser.add_argument("--auth-file", type=Path, help="线上登录文件，每行一个 用户名:密码。首个账号使用指定存档。")
    args = parser.parse_args(argv)
    try:
        session = GameSession(args.save_path, args.seed, args.load, args.scenario, args.difficulty)
        credentials = args.auth_file.read_text().rstrip("\r\n") if args.auth_file else ""
        server = create_server(session, args.port, public_url=args.public_url, credentials=credentials)
    except (OSError, ValueError) as e:
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
