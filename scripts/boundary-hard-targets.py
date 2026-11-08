"""Boundary study on constructed late-game states (not normal play): who can make the hardest drugs?

Each run builds a fresh state: research institute, knowledge 100, ample cash, one person per listed
profession at a fixed rank. The evidence-only bot (``career.bot``) makes every project decision and
never reads candidate truth. Results are recorded separately from normal-play simulations.

    uv run python scripts/boundary-hard-targets.py --seeds 40
    uv run python scripts/boundary-hard-targets.py --catalog n_abeta__aso,n_lung --seeds 40
"""

import argparse
import collections

from drugstory.career import bot
from drugstory.career import engine as g
from drugstory.career import science as sc
from drugstory.career.assist import advice, recommended_team
from drugstory.career.content import CATALOG
from drugstory.career.model import DECISIONS, ability, make_hero, new_game

LEGENDS = ["star", "alchemist", "guardian", "architect", "oracle"]
JUNIORS = ["sprout", "beaker", "bubble", "pill", "ruler"]
MASTERS = ["bridge", "wizard", "judge", "forge", "strategist"]
GATE_FULL = ["bridge", "wizard", "guardian", "forge", "oracle"]
# name: (people, rank, training, equipment level, members per lead, novice decisions, awakened people)
TEAMS = {
    "五位传奇": (LEGENDS, 4, 40, 3, 6, False, []),
    "五位见习练到传奇": (JUNIORS, 4, 40, 3, 6, False, []),
    "五位见习练到大师": (JUNIORS, 3, 20, 3, 6, False, []),
    "大师·设备1级·小组3人": (JUNIORS, 3, 20, 1, 3, False, []),
    "大师·没有临床交CRO": (JUNIORS[:4], 3, 20, 3, 6, False, []),
    "大师·直接选候选不做专项研究": (JUNIORS, 3, 20, 3, 6, True, []),
    "四道关全靠大师（傅以宁觉醒）": (MASTERS, 3, 20, 3, 6, False, ["forge"]),
    "四道关完全解决（傅以宁觉醒）": (GATE_FULL, 3, 20, 3, 6, False, ["forge"]),
    "四道关全靠大师 + 分层打法": (MASTERS, 3, 20, 3, 6, "smart", ["forge"]),
    "四道关完全解决 + 分层打法": (GATE_FULL, 3, 20, 3, 6, "smart", ["forge"]),
    "五位见习练到精英": (JUNIORS, 2, 10, 3, 6, False, []),
}
FINAL = ("approved", "failed", "terminated", "licensed")


def build(seed, spec):
    people, rank, training, equipment, members, _, awake = spec
    s = new_game(seed)
    s.update(facility=3, cash=1e6)
    s["equipment"] = dict.fromkeys(s["equipment"], equipment)
    s["knowledge"] = dict.fromkeys(s["knowledge"], 100)
    s["heroes"] = []
    for key in people:
        h = make_hero(key)
        h.update(rank=max(rank, h["tier"]), training=training, xp=200, members=members)
        if key in awake:
            h["personal"] = {"choice": "practice"}
        s["heroes"].append(h)
    return s


def run(seed, spec, catalog):
    s = build(seed, spec)
    novice = spec[5]
    team = [h["id"] for h in s["heroes"] if h["profession"] in ("bio", "chem")]
    try:
        s = g.execute(s, "start_project", {"catalog": catalog, "heroes": team})
    except ValueError:
        return "不能立项", None
    for _ in range(400):
        p = s["projects"][0]
        if p["status"] in FINAL:
            return p["status"], p
        if p.get("deferred"):
            return "搁置", p
        if novice == "smart" and p["status"] == "ready":
            s = smart(s, p) or bot.choose(s, False)
        elif p["status"] in DECISIONS:
            s = bot.choose(s, novice is True)
        else:
            s = g.execute(s, "next_event", {"batches": 0})
    return "超时", s["projects"][0]


def smart(s, p):
    """研究顾问提示的打法：照顾问做人群分层研究，II 期起分层入组。只看公开证据。"""
    tip = next((t for t in advice(s, p) if t["kind"] == "marker" and t["ok"]), None)
    if tip:
        return g.execute(s, tip["command"], tip["args"])
    if sc.stage_key(p) == "II" and sc.focused_available(s, p):
        ids, mode = recommended_team(s, p)
        try:
            return g.execute(s, "run_phase", {"project": p["id"], "heroes": ids, "plan": "focused", "mode": mode})
        except ValueError:
            return None
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="n_abeta__mab,n_abeta__aso,n_abeta__small_molecule,n_lung")
    parser.add_argument("--seeds", type=int, default=40)
    args = parser.parse_args()
    for catalog in args.catalog.split(","):
        spec = CATALOG[catalog]
        print(f"== {spec['name']}（{spec['indication']}），种子 1–{args.seeds}")
        for name, team in TEAMS.items():
            outcomes, where = collections.Counter(), collections.Counter()
            for seed in range(1, args.seeds + 1):
                status, p = run(seed, team, catalog)
                outcomes[status] += 1
                if p and status in ("failed", "terminated") and p["results"]:
                    last = p["results"][-1]
                    where[f"{last['key']}:{'/'.join(last['failures']) or '止损'}"] += 1
            abilities = sorted({ability(h) for h in build(1, team)["heroes"]})
            print(f"  {name}  能力{abilities}  {dict(outcomes)}  {dict(where.most_common(3))}")


if __name__ == "__main__":
    main()
