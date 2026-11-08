"""最后的难题：阿尔茨海默病的四道关。

每道关都是公开规则：缺了会抬高门槛、加大噪声或拉长试验；研究所里有对应专长的人（在职即可）
就能完全或部分解决。疾病卡上直接列出四道关、你的团队里谁能过，以及还有谁能过。
「入脑」在立项筛选时定下（分子设计决定），其余三关在每个阶段开工时按当时在职的人计算。
"""

from __future__ import annotations

from . import talents
from .content import CATALOG

TARGETS = {"abeta"}
LARGE = {"mab", "bispecific", "protein", "peptide", "adc", "gene_therapy", "sirna", "mrna", "cart"}
GATES = {
    "bbb": {
        "name": "入脑",
        "problem": "大分子过不了血脑屏障",
        "missing": "II、III 期获益门槛 +15",
        "full": ("forge", 2, "傅以宁（觉醒）· 脑穿梭递送"),
        "partial": (None, 0, "选 ASO 鞘内给药：不用过屏障，但药物分布有限，获益门槛 +7，审评工艺稳定门槛 +8"),
    },
    "population": {
        "name": "选对人",
        "problem": "只有早期、有斑块的患者获益",
        "missing": "II、III 期获益门槛 +12",
        "full": ("bridge", 1, "沈墨言 · 影像标志物，配合分层入组"),
        "partial": ("star", 1, "叶清和 · 机制直觉：门槛只 +7；沈墨言在但未分层入组时同样 +7"),
    },
    "aria": {
        "name": "脑水肿",
        "problem": "清除斑块时的脑水肿（ARIA）风险",
        "missing": "I、III 期安全门槛 +18",
        "full": ("guardian", 1, "孟长青 · 安全设计"),
        "partial": ("judge", 1, "白若霜 · 预审：门槛只 +12"),
    },
    "endpoint": {
        "name": "长终点",
        "problem": "18 个月的认知终点",
        "missing": "III 期噪声 ×2.4、工期 ×1.4",
        "full": ("oracle", 1, "伊莎贝尔·罗哈斯 · 长程终点：噪声恢复"),
        "partial": ("strategist", 1, "欧阳岚 · 多中心：工期恢复，噪声 ×1.8"),
    },
}


def applies(catalog):
    return CATALOG[catalog].get("target_id") in TARGETS


def _who(s, key, minimum):
    if key is None:
        return []
    return [h["name"] for h in s["heroes"] if h["employed"] and talents.level(h, key) >= minimum]


def status(s, catalog, p=None):
    """每道关的状态：full / partial / none，以及研究所里能过这道关的人。"""
    spec = CATALOG[catalog]
    modality = spec.get("modality_id")
    rows = {}
    for key, g in GATES.items():
        full_key, full_level, _ = g["full"]
        part_key, part_level, _ = g["partial"]
        full = _who(s, full_key, full_level)
        partial = _who(s, part_key, part_level)
        state = "full" if full else "partial" if partial else "none"
        if key == "bbb":
            locked = (p or {}).get("gates", {}).get("bbb")
            if locked:
                state = locked
            elif modality not in LARGE:
                state = "partial" if modality == "aso" else "full"
        if key == "population" and state == "full" and p is not None and p.get("population") != "focused":
            state = "partial"
        rows[key] = {"state": state, "people": full or partial}
    return rows


def lock_design(s, p):
    """立项筛选时定下「入脑」：分子设计一旦定了，后来请到谁也改不了。"""
    if applies(p["catalog"]):
        p.setdefault("gates", {})["bbb"] = status(s, p["catalog"])["bbb"]["state"]


def effects(s, p, key, partner=False):
    """这个阶段因四道关产生的门槛调整、噪声和工期倍率。授权给合作方后，合作方没有你的人。"""
    fx = {"limits": {}, "noise": 1.0, "weeks": 1.0}
    if not applies(p["catalog"]):
        return fx
    rows = status(s, p["catalog"], p)
    if partner:
        rows = {k: ({**v, "state": "none"} if k != "bbb" else v) for k, v in rows.items()}

    def add(stat, delta):
        fx["limits"][stat] = fx["limits"].get(stat, 0) + delta

    if key in ("II", "III"):
        add("effect", {"none": 15, "partial": 7, "full": 0}[rows["bbb"]["state"]])
        add("effect", {"none": 12, "partial": 7, "full": 0}[rows["population"]["state"]])
    if key == "review" and rows["bbb"]["state"] == "partial":
        add("quality", 8)
    if key in ("I", "III"):
        add("safety", {"none": 18, "partial": 12, "full": 0}[rows["aria"]["state"]])
    if key == "III":
        endpoint = rows["endpoint"]["state"]
        fx["noise"] = {"none": 2.4, "partial": 1.8, "full": 1.0}[endpoint]
        fx["weeks"] = 1.4 if endpoint == "none" else 1.0
    return fx


def view(s, catalog, p=None):
    if not applies(catalog):
        return None
    rows = status(s, catalog, p)
    return [
        {
            "key": key,
            "name": g["name"],
            "problem": g["problem"],
            "missing": g["missing"],
            "full": g["full"][2],
            "partial": g["partial"][2],
            "state": rows[key]["state"],
            "people": rows[key]["people"],
        }
        for key, g in GATES.items()
    ]
