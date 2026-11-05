"""Version 2 public transport: static content (rooms, cast, catalog) once, dynamic state on each action."""

from .content import CATALOG, EXPERIMENTS, KINDS, PROFESSIONS, ROOMS, ROSTER, SCENARIOS, STAGES, STATS
from .development import FOCUSES
from .units import SCALE
from .view import shown_profile

STATIC_FIELDS = ("scenarios", "professions", "stats", "experiments", "work_focuses")
CATALOG_FIELDS = ("key", "competition", "announced_rivals", "requirements", "unlocked", "occupied", "discovery")


def content():
    from .engine import catalog_requirements
    from .model import new_game

    opening = new_game()
    return {
        "api_version": 2,
        "content_version": "0.8.0",
        "display_scale": SCALE,
        "rooms": [
            {**room, "stages": [k for k, st in STAGES.items() if st["room"] == room["id"]]} for room in ROOMS.values()
        ],
        "roster": [
            {k: c[k] for k in ("key", "name", "nickname", "profession", "tier", "story", "bio", "look")}
            for c in ROSTER.values()
        ],
        "scenarios": SCENARIOS,
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
