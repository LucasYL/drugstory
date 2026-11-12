"""Version 2 public transport: static content (rooms, cast, catalog) once, dynamic state on each action."""

from .content import (
    CATALOG,
    CATALOG_BY_PAIR,
    COMBINATIONS,
    DISEASES,
    EXPERIMENTS,
    KINDS,
    MODALITIES,
    PATHS,
    PROFESSIONS,
    ROOMS,
    ROSTER,
    ROUTES,
    SCENARIOS,
    STAGES,
    STATS,
    stars,
)
from .development import FOCUSES
from .units import SCALE
from .view import shown_profile

STATIC_FIELDS = ("scenarios", "professions", "stats", "experiments", "work_focuses")
CATALOG_FIELDS = (
    "key",
    "competition",
    "announced_rivals",
    "requirements",
    "unlocked",
    "occupied",
    "discovery",
    "gates",
    "outlook",
    "autopilot",
    "share_loss",
)


def targets():
    """疾病卡与主流路线（静态）。只给药物类型，不给适配档位。"""
    weeks = sum(STAGES[k]["weeks"] for k in PATHS["innovative"])
    base = sum(STAGES[k]["cost"] * (2 if k == "review" else 1) for k in PATHS["innovative"])
    out = []
    for t in COMBINATIONS["targets"]:
        rows = []
        for m in ROUTES[t["key"]]:
            key = CATALOG_BY_PAIR[(t["key"], m)]
            hard = CATALOG[key]["difficulty"]
            rows.append(
                {
                    "modality": m,
                    "name": MODALITIES[m]["name"],
                    "key": key,
                    "title": CATALOG[key]["name"],
                    "years": round(weeks / 48),
                    "cost": int(round(base * (1.2 if hard else 1), -2)),
                }
            )
        out.append(
            {
                "key": t["key"],
                "name": t["name"],
                "disease": t["disease"],
                "area": DISEASES[t["key"]]["area"],
                "quote": DISEASES[t["key"]]["quote"],
                "difficulty_stars": stars(t["difficulty"], (0.9, 1.0, 1.2, 1.4)),
                "market_stars": t["market"],
                "routes": rows,
            }
        )
    return out


def content():
    from .engine import catalog_requirements
    from .model import new_game

    opening = new_game()
    return {
        "api_version": 2,
        "content_version": "0.13.1",
        "display_scale": SCALE,
        "rooms": [
            {**room, "stages": [k for k, st in STAGES.items() if st["room"] == room["id"]]} for room in ROOMS.values()
        ],
        "roster": [
            {k: c[k] for k in ("key", "name", "nickname", "profession", "tier", "story", "bio", "look")}
            for c in ROSTER.values()
        ],
        "scenarios": SCENARIOS,
        "targets": targets(),
        "professions": PROFESSIONS,
        "stats": STATS,
        "experiments": EXPERIMENTS,
        "work_focuses": FOCUSES,
        "catalog": [
            {
                **{k: v for k, v in c.items() if k not in ("combo_tier", "combo_reason")},
                "product_profile": shown_profile(key),
                "kind_name": KINDS[c["kind"]],
                "requirement_labels": [text for text, _ in catalog_requirements(opening, key)],
            }
            for key, c in CATALOG.items()
        ],
    }


def state(view):
    return {
        **{k: v for k, v in view.items() if k not in STATIC_FIELDS and k != "catalog"},
        "catalog": [
            {
                **{k: row[k] for k in CATALOG_FIELDS if k != "requirements"},
                "requirements": [c["ok"] for c in row["requirements"]],
            }
            for row in view["catalog"]
        ],
    }
