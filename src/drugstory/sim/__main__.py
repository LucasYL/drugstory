"""python -m drugstory.sim：批量跑 bot，打印平衡指标。"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from drugstory.content import load_content
from drugstory.sim.bots import STRATEGIES
from drugstory.sim.run import report, run, write_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="批量跑 bot，看平衡指标")
    parser.add_argument("--runs", type=int, default=50, help="每种策略跑几局（默认 50）")
    parser.add_argument("--strategy", choices=list(STRATEGIES), action="append", help="只跑某种策略，可以写多次")
    parser.add_argument("--years", type=int, default=None, help="每局跑几年（默认 20）")
    parser.add_argument("--seed", type=int, default=1, help="第一个种子（默认 1）")
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="临时改 balance 里的数值，比如 --set scoring.yearly_growth=0.05",
    )
    parser.add_argument("--csv", type=Path, help="把每一局的结果写进 CSV")
    args = parser.parse_args()

    overrides = {}
    for item in args.set:
        key, _, value = item.partition("=")
        overrides[key] = json.loads(value)
    content = load_content(balance_overrides=overrides or None)
    strategies = args.strategy or list(STRATEGIES)

    started = time.perf_counter()
    results = run(args.runs, strategies, content, args.years, args.seed)
    print(report(results))
    print(f"\n{len(results)} 局，用时 {time.perf_counter() - started:.1f} 秒")
    if args.csv:
        write_csv(results, args.csv)
        print(f"结果写进了 {args.csv}")


if __name__ == "__main__":
    main()
