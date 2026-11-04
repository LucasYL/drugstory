"""Versioned authored data and a single generated innovation catalogue."""

import json
from pathlib import Path

DATA = Path(__file__).with_name("data")
_RULES = json.loads((DATA / "rules.json").read_text())
PROFESSIONS = _RULES["PROFESSIONS"]
STATS = _RULES["STATS"]
RANKS = _RULES["RANKS"]
SKILLS = _RULES["SKILLS"]
SCENARIOS = _RULES["SCENARIOS"]
ROSTER = _RULES["ROSTER"]
FACILITIES = _RULES["FACILITIES"]
CATALOG = _RULES["CATALOG"]
KINDS = _RULES["KINDS"]
PATHS = _RULES["PATHS"]
STAGES = _RULES["STAGES"]
PLANS = _RULES["PLANS"]
EXPERIMENTS = _RULES["EXPERIMENTS"]
TERMS = _RULES["TERMS"]
PROMOTION = _RULES["PROMOTION"]
RANKS = {int(k): v for k, v in RANKS.items()}
PROMOTION = {int(k): v for k, v in PROMOTION.items()}
CLINICAL = {"I", "II", "III", "bridge", "confirm", "be"}
COMBINATIONS = json.loads((DATA / "combinations.json").read_text())
TARGETS = {t["key"]: t for t in COMBINATIONS["targets"]}
MODALITIES = {m["key"]: m for m in COMBINATIONS["modalities"]}
PRESETS = {
    ("egfr", "small_molecule"): "n_lung",
    ("jak", "small_molecule"): "n_inflammation",
    ("pcsk9", "mab"): "n_lipid",
    ("kras", "degrader"): "n_resistance",
    ("tnf", "bispecific"): "n_reset",
    ("lpa", "sirna"): "n_rna",
}
MARKET_MAP = {
    "solid_tumor": "lung",
    "heme": "blood",
    "metabolic": "sugar",
    "lipid": "lipid",
    "neuro": "neuro",
    "migraine": "pain",
    "rare": "rare",
    "autoimmune": "inflammation",
    "vaccine": "infection",
    "antiviral": "infection",
}
for pair in COMBINATIONS["combinations"]:
    t, m = TARGETS[pair["target_id"]], MODALITIES[pair["modality_id"]]
    key = PRESETS.get((t["key"], m["key"]), f"n_{t['key']}__{m['key']}")
    old = CATALOG.get(key, {})
    hard = int(t["difficulty"] >= 1.25 or m["unlock"] >= 150 or old.get("difficulty", 0) > 0)
    CATALOG[key] = {
        "key": key,
        "name": t["name"] + " × " + m["name"],
        "kind": "innovative",
        "indication": t["disease"],
        "market": MARKET_MAP[t["category"]],
        "target": t["name"],
        "modality": m["name"],
        "target_id": t["key"],
        "modality_id": m["key"],
        "description": "组合路线需要先研究适配性，再开发候选并取得临床证据。",
        "difficulty": hard,
        "threshold_bonus": max(4 * hard, round(max(0, t["difficulty"] - 0.9) * 8)),
        "knowledge": max(t["unlock"], m["unlock"]) // 6,
        "peak": old.get("peak", 100 + t["market"] * 18 + hard * 35),
        "available_week": 0,
        "combo_tier": pair["tier"],
        "combo_reason": pair["reason"],
        "equipment_level": 2 if m["unlock"] >= 220 else 1 if m["unlock"] >= 150 else 0,
    }
KINDS = dict(KINDS)
BUILD = {key for key, d in STAGES.items() if d["category"] == "build"}


def validate():
    assert len(ROSTER) == 20
    assert len(COMBINATIONS["combinations"]) == 288
    assert len([c for c in CATALOG.values() if c["kind"] == "innovative"]) == 288
    for c in CATALOG.values():
        assert c["kind"] in PATHS and c["peak"] > 0
    for stage in STAGES.values():
        assert stage["weeks"] > 0 and stage["cost"] > 0
        assert set(stage["roles"]) <= PROFESSIONS.keys()
        assert set(stage["limits"]) <= STATS.keys()


validate()
