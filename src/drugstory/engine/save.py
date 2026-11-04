"""存档、读档、回放（design/tech.md 第 8 节）。"""

from __future__ import annotations

import dataclasses
import json
import types
from pathlib import Path
from typing import Any, Union, get_args, get_origin, get_type_hints

from drugstory.content import Content
from drugstory.engine import rng
from drugstory.engine.actions import apply
from drugstory.engine.game import new_game
from drugstory.engine.loop import advance
from drugstory.engine.state import SAVE_VERSION, GameState, LoggedAction


class SaveError(ValueError):
    """存档有问题。"""


def to_data(obj: Any) -> Any:
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_data(getattr(obj, f.name)) for f in dataclasses.fields(obj) if f.name != "runtime"}
    if isinstance(obj, list):
        return [to_data(v) for v in obj]
    if isinstance(obj, dict):
        return {k: to_data(v) for k, v in obj.items()}
    return obj


def to_json(state: GameState) -> str:
    rng.sync(state)
    return json.dumps(to_data(state), ensure_ascii=False, separators=(",", ":"))


def _build(tp: Any, value: Any) -> Any:
    """按类型注解把 JSON 数据还原成 dataclass。"""
    origin = get_origin(tp)
    if tp is Any:
        return value
    if origin in (Union, types.UnionType):
        if value is None:
            return None
        return _build(next(a for a in get_args(tp) if a is not type(None)), value)
    if origin is list:
        (item,) = get_args(tp)
        return [_build(item, v) for v in value]
    if origin is dict:
        _, item = get_args(tp)
        return {k: _build(item, v) for k, v in value.items()}
    if dataclasses.is_dataclass(tp):
        hints = get_type_hints(tp)
        kwargs = {
            f.name: _build(hints[f.name], value[f.name])
            for f in dataclasses.fields(tp)
            if f.name != "runtime" and f.name in value
        }
        return tp(**kwargs)
    if tp is float:
        return float(value)
    return value


def from_json(text: str) -> GameState:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise SaveError(f"存档坏了：{e}") from None
    version = data.get("version") if isinstance(data, dict) else None
    if version not in (1, 2, SAVE_VERSION):
        raise SaveError(f"存档版本是 {version}，这个版本的游戏支持 1、2 和 {SAVE_VERSION}")
    try:
        data["version"] = SAVE_VERSION
        return _build(GameState, data)
    except (KeyError, TypeError, ValueError) as e:
        raise SaveError(f"存档坏了：{e}") from None


def save(state: GameState, path: str | Path) -> None:
    Path(path).write_text(to_json(state), encoding="utf-8")


def load(path: str | Path) -> GameState:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as e:
        raise SaveError(f"读不了存档：{e}") from None
    return from_json(text)


def replay(seed: int, log: list[LoggedAction], content: Content, scenario: str = "independent") -> GameState:
    """从同一个种子开局，在原来的周重放每一个操作。"""
    state = new_game(seed, content, scenario)
    for entry in log:
        advance(state, content, entry.week - state.week)
        if state.week != entry.week:
            raise SaveError(f"回放对不上：操作 {entry.name} 应该在第 {entry.week} 周，现在是第 {state.week} 周")
        apply(state, content, entry.name, entry.args)
    return state
