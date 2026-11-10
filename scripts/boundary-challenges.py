"""三种难病搭档关的边界研究（构造的后期状态，不是正常经营）：凑齐对的人有多大机会？

每种病三组团队：完全解决每道关的人都在、只有部分解决的人、没人能过关。其余专业用同样的大师级见习伙伴补齐，
尽量只让「谁能过关」不同。决定由证据型玩家（career.bot）做，带分层打法，不读候选真值。

    uv run python scripts/boundary-challenges.py --seeds 40
"""

import argparse
import collections
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("boundary", Path(__file__).with_name("boundary-hard-targets.py"))
boundary = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(boundary)

# catalog: {团队名: 人}
TEAMS = {
    "n_kras__small_molecule": {
        "全齐": ["alchemist", "bridge", "guardian", "ruler", "pill"],
        "部分": ["wizard", "star", "shield", "ruler", "pill"],
        "没人能过": ["beaker", "sprout", "bubble", "ruler", "pill"],
    },
    "n_hbv__sirna": {
        "全齐": ["star", "oracle", "judge", "beaker", "pill"],
        "部分": ["sprout", "curve", "bubble", "beaker", "pill"],
        "没人能过（小分子）": ["sprout", "ruler", "shield", "beaker", "pill"],
    },
    "n_rna": {
        "全齐": ["bridge", "oracle", "forge", "beaker", "bubble"],
        "部分": ["sprout", "strategist", "crystal", "ruler", "beaker", "bubble"],
        "没人能过": ["sprout", "curve", "pill", "beaker", "bubble"],
    },
}
CATALOG_FOR = {"没人能过（小分子）": "n_hbv__small_molecule"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=40)
    args = parser.parse_args()
    for catalog, teams in TEAMS.items():
        print(f"== {catalog}，种子 1–{args.seeds}")
        for name, people in teams.items():
            spec = (people, 3, 20, 3, 6, "smart", [])
            outcomes = collections.Counter()
            for seed in range(1, args.seeds + 1):
                status, _ = boundary.run(seed, spec, CATALOG_FOR.get(name, catalog))
                outcomes[status] += 1
            rate = outcomes["approved"] / args.seeds
            print(f"  {name}：获批 {outcomes['approved']}/{args.seeds}（{rate:.0%}） {dict(outcomes)}")


if __name__ == "__main__":
    main()
