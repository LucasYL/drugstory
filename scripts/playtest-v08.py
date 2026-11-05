"""Compare real operating choices, without injecting money or reading hidden drug truth."""

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from drugstory.career import economy as e
from drugstory.career import engine as g
from drugstory.career import readouts, stories
from drugstory.career.bot import attempt, choose
from drugstory.career.content import CATALOG, ROSTER
from drugstory.career.model import ability, busy, committed, dumps, new_game

STYLES = {
    "steady": ("foundation", "稳健综合"),
    "generics": ("foundation", "仿制与改良"),
    "royalty": ("licensing", "长期授权"),
    "rush": ("independent", "早押创新"),
    "academy": ("platform", "人物培养"),
    "prestige": ("independent", "突破大奖"),
    "explorer": ("independent", "组合探索"),
}


def idle_business(s, remaining):
    for offer in e.orders(s):
        if offer["taken"]:
            continue
        for h in s["heroes"]:
            if h["employed"] and h["id"] not in busy(s) and h["profession"] == offer["profession"]:
                out = attempt(s, "take_service", order=offer["id"], character=h["id"])
                if out:
                    return out
    return g.execute(s, "advance", {"weeks": 48 if remaining >= 48 else 4 if remaining >= 4 else 1})


def policy(s, style, remaining):
    cash = s["cash"] - committed(s)
    free = [h for h in s["heroes"] if h["employed"] and h["id"] not in busy(s)]
    if "nominate" in g.COMMANDS:
        from drugstory.career.honors import categories, proof_options

        if not s["season"]["entry"] and 30 <= s["week"] % 48 < 46:
            choices = [c for c in categories(s) if c["eligible"]]
            if choices:
                target = max(choices, key=lambda c: c["score"] - c["benchmark"])
                return g.execute(s, "nominate", {"category": target["key"]})
        if style in ("academy", "prestige") and cash > 3500:
            for option in proof_options(s):
                if option["available"]:
                    out = attempt(s, "independent_study", product=option["product"], heroes=option["recommended"])
                    if out:
                        return out
    if style in ("academy", "prestige") and cash > 1700:
        for teacher in sorted(free, key=lambda h: -h["rank"]):
            for pupil in free:
                if (
                    teacher["rank"] > pupil["rank"]
                    and teacher["rank"] >= 2
                    and teacher["profession"] == pupil["profession"]
                    and teacher["id"] not in pupil["mentored"]
                ):
                    return g.execute(s, "mentor", {"teacher": teacher["id"], "pupil": pupil["id"]})
    if style in ("academy", "prestige") and cash > 3000 and s["facility"] >= 1:
        for key, spec in ROSTER.items():
            if (
                spec["tier"] == 2
                and not any(h["id"] == key for h in s["heroes"])
                and any(h["profession"] == spec["profession"] and h["rank"] >= 3 for h in free)
            ):
                out = attempt(s, "hire", character=key)
                if out:
                    return out
    if cash > 1800:
        for h in free:
            q = stories.options(s, h)
            if q["unlocked"] and not q["done"] and not q["running"] and q["partners"]:
                return g.execute(
                    s, "personal_project", {"character": h["id"], "partner": q["partners"][0], "choice": "practice"}
                )
    if style != "rush":
        for p in s["projects"]:
            if p["status"] == "checkpoint" and (readouts.forecast(p) or 0) < 0.12:
                return g.execute(s, "trial_decision", {"project": p["id"], "choice": "stop"})
    if cash > 6000:
        for h in free:
            if h["members"] < min(4, 2 + h["rank"]):
                out = attempt(s, "resize", character=h["id"], members=min(4, 2 + h["rank"]))
                if out:
                    return out
    proposal = choose(s, remaining=remaining)
    action = proposal["actions"][-1]
    if action["command"] == "license_project" and style == "royalty":
        terms = "codevelop" if len(s["deals"]) % 3 == 2 and cash > 2000 else "royalty"
        return g.execute(s, "license_project", {**action["args"], "terms": terms})
    if style in ("academy", "prestige") and action["command"] == "run_phase":
        ids = action["args"]["heroes"]
        if len(ids) < 3:
            apprentices = [
                h
                for h in free
                if h["id"] not in ids
                and h["rank"] < 3
                and any(t["id"] in ids and t["profession"] == h["profession"] and t["rank"] > h["rank"] for t in free)
            ]
            if apprentices:
                return g.execute(s, "run_phase", {**action["args"], "heroes": ids + [apprentices[0]["id"]]})
    if action["command"] != "start_project":
        return proposal
    spec = CATALOG[action["args"]["catalog"]]
    if style == "academy" and cash > 1600:
        for h in free:
            if ability(h) < (60 if h["rank"] >= 2 else 42):
                out = attempt(s, "train", character=h["id"])
                if out:
                    return out
    if style == "explorer" and spec["kind"] == "innovative":
        candidates = [c for c in CATALOG.values() if c["kind"] == "innovative"]
        candidates.sort(key=lambda c: (c["key"] in s["notebook"], c["knowledge"], c["key"]))
    elif style == "generics" and spec["kind"] == "innovative":
        candidates = [c for c in CATALOG.values() if c["kind"] != "innovative"]
    elif style == "rush" and spec["kind"] != "innovative" and cash > 1100:
        candidates = [c for c in CATALOG.values() if c["kind"] == "innovative"]
    elif style == "prestige" and spec["kind"] == "innovative":
        candidates = sorted(
            [c for c in CATALOG.values() if c["kind"] == "innovative"],
            key=lambda c: (-c["difficulty"], sum(p["catalog"] == c["key"] for p in s["projects"])),
        )
    else:
        return proposal
    for c in candidates:
        roles = ("bio", "chem") if c["kind"] == "innovative" else ("proc", "chem")
        team = [h["id"] for h in free if h["profession"] in roles][:2]
        out = attempt(s, "start_project", catalog=c["key"], heroes=team)
        if out:
            return out
    return idle_business(s, remaining) if style == "generics" else proposal


