"""v0.10 一键默认玩家：只读公开快照，只用界面上的推荐。

它做的事和一个只点大按钮的新手一样：决定卡点主按钮、候选选「稳妥」、服务用默认人选、
新项目点第一张可开始的卡、能晋阶就晋阶、钱多了扩建和招人，其余时间按「下一件事」。
用来回答：只靠默认值，二十年后会怎样？会破产吗？多久要做一次决定？
不读取隐藏的候选真值，不注入资金。
"""

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from drugstory.career import economy as e
from drugstory.career import engine as g
from drugstory.career.model import dumps, new_game
from drugstory.career.view import snapshot

RESERVE = 400  # 万：开工前保留的周转金
DECIDE = ("selecting", "ready", "result", "problem", "checkpoint")


def steady(p):
    """和界面上的「稳妥」标签一样：最弱一项的下限最高的候选。"""
    return max(p["candidates"], key=lambda c: min(x["low"] for x in c["evidence"]))["id"]


def act(s, command, args):
    try:
        return g.execute(s, command, args)
    except ValueError:
        return None


def step(s, appetite, waiting):
    """waiting：记录为什么暂缓（缺钱或缺人），只用于统计。"""
    v = snapshot(s)
    cash = v["available_cash"]
    # 顶部提示条变红（现金只够撑 16 周以内）时，像玩家一样先停下花钱的事
    tight = v["runway"] is not None and v["runway"] < 16
    for p in v["projects"]:
        if not p["active"] or p["deferred"] or p["status"] not in DECIDE:
            continue
        if p["status"] == "selecting":
            return act(s, "choose_candidate", {"project": p["id"], "candidate": steady(p)}), "decide"
        if p["status"] == "checkpoint":
            chance = p["trial_decision"]["chance"]
            choice = "stop" if chance is not None and chance <= 15 else "keep"
            return act(s, "trial_decision", {"project": p["id"], "choice": choice}), "decide"
        q = p["quick"]
        if q and q["ok"]:
            if q["command"] != "launch" and q["cost"] and (cash - q["cost"] < RESERVE or tight):
                waiting[p["id"]] = ("cash", q["cost"] + RESERVE, s["week"])
                return act(s, "defer", {"project": p["id"]}), "defer"
            return act(s, q["command"], q["args"]), "decide"
        if p["status"] == "problem" or not q:
            return act(s, "terminate", {"project": p["id"]}), "stop"
        # 主按钮暂时用不了（多半是人都在忙）：暂缓，等有人空出来再看
        waiting[p["id"]] = ("people", 0, s["week"])
        return act(s, "defer", {"project": p["id"]}), "defer"
    for p in v["projects"]:
        # 暂缓的项目：界面上一旦出现可用的主按钮（人空出来、钱够了）就点它
        q = p["quick"]
        affordable = q and (q["command"] == "launch" or not q["cost"] or (cash - q["cost"] >= RESERVE and not tight))
        if p["active"] and p["deferred"] and q and q["ok"] and affordable:
            return act(s, q["command"], q["args"]), "resume"
    assignments = [
        {"order": k, "character": x["hero"]} for k, x in v["assist"]["services"].items() if x["hero"] and not x["note"]
    ]
    if assignments and cash > 100:
        out = act(s, "take_services", {"assignments": assignments[:3]})
        if out:
            return out, "service"
    for h in v["heroes"]:
        if (
            h["rank"] < 4
            and not h["busy"]
            and all(c["ok"] for c in h["promotion"])
            and cash - h["promotion_cost"] > RESERVE
        ):
            out = act(s, "promote", {"character": h["id"]})
            if out:
                return out, "promote"
    if tight:
        # 现金为负时减少团队成员（每人每周省 ¥0.42 万），其余等服务回款
        if cash < 0 or v["cash"] < 0:
            for h in v["heroes"]:
                if not h["busy"] and h["members"] > 0:
                    out = act(s, "resize", {"character": h["id"], "members": 0})
                    if out:
                        return out, "cut"
        return advance(s, waiting), "next"
    active = [p for p in v["projects"] if p["active"]]
    if len(active) < (1 if s["week"] < 96 else 2):
        kinds = ["improved", "generic"]
        if appetite == "bold" and cash > 2500:
            kinds = ["innovative", *kinds]
        for kind in kinds:
            team = v["assist"]["screen"][kind]
            if not team:
                continue
            for c in v["catalog"]:
                if c["kind"] == kind and c["unlocked"] and not c["occupied"]:
                    out = act(s, "start_project", {"catalog": c["key"], "heroes": team})
                    if out:
                        return out, "start"
    if cash > 2000:
        for c in sorted(v["roster"], key=lambda c: c["cost"]):
            flow = v["weekly_profit"] + v["weekly_royalty"] - v["costs_per_week"] - c["weekly_salary"]
            if c["unlocked"] and (c["tier"] < 3 or c["connected"]) and cash - c["cost"] > 1500 and cash + flow * 52 > 0:
                out = act(s, "hire", {"character": c["key"]})
                if out:
                    return out, "hire"
    nf = v["next_facility"]
    if nf and cash > nf["cost"] * 2:
        out = act(s, "upgrade", {})
        if out:
            return out, "upgrade"
    for r in v["equipment"]:
        if r["cost"] and r["available"] and cash > r["cost"] * 3:
            out = act(s, "upgrade_equipment", {"profession": r["profession"]})
            if out:
                return out, "equipment"
    h = v["honors"]
    if not h["entry"] and 30 <= s["week"] % 48 < 46:
        choices = [c for c in h["categories"] if c["eligible"]]
        if choices:
            best = max(choices, key=lambda c: c["score"] - c["benchmark"])
            out = act(s, "nominate", {"category": best["key"]})
            if out:
                return out, "nominate"
    return advance(s, waiting), "next"


