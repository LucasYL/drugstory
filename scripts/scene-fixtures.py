"""Generate reproducible UI checkpoints through normal play, without funding or hidden-value selection."""

import importlib.util
import json
from pathlib import Path

from drugstory.career.model import dumps, new_game
from drugstory.career.view import snapshot

spec = importlib.util.spec_from_file_location("study", Path("scripts/playtest-v08.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
out = Path(".artifacts/scene-fixtures")
out.mkdir(parents=True, exist_ok=True)
s = new_game(1, "independent", "standard")
seen = {}
for _ in range(7000):
    v = snapshot(s)
    conditions = {
        "license": any(p["status"] == "result" and p["quotes"] for p in v["projects"]),
        "interim": any(p["status"] == "checkpoint" and p["key"] == "II" for p in v["projects"]),
        "personal": any(
            h["personal_project"]["unlocked"]
            and not h["personal_project"]["done"]
            and h["personal_project"]["partners"]
            and not h["busy"]
            for h in v["heroes"]
        ),
        "expansion": v["facility"]["level"] == 2
        and v["next_facility"]
        and v["available_cash"] >= v["next_facility"]["cost"],
    }
    for k, ready in conditions.items():
        if ready and k not in seen:
            (out / f"{k}.json").write_text(dumps(s))
            seen[k] = {"week": s["week"], "cash": s["cash"], "commands": len(s["actions"])}
            print(k, seen[k], flush=True)
    if len(seen) == 4 or s["week"] >= 960 or s["game_over"]:
        break
    s = module.policy(s, "prestige", 960 - s["week"])
(out / "manifest.json").write_text(json.dumps(seen, ensure_ascii=False, indent=2))
