"""难病的搭档关：每道关缺了谁会抬高门槛、加大噪声、拉长试验或减少需求；对的人在职就能完全或部分解决。

数据在 data/challenges.json：阿尔茨海默病是「最后的难题」（四道关），KRAS G12C、乙肝、Lp(a) 各三道。
都是公开规则，疾病卡直接列出每道关、研究所里谁能过、还有谁能过。
有的关在立项筛选时就定下（分子设计决定），后来请到谁也改不了；其余在每个阶段开工时按当时在职的人计算。
"""

from __future__ import annotations

import json

from . import talents
from .content import CATALOG, DATA

CHALLENGES = json.loads((DATA / "challenges.json").read_text())
TARGETS = set(CHALLENGES)
# 进不了脑的大分子（阿尔茨海默「入脑」）
LARGE = {"mab", "bispecific", "protein", "peptide", "adc", "gene_therapy", "sirna", "mrna", "cart"}
GATES = {
    g["key"]: {**g, "full": tuple(g["full"]), "partial": tuple(g["partial"])} for g in CHALLENGES["abeta"]["gates"]
}


def _gates(catalog):
    return CHALLENGES.get(CATALOG[catalog].get("target_id"), {}).get("gates", [])


def applies(catalog):
    return bool(_gates(catalog))


def _who(s, key, minimum):
    if key is None:
        return []
    return [h["name"] for h in s["heroes"] if h["employed"] and talents.level(h, key) >= minimum]


def _locked(g, modality, people_state):
    """立项时定下的关：由药物类型决定。"""
    if g["lock"] == "bbb":
        if modality in LARGE:
            return people_state if people_state == "full" else "none"
        return "partial" if modality == "aso" else "full"
    if g["lock"] == "cccdna":
        if modality not in ("sirna", "aso"):
            return "none"
        return "full" if people_state == "full" else "partial"
    return people_state


def status(s, catalog, p=None):
    """每道关的状态：full / partial / none，以及研究所里能过这道关的人。"""
    modality = CATALOG[catalog].get("modality_id")
    rows = {}
    for g in _gates(catalog):
        full_key, full_level, _ = g["full"]
        part_key, part_level, _ = g["partial"]
        full = _who(s, full_key, full_level)
        partial = _who(s, part_key, part_level)
        state = "full" if full else "partial" if partial else "none"
        if g.get("lock"):
            locked = (p or {}).get("gates", {}).get(g["key"])
            state = locked or _locked(g, modality, state)
        if g.get("focused") and state == "full" and p is not None and p.get("population") != "focused":
            state = "partial"
        rows[g["key"]] = {"state": state, "people": full or partial}
    return rows


def lock_design(s, p):
    """立项筛选时定下由分子设计决定的关。"""
    rows = status(s, p["catalog"])
    for g in _gates(p["catalog"]):
        if g.get("lock"):
            p.setdefault("gates", {})[g["key"]] = rows[g["key"]]["state"]


def _rows(s, p, partner):
    rows = status(s, p["catalog"], p)
    if partner:
        # 授权给合作方以后，合作方没有你的人；立项时定下的关不变
        locked = {g["key"] for g in _gates(p["catalog"]) if g.get("lock")}
        rows = {k: (v if k in locked else {**v, "state": "none"}) for k, v in rows.items()}
    return rows


def effects(s, p, key, partner=False):
    """这个阶段因搭档关产生的门槛调整、噪声和工期倍率。"""
    fx = {"limits": {}, "noise": 1.0, "weeks": 1.0}
    if not applies(p["catalog"]):
        return fx
    rows = _rows(s, p, partner)
    for g in _gates(p["catalog"]):
        state = rows[g["key"]]["state"]
        for e in g["effects"]:
            if key not in e.get("stages", []):
                continue
            value = e[state]
            if e["type"] == "limit" and value:
                fx["limits"][e["stat"]] = fx["limits"].get(e["stat"], 0) + value
            elif e["type"] == "noise":
                fx["noise"] *= value
            elif e["type"] == "weeks":
                fx["weeks"] *= value
    return fx


def peak_factor(s, p, partner=False):
    """上市需求的倍率（例如 Lp(a)「半年一针」）。"""
    if not applies(p["catalog"]):
        return 1.0
    rows = _rows(s, p, partner)
    factor = 1.0
    for g in _gates(p["catalog"]):
        for e in g["effects"]:
            if e["type"] == "peak":
                factor *= e[rows[g["key"]]["state"]]
    return factor


def view(s, catalog, p=None):
    if not applies(catalog):
        return None
    rows = status(s, catalog, p)
    return [
        {
            "key": g["key"],
            "name": g["name"],
            "problem": g["problem"],
            "missing": g["missing"],
            "full": g["full"][2],
            "partial": g["partial"][2],
            "state": rows[g["key"]]["state"],
            "people": rows[g["key"]]["people"],
            "title": CHALLENGES[CATALOG[catalog]["target_id"]]["title"],
        }
        for g in _gates(catalog)
    ]