def advance(s, waiting):
    """按「下一件事」；还有没处理的决定时，先把它们暂缓（界面上同样要求先处理或暂缓）。"""
    try:
        return g.execute(s, "next_event", {"batches": 0})
    except ValueError:
        for p in s["projects"]:
            if p["status"] in DECIDE and not p.get("deferred"):
                waiting[p["id"]] = ("people", 0, s["week"])
                s = g.execute(s, "defer", {"project": p["id"]})
        return g.execute(s, "next_event", {"batches": 0})


def play(seed, appetite, weeks, mode):
    s = new_game(seed, "foundation", mode)
    counts = {}
    first = {}
    stops = []
    waiting = {}
    since_time = 0
    for _ in range(20000):
        if s["week"] >= weeks or s["game_over"]:
            break
        before = s["week"]
        out, kind = step(s, appetite, waiting)
        # 同一周里连着做了很多事还没推进时间，说明在原地打转：先推进时间
        since_time = since_time + 1 if out is not None and out["week"] == before else 0
        if out is None or since_time > 12:
            out, kind, since_time = advance(s, waiting), "next", 0
        s = out
        counts[kind] = counts.get(kind, 0) + 1
        if kind == "next":
            stops.append(s["week"] - before)
        for d in s["products"]:
            first.setdefault(d["kind"], s["week"])
    else:
        raise RuntimeError("default player stalled")
    years = max(1, s["week"] / 48)
    report = e.report(s)
    return s, {
        "weeks": s["week"],
        "actions": counts,
        "decisions_per_year": round(counts.get("decide", 0) / years, 1),
        "other_actions_per_year": round(sum(n for k, n in counts.items() if k not in ("next", "decide")) / years, 1),
        "next_per_year": round(counts.get("next", 0) / years, 1),
        "weeks_per_next": round(sum(stops) / max(1, len(stops)), 1),
        "longest_next": max(stops or [0]),
        "first_product": first,
        "products": {k: sum(d["kind"] == k for d in s["products"]) for k in ("generic", "improved", "innovative")},
        "heroes": len([h for h in s["heroes"] if h["employed"]]),
        "max_rank": max(h["rank"] for h in s["heroes"]),
        "facility": s["facility"],
        "cash": round(s["cash"]),
        "minimum_cash": round(s["minimum_cash"]),
        "awards": len(s.get("awards", [])),
        "score": report["score"],
        "bankrupt": s["game_over"],
    }


def task(job):
    seed, appetite, weeks, mode, output = job
    s, metrics = play(seed, appetite, weeks, mode)
    if seed <= 2:
        (output / f"{mode}-{appetite}-{seed}.json").write_text(dumps(s))
    return {"mode": mode, "appetite": appetite, "seed": seed, **metrics}


def summary(rows):
    def mean(key):
        return round(sum(r[key] for r in rows) / len(rows), 1)

    return {
        "runs": len(rows),
        "bankrupt": sum(r["bankrupt"] for r in rows),
        "cash_median": sorted(r["cash"] for r in rows)[len(rows) // 2],
        "minimum_cash_low": min(r["minimum_cash"] for r in rows),
        "decisions_per_year": mean("decisions_per_year"),
        "other_actions_per_year": mean("other_actions_per_year"),
        "next_per_year": mean("next_per_year"),
        "weeks_per_next": mean("weeks_per_next"),
        "longest_next": max(r["longest_next"] for r in rows),
        "generic": mean_of(rows, "generic"),
        "improved": mean_of(rows, "improved"),
        "innovative": mean_of(rows, "innovative"),
        "first_product_week": sorted(r["first_product"].get("generic", 9999) for r in rows)[len(rows) // 2],
        "max_rank": mean("max_rank"),
        "heroes": mean("heroes"),
        "awards": mean("awards"),
        "score": mean("score"),
    }


def mean_of(rows, kind):
    return round(sum(r["products"][kind] for r in rows) / len(rows), 2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=12)
    parser.add_argument("--weeks", type=int, default=960)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--output", type=Path, default=Path(".artifacts/v10-study"))
    parser.add_argument("--appetites", nargs="*", default=["cautious", "bold"])
    parser.add_argument("--modes", nargs="*", default=["standard", "competition"])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    jobs = [
        (seed, appetite, args.weeks, mode, args.output)
        for mode in args.modes
        for appetite in args.appetites
        for seed in range(1, args.seeds + 1)
    ]
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        rows = list(pool.map(task, jobs))
    (args.output / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    table = {}
    for mode in args.modes:
        for appetite in args.appetites:
            group = [r for r in rows if r["mode"] == mode and r["appetite"] == appetite]
            table[f"{mode}/{appetite}"] = summary(group)
            print(mode, appetite, json.dumps(table[f"{mode}/{appetite}"], ensure_ascii=False))
    (args.output / "summary.json").write_text(json.dumps(table, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
