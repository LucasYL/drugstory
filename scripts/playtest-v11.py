"""v0.11 试玩研究：任期评级、章节、委托、年度奖、角色传承在正常经营里是什么样。

三种自动玩家，都只读公开信息，不读候选真值，不注资：
- 默认玩家（scripts/playtest-v10.py）：只点界面推荐按钮；谨慎（只做仿制和改良）/ 大胆两种口味。
- 证据玩家（career.bot）：按证据挑候选，必要时定向优化，期中估计低就止损。
- 新手玩家（career.bot novice）：直接选中间候选，不做专项研究。

自动玩家的结果不是人类玩家的胜率，也不说明游戏一定好玩。

    uv run python scripts/playtest-v11.py --seeds 12 --jobs 4
"""

import argparse
import collections
import importlib.util
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from drugstory.career import bot, rating
from drugstory.career.content import CATALOG

_spec = importlib.util.spec_from_file_location("playtest_v10", Path(__file__).with_name("playtest-v10.py"))
v10 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v10)


def metrics(s):
    final = s.get("final") or {**rating.summarize(s), "early": None}
    own = [d for d in s["products"] if not d["partner"]]
    return {
        "week": s["week"],
        "bankrupt": s["game_over"],
        "cash": round(s["cash"]),
        "grade": final["grade"],
        "total": final["total"],
        "ending": final["ending"],
        "dims": {d["key"]: d["score"] for d in final["dimensions"]},
        "chapters": len(s.get("chapter_log", [])),
        "stars": sum(c["stars"] for c in s.get("chapter_log", [])),
        "chapter_weeks": [c["week"] for c in s.get("chapter_log", [])],
        "bounties": len(s.get("bounties", [])),
        "bounties_done": len(s.get("bounties_done", [])),
        "awards": len(s.get("awards", [])),
        "nominations": len(s.get("nominations", [])),
        "generic": sum(d["kind"] == "generic" for d in own),
        "improved": sum(d["kind"] == "improved" for d in own),
        "innovative": sum(d["kind"] == "innovative" for d in s["products"]),
        "hard": sum(1 for d in s["products"] if d["kind"] == "innovative" and CATALOG[d["catalog"]].get("difficulty")),
        "alzheimer": sum(1 for d in s["products"] if CATALOG[d["catalog"]].get("target_id") == "abeta"),
        "patients": round(sum(d.get("patients", 0) for d in s["products"])),
        "legends_retired": sum(1 for h in s["heroes"] if h.get("retired")),
        "inheritances": len(s.get("inheritances", [])),
        "prodigy": any(h["id"] == "prodigy" for h in s["heroes"]),
        "home_rank4": sum(1 for h in s["heroes"] if h["tier"] == 1 and h["rank"] >= 4),
    }


def task(job):
    player, flavor, mode, seed, weeks = job
    if player == "default":
        s, _ = v10.play(seed, flavor, weeks, mode)
    else:
        s = bot.play(seed, flavor, novice=player == "novice", weeks=weeks)
    return {"player": player, "flavor": flavor, "mode": mode, "seed": seed, **metrics(s)}


def summarize(rows):
    def mean(key):
        return round(sum(r[key] for r in rows) / len(rows), 1)

    return {
        "runs": len(rows),
        "bankrupt": sum(r["bankrupt"] for r in rows),
        "grades": dict(sorted(collections.Counter(r["grade"] for r in rows).items())),
        "total": mean("total"),
        "endings": dict(collections.Counter(r["ending"] for r in rows).most_common()),
        "chapters": mean("chapters"),
        "stars": mean("stars"),
        "bounties_done": f"{sum(r['bounties_done'] for r in rows)}/{sum(r['bounties'] for r in rows)}",
        "awards": mean("awards"),
        "nominations": mean("nominations"),
        "generic": mean("generic"),
        "improved": mean("improved"),
        "innovative": mean("innovative"),
        "hard": mean("hard"),
        "alzheimer": sum(r["alzheimer"] for r in rows),
        "patients_wan_median": sorted(r["patients"] for r in rows)[len(rows) // 2] // 10000,
        "inheritances": mean("inheritances"),
        "legends_retired": mean("legends_retired"),
        "prodigy_hired": sum(r["prodigy"] for r in rows),
        "home_rank4": mean("home_rank4"),
        "dims": {k: round(sum(r["dims"][k] for r in rows) / len(rows), 1) for k in rating.WEIGHTS},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=12)
    parser.add_argument("--weeks", type=int, default=960)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--output", type=Path, default=Path(".artifacts/v11-study"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    seeds = range(1, args.seeds + 1)
    jobs = [
        ("default", a, m, n, args.weeks)
        for m in ("standard", "competition")
        for a in ("cautious", "bold")
        for n in seeds
    ]
    jobs += [
        (p, sc, "standard", n, args.weeks)
        for p in ("evidence", "novice")
        for sc in ("foundation", "independent")
        for n in seeds
    ]
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        rows = list(pool.map(task, jobs))
    (args.output / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    groups = collections.defaultdict(list)
    for r in rows:
        groups[f"{r['player']}/{r['flavor']}/{r['mode']}"].append(r)
    table = {k: summarize(v) for k, v in groups.items()}
    for k, v in table.items():
        print(k, json.dumps(v, ensure_ascii=False))
    (args.output / "summary.json").write_text(json.dumps(table, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