def play(seed, style, weeks, mode="standard"):
    s = new_game(seed, STYLES[style][0], mode)
    times, years, unlocks = {}, [], {}
    idle_person_weeks = total_person_weeks = longest_gap = longest_event_gap = 0
    last_reward = last_event = 0
    big = {
        "product_launched",
        "award_won",
        "character_promoted",
        "patent_granted",
        "patent_expired",
        "milestone_reached",
        "facility_upgraded",
        "legacy_reached",
        "deal_signed",
    }
    event_counts = {}
    seen_event = 0
    for _ in range(7000):
        for tier in (2, 3, 4):
            if str(tier) not in unlocks and any(
                c["tier"] == tier and all(ok for _, ok in e.recruit_requirements(s, k)) for k, c in ROSTER.items()
            ):
                unlocks[str(tier)] = s["week"]
        for kind in ("generic", "improved", "innovative"):
            if kind not in times and any(p["kind"] == kind for p in s["products"]):
                times[kind] = s["week"]
        if s["week"] >= weeks or s["game_over"]:
            break
        old = s
        s = policy(s, style, weeks - s["week"])
        delta = s["week"] - old["week"]
        employed = [h for h in old["heroes"] if h["employed"]]
        total_person_weeks += delta * len(employed)
        idle_person_weeks += delta * sum(h["id"] not in busy(old) for h in employed)
        if (
            len(s["products"]) > len(old["products"])
            or len(s.get("awards", [])) > len(old.get("awards", []))
            or max(h["rank"] for h in s["heroes"]) > max(h["rank"] for h in old["heroes"])
        ):
            longest_gap = max(longest_gap, s["week"] - last_reward)
            last_reward = s["week"]
        happened = [ev for ev in s.get("events", []) if ev["id"] > seen_event and ev["type"] in big]
        seen_event = s.get("event_seq", 0)
        for ev in happened:
            event_counts[ev["type"]] = event_counts.get(ev["type"], 0) + 1
        if happened:
            longest_event_gap = max(longest_event_gap, s["week"] - last_event)
            last_event = s["week"]
        if s["week"] // 48 > old["week"] // 48:
            years.append(
                {
                    "year": s["week"] // 48,
                    "cash": round(s["cash"]),
                    "products": len(s["products"]),
                    "rank": max(h["rank"] for h in s["heroes"]),
                }
            )
    else:
        raise RuntimeError("policy stalled")
    longest_gap = max(longest_gap, s["week"] - last_reward)
    longest_event_gap = max(longest_event_gap, s["week"] - last_event)
    return s, {
        "first_products": times,
        "unlocks": unlocks,
        "years": years,
        "idle_fraction": round(idle_person_weeks / max(1, total_person_weeks), 3),
        "longest_reward_gap": longest_gap,
        "longest_event_gap": longest_event_gap,
        "big_events": event_counts,
        "patents": len([p for p in s["projects"] if (p.get("patent") or {}).get("granted")]),
        "characters": len(s["heroes"]),
        "awards": s.get("awards", []),
        "legacies": s.get("legacies", []),
        "proofs": s.get("proofs", []),
        "personal_completed": sum(bool(h.get("personal")) for h in s["heroes"]),
        "combinations": len(s["notebook"]),
        "equipment": s["equipment"],
        "readout_events": sum(ev["type"] == "evidence_received" for ev in s["events"]),
    }


def task(job):
    seed, style, weeks, mode, output = job
    s, metrics = play(seed, style, weeks, mode)
    if seed <= 2:
        (output / f"{mode}-{style}-{seed}.json").write_text(dumps(s))
    return {"mode": mode, "style": style, "seed": seed, **e.report(s), **metrics}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=6)
    parser.add_argument("--weeks", type=int, default=960)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--output", type=Path, default=Path(".artifacts/v08-study"))
    parser.add_argument("--styles", nargs="*", default=list(STYLES))
    parser.add_argument("--modes", nargs="*", default=["standard", "competition"])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    jobs = [
        (seed, style, args.weeks, mode, args.output)
        for mode in args.modes
        for style in args.styles
        for seed in range(1, args.seeds + 1)
    ]
    rows = []
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        for row in pool.map(task, jobs):
            rows.append(row)
            (args.output / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
            if row["seed"] == args.seeds:
                group = [r for r in rows if r["mode"] == row["mode"] and r["style"] == row["style"]]
                print(
                    row["mode"],
                    row["style"],
                    "runs",
                    len(group),
                    "bankrupt",
                    sum(r["bankrupt"] for r in group),
                    "goals",
                    sum(r["objective"] for r in group),
                    flush=True,
                )


if __name__ == "__main__":
    main()
