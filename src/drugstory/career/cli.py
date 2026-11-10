"""Compact terminal frontend for the same v10 action engine."""

import argparse
import json
from pathlib import Path

from . import engine
from .content import SCENARIOS
from .model import dumps, load, new_game, resolve_save
from .server import atomic_write
from .view import snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(description="新药物语 · 一屏研究所 v0.12")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--scenario", choices=list(SCENARIOS), default="foundation")
    parser.add_argument("--difficulty", choices=["standard", "competition"], default="standard")
    parser.add_argument("--term", type=int, choices=[10, 20], default=10)
    parser.add_argument("--load", type=Path)
    parser.add_argument("--save", type=Path, default=Path("saves/institute-cli.json"))
    args = parser.parse_args(argv)
    found, args.save = resolve_save(args.save)
    source = args.load or found
    s = load(source) if source else new_game(args.seed, args.scenario, args.difficulty, args.term)
    if s.pop("migrated_from", None):
        # 旧版存档只读不改，新进度写到本版本的文件
        print(f"已读入旧版存档 {source}；原文件不改写，新进度保存到 {args.save}")
    print("输入 view 查看，next 推进到下一件需要你的事，help 列出操作，或 操作名 {JSON参数}；quit 退出。")
    while True:
        try:
            command = input("> ").strip()
            if command in ("quit", "q"):
                return
            if command in ("view", "v"):
                print(json.dumps(snapshot(s), ensure_ascii=False, indent=2))
                continue
            if command == "help":
                import inspect

                for name, fn in engine.COMMANDS.items():
                    print(name, inspect.signature(fn))
                continue
            name, _, raw = command.partition(" ")
            if name == "next":
                # "next" skips development batches and readouts; "next_event" keeps the old pace.
                name, raw = "next_event", raw or '{"batches": 0}'
            candidate = engine.execute(s, name, json.loads(raw) if raw else {})
            atomic_write(args.save, dumps(candidate))
            s = candidate
            print(f"第 {s['week']} 周 · 现金 ¥{s['cash']:,.0f} 万")
            for event in s["journal"][-3:]:
                print(event["text"])
        except (ValueError, TypeError, OSError) as ex:
            print(ex)
        except (EOFError, KeyboardInterrupt):
            return


if __name__ == "__main__":
    main()
