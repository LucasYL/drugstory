"""v0.13 试玩研究：年度目标、专长与主动技能、难病搭档关、失败事件卡、花钱的出口。

玩家和 v0.12 一样（scripts/playtest-v12.py）：引导、默认（谨慎/大胆）、证据、新手，都只读公开信息，不注资。
本版另外：
- 所有玩家在研究大会出题后选第一个目标（像在界面上点第一张卡）；`--no-goals` 做不选目标的对照；
- 统计每种命令用了几次（主动技能、请专家补正、花钱的出口）；
- 记下年度目标完成情况、两次成就（编年史）之间的最长间隔、专长触发次数、失败事件卡次数、期末现金。

自动玩家的结果不是人类玩家的胜率，也不说明游戏一定好玩。

    uv run python scripts/playtest-v13.py --seeds 12 --jobs 4
    uv run python scripts/playtest-v13.py --players evidence --seeds 24 --output .artifacts/v13-evidence
"""

import argparse
import collections
import importlib.util
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from drugstory.career import engine as g

_v12 = importlib.util.spec_from_file_location("playtest_v12", Path(__file__).with_name("playtest-v12.py"))
v12 = importlib.util.module_from_spec(_v12)
_v12.loader.exec_module(v12)

COUNTS = collections.Counter()
PICK_GOALS = True
_execute = g.execute


def _counted(fn):
    def wrapper(s, **args):
        out = fn(s, **args)  # 只数成功的操作；被引擎拒绝的尝试不算
        COUNTS[fn.__name__] += 1
        return out

    wrapper.__name__ = fn.__name__
    wrapper.__annotations__ = fn.__annotations__
    wrapper.__signature__ = __import__("inspect").signature(fn)
    return wrapper


def execute(state, command, args=None):
    """真实引擎；之后若有没选的年度目标，就选第一个。"""
    out = _execute(state, command, args or {})
    goal = out.get("year_goal")
    if PICK_GOALS and goal and goal["picked"] is None and goal["offers"] and not out["game_over"]:
        out = _execute(out, "pick_goal", {"goal": goal["offers"][0]})
    return out


def install():
    """每个进程只包一次（ProcessPoolExecutor 会在同一进程里跑多局）。"""
    if g.execute is execute:
        return
    g.COMMANDS.update({name: _counted(fn) for name, fn in g.COMMANDS.items()})
    g.execute = execute


def max_gap(s):
    weeks = sorted({0, *(c["week"] for c in s.get("chronicle", []))})
    end = s["week"]
    return max(b - a for a, b in zip(weeks, [*weeks[1:], end], strict=True))


def extra(s):
    picked = s.get("goal_history", [])
    return {
        "goals_picked": len(picked),
        "goals_done": len(s.get("goal_log", [])),
        "goal_keys_done": [x["key"] for x in s.get("goal_log", [])],
        "max_gap": max_gap(s),
        "talent_uses": sum(sum(h.get("talent_uses", {}).values()) for h in s["heroes"]),
        "talent_by_hero": {
            h["id"]: sum(h.get("talent_uses", {}).values()) for h in s["heroes"] if h.get("talent_uses")
        },
        "incidents": sum(1 for p in s["projects"] for r in p["results"] if not r["passed"]),
        "lines": sum(1 for d in s["products"] if d.get("production") == "self"),
        "access": sum(1 for d in s["products"] if d.get("access")),
        "fellowships": s.get("fellowships", 0),
        "wards": s.get("wards", 0),
        "invest_spent": round(
            sum(s["expense"].get(k, 0) for k in ("lines", "access", "fellowship", "wards", "operations"))
        ),
        "commands": dict(COUNTS),
    }


def task(job, pick_goals=True):
    global PICK_GOALS
    PICK_GOALS = pick_goals
    install()
    COUNTS.clear()
    captured = {}
    original = v12.v11.metrics

    def metrics(s):
        captured["s"] = s
        return original(s)

    v12.v11.metrics = metrics
    try:
        row = v12.task(job)
    finally:
        v12.v11.metrics = original
    row.update(extra(captured["s"]))
    return row


def median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else None


def summarize(rows):
    out = v12.summarize(rows)
    out.update(
        cash_median=median(r["cash"] for r in rows),
        goals=f"{sum(r['goals_done'] for r in rows)}/{sum(r['goals_picked'] for r in rows)}",
        max_gap_median=median(r["max_gap"] for r in rows),
        talent_uses_median=median(r["talent_uses"] for r in rows),
        skills_median=median(r["commands"].get("use_skill", 0) for r in rows),
        incidents_median=median(r["incidents"] for r in rows),
        expert_reworks=sum(r["commands"].get("rework_expert", 0) for r in rows),
        reworks=sum(r["commands"].get("rework", 0) for r in rows),
        lines_median=median(r["lines"] for r in rows),
        wards_median=median(r["wards"] for r in rows),
        fellowships_median=median(r["fellowships"] for r in rows),
        access_median=median(r["access"] for r in rows),
        invest_spent_median=median(r["invest_spent"] for r in rows),
    )
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=12)
    parser.add_argument("--weeks", type=int, default=960)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--players", default="guided,default,evidence,novice")
    parser.add_argument("--output", type=Path, default=Path(".artifacts/v13-study"))
    parser.add_argument("--no-goals", action="store_true", help="对照：不选年度目标")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    seeds = range(1, args.seeds + 1)
    players = args.players.split(",")
    jobs = []
    if "guided" in players:
        jobs += [("guided", "guide", m, n, args.weeks) for m in ("standard", "competition") for n in seeds]
    if "default" in players:
        jobs += [
            ("default", a, m, n, args.weeks)
            for m in ("standard", "competition")
            for a in ("cautious", "bold")
            for n in seeds
        ]
    for p in ("evidence", "novice"):
        if p in players:
            jobs += [(p, sc, "standard", n, args.weeks) for sc in ("foundation", "independent") for n in seeds]
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        rows = list(pool.map(task, jobs, [not args.no_goals] * len(jobs)))
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
