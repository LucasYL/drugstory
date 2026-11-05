"""Four independent batches with fixed information; no post-data reroll or endpoint changes."""

import math

from . import events
from .content import BUILD, STAGES, STATS
from .model import rand
from .units import pts, pts_map


def initialize(p):
    e = p["execution"]
    e["batches"] = []
    e["batch_count"] = 1 if e["key"] in BUILD else 4


def tick(s, p):
    from .science import limits, selected, update_belief

    e = p["execution"]
    key = e["key"]
    if p.get("experiment") or key in BUILD:
        return
    elapsed = e["weeks"] - p["left"]
    due = min(e["batch_count"], int(elapsed * e["batch_count"] / e["weeks"]))
    while len(e["batches"]) < due:
        index = len(e["batches"])
        c = selected(p)
        values = {}
        sigmas = {}
        for stat in limits(p, key):
            sigma = e["noise_by_stat"][stat] * math.sqrt(e["batch_count"])
            offset = c["subgroup"] if p.get("population") == "focused" and stat == "effect" else 0
            value = (
                c["truth"][stat]
                + offset
                + rand(s, "batch", p["id"], c["id"], key, p["repairs"], index, stat).gauss(0, sigma)
            )
            update_belief(c, stat, value - offset, sigma)
            values[stat] = value
            sigmas[stat] = sigma
        batch = {"index": index + 1, "week": s["week"], "values": values, "sigma": sigmas}
        e["batches"].append(batch)
        p.setdefault("readings", []).append({"stage": key, "candidate": c["id"], **batch})
        stage_limits = limits(p, key)
        events.emit(
            s,
            "evidence_received",
            project=p["id"],
            actors=p["team"],
            room=STAGES[key]["room"],
            data={
                "name": p["name"],
                "stage": STAGES[key]["name"],
                "batch": index + 1,
                "values": pts_map(values),
                "limits": pts_map(stage_limits),
                "margins": {k: pts(v - stage_limits[k]) for k, v in values.items()},
                "executor": p.get("mode", "internal"),
                "detail": "、".join(f"{STATS[k]} {pts(v)}（门槛 {pts(stage_limits[k])}）" for k, v in values.items()),
                "final": index + 1 == e["batch_count"],
            },
        )


def aggregate(p):
    e = p["execution"]
    if len(e["batches"]) != e["batch_count"]:
        raise ValueError("阶段证据尚未收齐")
    return {stat: sum(b["values"][stat] for b in e["batches"]) / e["batch_count"] for stat in e["noise_by_stat"]}


def forecast(p):
    """Conditional chance for fixed final mean, not pretending interim data are independent twice."""
    from .science import NORMAL, limits, selected

    e = p.get("execution", {})
    batches = e.get("batches", [])
    if not batches or len(batches) >= e["batch_count"]:
        return None
    c = selected(p)
    k = e["batch_count"]
    n = len(batches)
    left = k - n
    prob = 1
    for stat, limit in limits(p, e["key"]).items():
        b = c["belief"][stat]
        offset = c["marker"]["mean"] if p.get("population") == "focused" and stat == "effect" else 0
        past = sum(x["values"][stat] for x in batches)
        mean = (past + left * (b["mean"] + offset)) / k
        variance = (left / k) ** 2 * b["variance"] + left * e["noise_by_stat"][stat] ** 2 / k
        if offset:
            variance += (left / k) ** 2 * c["marker"]["variance"]
        prob *= 1 - NORMAL.cdf((limit - mean) / math.sqrt(variance))
    return prob
