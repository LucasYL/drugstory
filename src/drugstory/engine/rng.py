"""随机流：每个系统一个独立的 random.Random，都从主种子派生。

加一个新系统、或者某个系统多抽一次随机数，都不会打乱其他系统的随机序列。
字符串种子用的是确定的哈希，不受 Python 的哈希随机化影响。随机流的状态跟着存档走。
"""

from __future__ import annotations

import random
from typing import Any

from drugstory.engine.state import GameState


def stream(state: GameState, name: str) -> random.Random:
    cache: dict[str, random.Random] = state.runtime.setdefault("rng", {})
    rng = cache.get(name)
    if rng is None:
        rng = random.Random(f"{state.seed}:{name}")
        saved = state.rng_states.get(name)
        if saved is not None:
            rng.setstate(_from_json(saved))
        cache[name] = rng
    return rng


def sync(state: GameState) -> None:
    """把正在用的随机流的状态写回 state.rng_states，存档前调用。"""
    for name, rng in state.runtime.get("rng", {}).items():
        state.rng_states[name] = _to_json(rng.getstate())


def _to_json(s: tuple[Any, ...]) -> list[Any]:
    version, internal, gauss = s
    return [version, list(internal), gauss]


def _from_json(s: list[Any]) -> tuple[Any, ...]:
    version, internal, gauss = s
    return (version, tuple(internal), gauss)
