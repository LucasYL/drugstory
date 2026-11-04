"""Reach UI checkpoints through ordinary player actions; never edit cash or drug properties."""

from pathlib import Path

from drugstory.career import economy as e
from drugstory.career import science as sc
from drugstory.career.bot import choose
from drugstory.career.content import ROSTER
from drugstory.career.model import ability, busy, dumps, new_game

out = Path(".artifacts/v04-ui-checkpoints")
out.mkdir(parents=True, exist_ok=True)
found = set()
for seed in range(1, 4):
    for scenario in ("licensing", "foundation", "independent"):
        s = new_game(seed, scenario)
        for _ in range(4000):
            candidates = {}
            for p in s["projects"]:
                if p["status"] == "result" and e.quote(s, p, "codevelop"):
                    candidates["authorization"] = p["id"]
                if p["kind"] == "improved" and p["status"] == "result" and sc.stage_key(p) == "review":
                    candidates["improved-launch"] = p["id"]
                if p["kind"] == "innovative" and p["status"] == "failed" and s["cash"] > 800:
                    candidates["failure-recovery"] = p["id"]
            for key, spec in ROSTER.items():
                if (
                    spec["tier"] == 4
                    and all(ok for _, ok in e.recruit_requirements(s, key))
                    and (
                        any(
                            h["employed"]
                            and h["profession"] == spec["profession"]
                            and h["id"] not in busy(s)
                            and ability(h) >= 45
                            for h in s["heroes"]
                        )
                        and s["cash"] > 3000
                    )
                ):
                    candidates["legend-recruitment"] = key
            for kind, target in candidates.items():
                if kind not in found:
                    (out / f"{kind}.json").write_text(dumps(s))
                    print(kind, "seed", seed, scenario, "week", s["week"], "target", target, flush=True)
                    found.add(kind)
            if len(found) == 4 or s["week"] >= 960 or s["game_over"]:
                break
            s = choose(s, remaining=960 - s["week"])
        if len(found) == 4:
            break
    if len(found) == 4:
        break
if len(found) != 4:
    raise RuntimeError(f"Only reached {sorted(found)}")
