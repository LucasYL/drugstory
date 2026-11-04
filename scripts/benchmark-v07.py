"""Paired team boundary experiment. Unlimited financing here is NOT an economy playtest."""

import argparse
import copy
import json
from pathlib import Path

from drugstory.career import engine as g
from drugstory.career import science as sc
from drugstory.career.content import CATALOG, PATHS
from drugstory.career.model import make_hero, new_game
from drugstory.career.view import recommended_team


def source(seed, catalog):
    s = new_game(seed)
    s["heroes"] = [make_hero(k) for k in ("sprout", "beaker", "bubble", "pill", "ruler")]
    s["cash"] = s["capital"] = 100000
    s["facility"] = 3
    s["knowledge"] = dict.fromkeys(s["knowledge"], 100)
    s["equipment"] = dict.fromkeys(s["equipment"], 2)
    # Unlock fixture, then normalize team after the SAME candidate draw for every rank.
    for h in s["heroes"]:
        h.update(rank=3, training=25)
    g.start_project(s, catalog, ["sprout", "beaker"])
    g.advance(s, 48)
    p = s["projects"][0]
    scores = []
    for i in range(len(p["candidates"])):
        probe = copy.copy(p)
        probe["chosen"] = i
        scores.append(sc.outlook(probe))
    g.choose_candidate(s, "1", scores.index(max(scores)))
    s["equipment"] = dict.fromkeys(s["equipment"], 0)
    return s


def run(s, rank, members):
    s = copy.deepcopy(s)
    for h in s["heroes"]:
        h.update(rank=rank, base={1: 35, 2: 58, 4: 90}[rank], tier=rank, training=0, xp=0, members=members)
    for _ in range(60):
        p = s["projects"][0]
        if p["status"] in ("failed", "problem"):
            return {"pass": False, "weeks": s["week"] - 8}
        if p["status"] == "result":
            if sc.stage_key(p) == "review":
                return {"pass": True, "weeks": s["week"] - 8}
            g.continue_project(s, "1")
        elif p["status"] == "ready":
            ids, mode = recommended_team(s, p)
            g.run_phase(s, "1", ids, mode=mode)
        elif p["status"] == "checkpoint":
            g.trial_decision(s, "1", "keep")
        else:
            g.advance(s, 48)
    raise RuntimeError("phase stalled")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=400)
    parser.add_argument("--output", type=Path, default=Path(".artifacts/v07-benchmark.json"))
    args = parser.parse_args()
    rows = []
    for catalog in ("n_lung", "n_resistance"):
        bases = [source(i, catalog) for i in range(1, args.seeds + 1)]
        for rank, members in ((1, 2), (2, 2), (4, 2), (4, 0), (4, 6)):
            results = [run(s, rank, members) for s in bases]
            row = {
                "catalog": catalog,
                "tier": CATALOG[catalog]["combo_tier"],
                "rank": rank,
                "members": members,
                "n": args.seeds,
                "approved": sum(r["pass"] for r in results),
                "finished_weeks": [r["weeks"] for r in results if r["pass"]],
                "nominal_path_weeks": sum(
                    sc.plan_phase(bases[0], bases[0]["projects"][0], [], key=k)["weeks"] for k in PATHS["innovative"]
                ),
            }
            rows.append(row)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2))
            print({k: v for k, v in row.items() if k != "finished_weeks"}, flush=True)


if __name__ == "__main__":
    main()
