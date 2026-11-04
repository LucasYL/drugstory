"""Reach award and research checkpoints by normal actions from a fresh seed."""

import runpy
from pathlib import Path

from drugstory.career import honors as h
from drugstory.career.model import dumps, new_game

policy = runpy.run_path(str(Path(__file__).with_name("playtest-v05.py")))["policy"]
out = Path(".artifacts/v05-checkpoints")
out.mkdir(parents=True, exist_ok=True)
s = new_game(1, "independent")
found = set()
for _ in range(7000):
    entries = h.categories(s)
    cases = {
        "nomination": 30 <= s["week"] % 48 < 46
        and not s["season"]["entry"]
        and any(c["eligible"] and c["score"] >= c["benchmark"] for c in entries),
        "ceremony": bool(s["season"]["entry"])
        and s["week"] % 48 >= 40
        and any(c["key"] == s["season"]["entry"] and c["eligible"] and c["score"] >= c["benchmark"] for c in entries),
        "independent-study": any(o["available"] for o in h.proof_options(s)),
        "grand-final": not h.legacy_progress(s)[0]["won"] and all(c["ok"] for c in h.legacy_progress(s)[0]["checks"]),
    }
    for key, ready in cases.items():
        if ready and key not in found:
            (out / (key + ".json")).write_text(dumps(s))
            found.add(key)
            print(key, "week", s["week"], flush=True)
    if len(found) == 4 or s["week"] >= 960 or s["game_over"]:
        break
    s = policy(s, "prestige", 960 - s["week"])
assert len(found) == 4, found
