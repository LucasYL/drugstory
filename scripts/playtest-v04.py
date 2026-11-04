"""Four routes × the same seeds × two operator policies, without injected resources."""

import argparse
import json
import sys
from pathlib import Path

from drugstory.career.bot import play
from drugstory.career.content import SCENARIOS
from drugstory.career.economy import report
from drugstory.career.model import dumps

parser = argparse.ArgumentParser()
parser.add_argument("--seeds", type=int, default=100)
parser.add_argument("--weeks", type=int, default=960)
parser.add_argument("--output", type=Path, default=Path(".artifacts/v04-sim"))
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
rows = []
for scenario in SCENARIOS:
    for novice in (True, False):
        group = []
        for seed in range(1, args.seeds + 1):
            s = play(seed, scenario, novice, args.weeks)
            row = {"scenario": scenario, "novice": novice, "seed": seed, **report(s)}
            bins = {}
            for project in s["projects"]:
                for phase in project["results"]:
                    probability = phase.get("probability")
                    if probability is None:
                        continue
                    label = project["kind"] + ":" + phase["key"] + ":" + str(min(9, int(probability * 10)))
                    b = bins.setdefault(label, {"count": 0, "predicted": 0.0, "passed": 0})
                    b["count"] += 1
                    b["predicted"] += probability
                    b["passed"] += phase["passed"]
            row["calibration"] = bins
            rows.append(row)
            group.append(row)
            if seed <= 3:
                (args.output / f"{scenario}-{'novice' if novice else 'skilled'}-{seed}.json").write_text(dumps(s))
        print(
            scenario,
            "novice" if novice else "skilled",
            "bankrupt",
            sum(r["bankrupt"] for r in group),
            "goals",
            sum(r["objective"] for r in group),
            "innovative",
            sum(r["approvals"]["innovative"] for r in group),
            "failed",
            sum(r["failures"] for r in group),
            flush=True,
        )
        (args.output / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
sys.stdout.flush()
