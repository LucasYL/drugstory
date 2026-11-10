"""v0.12 试玩研究：引导、仿制药交给团队、数字换词之后，各类玩家二十年后会怎样。

四种自动玩家，都只读公开快照或公开信念，不读候选真值，不注资：
- 引导玩家（新）：像新手一样只做屏幕上给的事——决定卡主按钮、候选选「稳妥」、左上角引导的建议、
  第二款起的仿制药「交给团队 · 标准」，其余时间按「下一件事」。用来量 W1 引导和 W2 交给团队的效果。
- 默认玩家（scripts/playtest-v10.py）：只点推荐按钮，但会自己晋阶、招人、扩建；谨慎 / 大胆两种口味。
- 证据玩家（career.bot）：按证据挑候选，必要时定向优化，期中估计低就止损。
- 新手玩家（career.bot novice）。

自动玩家的结果不是人类玩家的胜率，也不说明游戏一定好玩。

    uv run python scripts/playtest-v12.py --seeds 12 --jobs 4
"""

import argparse
import collections
import importlib.util
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from drugstory.career import engine as g
from drugstory.career.model import blocking, new_game
from drugstory.career.view import snapshot

_v11 = importlib.util.spec_from_file_location("playtest_v11", Path(__file__).with_name("playtest-v11.py"))
v11 = importlib.util.module_from_spec(_v11)
_v11.loader.exec_module(v11)

DECIDE = ("selecting", "ready", "result", "problem", "checkpoint")
RESERVE = 300  # 万：界面按钮下出现现金警告的线


def act(s, command, args):
    try:
        return g.execute(s, command, args)
    except ValueError:
        return None


def steady(p):
    return max(p["candidates"], key=lambda c: min(x["low"] for x in c["evidence"]))["id"]


def start_route(s, v, route, catalog=None):
    """「开始一个 X 项目」：引导点名的那条路线，或新项目页自动选中的第一张可开始的卡；仿制药能交给团队就交给团队。"""
    team = v["assist"]["screen"][route]
    if catalog:
        return act(s, "start_project", {"catalog": catalog, "heroes": team})
    for c in v["catalog"]:
        if c["kind"] == route and c["unlocked"] and not c["occupied"]:
            args = {"catalog": c["key"], "heroes": team}
            if c.get("autopilot"):
                args["autopilot"] = "standard"
            return act(s, "start_project", args)
    return None


def guided_step(s):
    v = snapshot(s)
    for p in v["projects"]:
        if not p["active"] or p["deferred"] or p["autopilot"] or p["status"] not in DECIDE:
            continue
        if p["status"] == "selecting":
            return act(s, "choose_candidate", {"project": p["id"], "candidate": steady(p)}), "decide"
        if p["status"] == "checkpoint":
            chance = p["trial_decision"]["chance"]
            choice = "stop" if chance is not None and chance <= 15 else "keep"
            return act(s, "trial_decision", {"project": p["id"], "choice": choice}), "decide"
        q = p["quick"]
        if q and q["ok"]:
            # 界面在按钮下写「开工后可用现金…可以先接服务或暂缓」时，像谨慎的新手一样先暂缓
            if q["command"] != "launch" and q["cost"] and v["available_cash"] - q["cost"] < RESERVE:
                return act(s, "defer", {"project": p["id"]}), "defer"
            return act(s, q["command"], q["args"]), "decide"
        if p["status"] == "problem" or not q:
            return act(s, "terminate", {"project": p["id"]}), "stop"
        return act(s, "defer", {"project": p["id"]}), "defer"
    for p in v["projects"]:
        q = p["quick"]
        roomy = q and (q["command"] == "launch" or not q["cost"] or v["available_cash"] - q["cost"] >= RESERVE)
        if p["active"] and p["deferred"] and q and q["ok"] and roomy:
            return act(s, q["command"], q["args"]), "resume"
    tip = next((x for x in v["guide"] if x["ok"]), None)
    if tip:
        if tip["command"]:
            return act(s, tip["command"], tip["args"]), "guide:" + tip["kind"]
        if tip["kind"] == "project" and tip["route"]:
            return start_route(s, v, tip["route"], tip.get("catalog")), "guide:project"
        if tip["kind"] == "services":
            assignments = [
                {"order": k, "character": x["hero"]} for k, x in v["assist"]["services"].items() if x["hero"]
            ]
            return act(s, "take_services", {"assignments": assignments[:3]}), "guide:services"
        if tip["kind"] == "personal":
            info = next(h for h in v["heroes"] if h["id"] == tip["hero"])["personal_project"]
            if info["partners"]:
                args = {"character": tip["hero"], "partner": info["partners"][0], "choice": "practice"}
                return act(s, "personal_project", args), "guide:personal"
    if not any(p["active"] for p in v["projects"]):
        # 研究台空着：点「开始下一个项目」
        for route in ("generic", "improved", "innovative"):
            out = start_route(s, v, route)
            if out:
                return out, "start"
    return None, "next"


def next_event(s):
    try:
        return g.execute(s, "next_event", {"batches": 0})
    except ValueError:
        for p in s["projects"]:
            if blocking(p):
                s = g.execute(s, "defer", {"project": p["id"]})
        return g.execute(s, "next_event", {"batches": 0})


def guided_play(seed, mode, weeks):
    s = new_game(seed, "foundation", mode, term=20)
    counts = collections.Counter()
    since = 0
    for _ in range(20000):
        if s["week"] >= weeks or s["game_over"]:
            break
        before = s["week"]
        out, kind = guided_step(s)
        since = since + 1 if out is not None and out["week"] == before else 0
        if out is None or since > 12:
            out, kind, since = next_event(s), "next", 0
        s = out
        counts[kind] += 1
    return s, dict(counts)


def task(job):
    player, flavor, mode, seed, weeks = job
    if player == "guided":
        s, counts = guided_play(seed, mode, weeks)
        row = v11.metrics(s)
        row["actions"] = counts
    else:
        row = v11.task(job)
        row.pop("player", None)
        for k in ("flavor", "mode", "seed"):
            row.pop(k, None)
    row.update(player=player, flavor=flavor, mode=mode, seed=seed)
    if player == "guided":
        row["first_rank2"] = s["first_rank2"]
        row["chapter2_week"] = next((c["week"] for c in s["chapter_log"] if c["chapter"] == 1), None)
        row["partners"] = sum(h["employed"] for h in s["heroes"])
    return row


def summarize(rows):
    out = v11.summarize(rows)
    if rows and rows[0]["player"] == "guided":
        weeks = sorted(r["chapter2_week"] for r in rows if r["chapter2_week"] is not None)
        out["chapter2_done"] = f"{len(weeks)}/{len(rows)}"
        out["chapter2_week_median"] = weeks[len(weeks) // 2] if weeks else None
        out["partners_median"] = sorted(r["partners"] for r in rows)[len(rows) // 2]
        out["first_elite_median"] = sorted(r["first_rank2"] or 9999 for r in rows)[len(rows) // 2]
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=12)
    parser.add_argument("--weeks", type=int, default=960)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--players", default="guided,default,evidence,novice")
    parser.add_argument("--output", type=Path, default=Path(".artifacts/v12-study"))
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
