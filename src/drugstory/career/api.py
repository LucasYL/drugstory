"""Version 1 public transport: static content once, dynamic decisions on each action."""

from .content import CATALOG, EXPERIMENTS, KINDS, PROFESSIONS, SCENARIOS, STATS
from .development import FOCUSES
from .product_design import profile

STATIC_FIELDS = ("scenarios", "professions", "stats", "experiments", "work_focuses")
CATALOG_FIELDS = ("key", "competition", "announced_rivals", "requirements", "unlocked", "occupied", "discovery")


def content():
    from .engine import catalog_requirements
    from .model import new_game

    opening = new_game()
    return {
        "api_version": 1,
        "content_version": "0.7.0",
        "scenarios": SCENARIOS,
        "professions": PROFESSIONS,
        "stats": STATS,
        "experiments": EXPERIMENTS,
        "work_focuses": FOCUSES,
        "catalog": [
            {
                **{k: v for k, v in c.items() if k not in ("combo_tier", "combo_reason")},
                "product_profile": profile(key),
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
