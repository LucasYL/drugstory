"""Public-evidence strategies across both v6 modes. Player saves are never loaded."""

import argparse
import json
import runpy
from collections import Counter
from pathlib import Path

from drugstory.career import challenge, product_design, stories
from drugstory.career import economy as e
from drugstory.career import engine as g
from drugstory.career.model import busy, committed, dumps, new_game

BASE = runpy.run_path(str(Path(__file__).with_name("playtest-v05.py")))
BASE_POLICY = BASE["policy"]
STYLES = BASE["STYLES"]
MODE = "standard"


def policy(s, style, remaining):
    cash = s["cash"] - committed(s)
    for p in s["projects"]:
        if p["status"] == "checkpoint":
            key = p["execution"]["key"]
            choice = "keep"
            if cash > 1800 and style in ("steady", "academy", "prestige"):
                choice = {
                    "I": "monitor",
                    "II": "representative",
                    "III": "audit",
                    "bridge": "support",
                    "confirm": "support",
                }[key]
            if style == "rush":
                choice = "regional" if key == "II" else "remote" if key == "III" and cash > 1800 else "keep"
            return g.execute(s, "trial_decision", {"project": p["id"], "choice": choice})
    if challenge.enabled(s) and s["facility"]:
        target = "lean" if cash < 3500 else "frontier" if style == "prestige" and cash > 10000 else "balanced"
        if s["platform_policy"] != target:
            return g.execute(s, "platform_policy", {"policy_name": target})
    if cash > (1500 if style == "academy" else 2500):
        for h in s["heroes"]:
            if not h["employed"] or h["id"] in busy(s):
                continue
            q = stories.options(s, h)
            if q["unlocked"] and not q["done"] and not q["running"] and q["partners"]:
                return g.execute(
                    s,
                    "personal_project",
                    {
                        "character": h["id"],
                        "partner": q["partners"][0],
                        "choice": "handoff" if style in ("generics", "royalty") else "verify",
                    },
                )
    out = BASE_POLICY(s, style, remaining)
    action = out["actions"][-1]
    if (
        action["command"] == "start_project"
        and cash > 1600
        and style in ("generics", "academy", "steady")
        and product_design.profile(action["args"]["catalog"])
    ):
        return g.execute(s, "start_project", {**action["args"], "design": "validated"})
    return out


def play(seed, style, weeks=960, mode="standard"):
    globals_for_play = BASE["play"].__globals__
    globals_for_play["policy"] = policy
    globals_for_play["new_game"] = lambda seed, scenario: new_game(seed, scenario, mode)
    s, metrics = BASE["play"](seed, style, weeks)
    quests = [h["personal"] for h in s["heroes"] if h.get("personal")]
    trial_counts = Counter(c["choice"] for c in (a["args"] for a in s["actions"] if a["command"] == "trial_decision"))
    metrics.update(
        personal_completed=len(quests),
        personal_first=min((q["week"] for q in quests), default=None),
        trial_choices=dict(trial_counts),
        validated_products=sum(bool(d.get("design_reward")) for d in s["products"]),
        upkeep=round(s["expense"].get("platform_maintenance", 0)),
        mode=mode,
    )
    return s, metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=6)
    parser.add_argument("--weeks", type=int, default=960)
    parser.add_argument("--output", type=Path, default=Path(".artifacts/v06-study"))
    parser.add_argument("--styles", nargs="*", default=list(STYLES))
    parser.add_argument("--modes", nargs="*", default=["standard", "competition"])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rows = []
    for mode in args.modes:
        for style in args.styles:
            group = []
            for seed in range(1, args.seeds + 1):
                s, metrics = play(seed, style, args.weeks, mode)
                row = {"mode": mode, "style": style, "seed": seed, **e.report(s), **metrics}
                rows.append(row)
                group.append(row)
                if seed <= 2:
                    (args.output / f"{mode}-{style}-{seed}.json").write_text(dumps(s))
            (args.output / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
            print(
                mode,
                style,
                "runs",
                len(group),
                "bankrupt",
                sum(r["bankrupt"] for r in group),
                "goals",
                sum(r["objective"] for r in group),
                "quests",
                sum(r["personal_completed"] for r in group),
                flush=True,
            )


if __name__ == "__main__":
    main()
