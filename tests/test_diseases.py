"""v0.12：创新药先选病，再从主流路线里选。只公开药物类型，不公开适配档位。"""

import json

from drugstory.career import api
from drugstory.career.content import CATALOG, DISEASES, ROUTES, TARGETS


def test_every_disease_has_area_quote_and_routes():
    assert set(DISEASES) == set(TARGETS) and len(DISEASES) == 24
    for key, d in DISEASES.items():
        assert d["area"] and d["quote"]
        assert ROUTES[key]


def test_alzheimer_routes_are_antibody_and_aso():
    assert ROUTES["abeta"] == ["mab", "aso"]


def test_routes_point_to_real_catalog_entries():
    for t in api.content()["targets"]:
        for r in t["routes"]:
            assert CATALOG[r["key"]]["target_id"] == t["key"]
            assert CATALOG[r["key"]]["modality_id"] == r["modality"]
            assert r["years"] > 0 and r["cost"] > 0


def test_static_targets_do_not_leak_fit_tiers():
    text = json.dumps(api.content()["targets"], ensure_ascii=False)
    assert "tier" not in text and "reason" not in text
    for t in api.content()["targets"]:
        assert 1 <= t["difficulty_stars"] <= 5 and 2 <= t["market_stars"] <= 5
