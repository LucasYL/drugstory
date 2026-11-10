"""仿制药三种做法（标准 / 加急 / 精工）谁更划算：校准用的分析脚本。

这是分析，不是玩家策略：它比较的是真实结果（任期内的利润减去花费），会读模拟后的真实收入，
但三种做法本身只用公开信息（交给团队后由引擎按公开证据推进）。

起点：每个种子用推荐操作做完第一款仿制药（稳压片）。然后对另外五种仿制药 × 三种做法，各跑一次
「只做这一个项目，一直到任期结束」，记下这款药在任期内的累计利润减去项目花费。
要求：每种做法最好的比例都在 20%–60% 之间。

    uv run python scripts/generic-plans.py --seeds 20 --jobs 4
"""

import argparse
import collections
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from drugstory.career import assist
from drugstory.career import engine as g
from drugstory.career.model import blocking, new_game

GENERICS = ["g_lipid", "g_pain", "g_sugar", "g_allergy", "g_inflammation"]
MODES = ["standard", "rush", "craft"]
TERM = 960


def first_generic(seed, term=20):
    s = new_game(seed, term=term)
    s = g.execute(s, "start_project", {"catalog": "g_pressure", "heroes": ["beaker", "pill"]})
    while not s["products"]:
        p = next((p for p in s["projects"] if blocking(p)), None)
        if p is None:
            s = g.execute(s, "next_event", {"batches": 0})
        elif p["status"] == "selecting":
            s = g.execute(s, "choose_candidate", {"project": p["id"], "candidate": assist.steady_candidate(p)})
        else:
            q = assist.quick(s, p)
            if q is None or not q["ok"]:
                s = g.execute(s, "terminate", {"project": p["id"]})
                return s
            s = g.execute(s, q["command"], q["args"])
    return s


def run(job):
    seed, catalog, mode, term = job
    end = term * 48
    s = first_generic(seed, term)
    if not s["products"]:
        return None
    team = assist.screening_team(s, "generic") or ["beaker", "pill"]
    s = g.execute(s, "start_project", {"catalog": catalog, "heroes": team, "autopilot": mode})
    pid = s["projects"][-1]["id"]
    while s["week"] < end and not s["game_over"]:
        p = next(p for p in s["projects"] if p["id"] == pid)
        if blocking(p):
            q = assist.quick(s, p)
            if p["status"] == "problem" and q and q["ok"]:
                s = g.execute(s, q["command"], q["args"])
                s = g.execute(s, "set_autopilot", {"project": pid, "mode": mode})
            else:
                s = g.execute(s, "terminate", {"project": pid})
            continue
        s = g.execute(s, "advance", {"weeks": 48 if end - s["week"] >= 48 else 1})
    p = next(p for p in s["projects"] if p["id"] == pid)
    d = next((d for d in s["products"] if d["project"] == pid), None)
    profit = d["total_profit"] if d else 0.0
    return {
        "seed": seed,
        "catalog": catalog,
        "mode": mode,
        "launched": d["launched"] if d else None,
        "status": p["status"],
        "spent": round(p["spent"]),
        "profit": round(profit),
        "net": round(profit - p["spent"]),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--term", type=int, choices=[10, 20], default=20)
    parser.add_argument("--output", type=Path, default=Path(".artifacts/generic-plans"))
    args = parser.parse_args()
    jobs = [(seed, c, m, args.term) for seed in range(1, args.seeds + 1) for c in GENERICS for m in MODES]
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        rows = [r for r in pool.map(run, jobs) if r]
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / f"results-{args.term}y.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    cases = collections.defaultdict(dict)
    for r in rows:
        cases[(r["seed"], r["catalog"])][r["mode"]] = r
    wins = collections.Counter()
    for by_mode in cases.values():
        if len(by_mode) == 3:
            wins[max(MODES, key=lambda m: by_mode[m]["net"])] += 1
    total = sum(wins.values())
    summary = {
        "cases": total,
        "best_share": {m: round(wins[m] / total, 2) for m in MODES},
        "mean_net": {
            m: round(sum(r["net"] for r in rows if r["mode"] == m) / max(1, sum(r["mode"] == m for r in rows)))
            for m in MODES
        },
        "launched": {m: sum(r["launched"] is not None for r in rows if r["mode"] == m) for m in MODES},
        "mean_launch_week": {
            m: round(
                sum(r["launched"] for r in rows if r["mode"] == m and r["launched"])
                / max(1, sum(1 for r in rows if r["mode"] == m and r["launched"]))
            )
            for m in MODES
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    (args.output / f"summary-{args.term}y.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
