"""汇总游玩记录（server.py 的 --playlog / --playlog-dir 写出的 JSON Lines）。

看真人玩家怎么玩：玩了几次、每次推进了多少游戏时间、最常用哪些操作、在哪儿停下。
只读记录文件，不碰存档。

    uv run python scripts/playlog-report.py saves/playlog/*.jsonl
"""

import argparse
import collections
import json
import statistics
from datetime import datetime, timedelta
from pathlib import Path

GAP = timedelta(minutes=30)


def sessions(rows):
    out, current, last = [], [], None
    for r in rows:
        t = datetime.fromisoformat(r["t"])
        if last is not None and t - last > GAP:
            out.append(current)
            current = []
        current.append(r)
        last = t
    if current:
        out.append(current)
    return out


def report(path):
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    if not rows:
        return {"file": str(path), "actions": 0}
    parts = sessions(rows)
    gaps = [
        (datetime.fromisoformat(b["t"]) - datetime.fromisoformat(a["t"])).total_seconds()
        for a, b in zip(rows, rows[1:], strict=False)
        if b["name"] == "next_event" and datetime.fromisoformat(b["t"]) - datetime.fromisoformat(a["t"]) <= GAP
    ]
    return {
        "file": str(path),
        "actions": len(rows),
        "errors": sum(not r["ok"] for r in rows),
        "sessions": len(parts),
        "years_per_session": [round((p[-1]["week"] - p[0]["week"]) / 48, 1) for p in parts],
        "minutes_per_session": [
            round((datetime.fromisoformat(p[-1]["t"]) - datetime.fromisoformat(p[0]["t"])).total_seconds() / 60, 1)
            for p in parts
        ],
        "last_action_of_session": [f"第 {p[-1]['week']} 周 {p[-1]['name']}" for p in parts],
        "commands": dict(collections.Counter(r["name"] for r in rows).most_common()),
        "common_errors": dict(collections.Counter(r["error"] for r in rows if r["error"]).most_common(5)),
        "seconds_before_next_event_median": round(statistics.median(gaps), 1) if gaps else None,
        "reached_week": rows[-1]["week"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", type=Path, nargs="+")
    for path in parser.parse_args().files:
        print(json.dumps(report(path), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
