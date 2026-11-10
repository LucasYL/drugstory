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
ROOMS = {room["id"]: room for room in _RULES["ROOMS"]}
COMMERCIAL = _RULES["COMMERCIAL"]
PATENT = _RULES["PATENT"]
EQUIPMENT_UPKEEP = _RULES["EQUIPMENT_UPKEEP"]
PROFESSION_ROOM = {prof: room["id"] for room in _RULES["ROOMS"] for prof in room["professions"]}
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

# 从病进入创新药：每种病的领域、一句患者的话，以及「研究界正在试的路线」。
# 主流路线只说是哪几种药物类型（适配档位 ≥ 1，没有就取档位 0），不公开档位本身；阿尔茨海默固定是单抗和 ASO。
DISEASES = json.loads((DATA / "diseases.json").read_text())
ROUTES = {}
for _t in COMBINATIONS["targets"]:
    _pairs = [x for x in COMBINATIONS["combinations"] if x["target_id"] == _t["key"]]
    _good = [x["modality_id"] for x in _pairs if x["tier"] >= 1] or [x["modality_id"] for x in _pairs if x["tier"] == 0]
    ROUTES[_t["key"]] = ["mab", "aso"] if _t["key"] == "abeta" else _good
CATALOG_BY_PAIR = {(c["target_id"], c["modality_id"]): k for k, c in CATALOG.items() if c.get("target_id")}


def stars(value, steps):
    """把难度或市场换成 1–5 颗星。"""
    return next((i + 1 for i, edge in enumerate(steps) if value <= edge), len(steps) + 1)


def validate():
    assert len(ROSTER) == 21
    assert set(DISEASES) == set(TARGETS) and all(v["area"] and v["quote"] for v in DISEASES.values())
    assert all(ROUTES[t] and all((t, m) in CATALOG_BY_PAIR for m in ROUTES[t]) for t in TARGETS)
    assert len(COMBINATIONS["combinations"]) == 288
    assert len([c for c in CATALOG.values() if c["kind"] == "innovative"]) == 288
    for c in CATALOG.values():
        assert c["kind"] in PATHS and c["peak"] > 0
    assert set(PROFESSION_ROOM) == set(PROFESSIONS)
    for hero in ROSTER.values():
        assert hero["name"] and hero["nickname"] and hero["bio"] and hero["look"]
    assert len({hero["name"] for hero in ROSTER.values()}) == len(ROSTER)
    for stage in STAGES.values():
        assert stage["room"] in ROOMS
        assert stage["weeks"] > 0 and stage["cost"] > 0
        assert set(stage["roles"]) <= PROFESSIONS.keys()
        assert set(stage["limits"]) <= STATS.keys()


validate()
