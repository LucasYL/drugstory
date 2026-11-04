"""Replay normal-operation recordings into isolated mouse-test checkpoints."""

import json
from pathlib import Path

from drugstory.career import engine as g
from drugstory.career.model import dumps, new_game

source = Path(".artifacts/v06-first/standard-steady-1.json")
recording = json.loads(source.read_text())
s = new_game(recording["seed"], recording["scenario"], recording["difficulty"])
out = Path(".artifacts/v06-checkpoints")
out.mkdir(parents=True, exist_ok=True)
found = set()
for action in recording["actions"]:
    project = next((p for p in s["projects"] if p["id"] == action["args"].get("project")), None)
    checks = {
        "personal": action["command"] == "personal_project",
        "trial": action["command"] == "trial_decision" and project["execution"]["key"] == "II",
        "next-stage": action["command"] == "continue_project" and project["kind"] == "generic",
    }
    for name, ready in checks.items():
        if ready and name not in found:
            (out / f"{name}.json").write_text(dumps(s))
            found.add(name)
            print(name, s["week"], flush=True)
    if len(found) == 3:
        break
    s = g.execute(s, action["command"], action["args"])
assert len(found) == 3, found
