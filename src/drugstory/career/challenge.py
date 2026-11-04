"""Optional bounded commercial challenge; scientific approval limits are unchanged."""

MODES = {
    "standard": {"name": "舒展经营", "text": "适合体验人物、研发与年度荣誉；没有额外平台维护或总市场容量限制。"},
    "competition": {
        "name": "产业竞逐",
        "text": "对手研发更快、市场总容量有限；同领域产品需要竞争需求。审批标准不变。",
    },
}
CAPACITY = {
    "pressure": 90,
    "lipid": 190,
    "pain": 110,
    "sugar": 95,
    "allergy": 85,
    "inflammation": 210,
    "lung": 250,
    "blood": 180,
    "neuro": 160,
    "rare": 100,
    "infection": 220,
}


def enabled(s):
    return s.get("difficulty", "standard") == "competition"


def upkeep(s):
    return 0


def view(s):
    return {
        "mode": s.get("difficulty", "standard"),
        "modes": MODES,
        "upkeep": 0,
        "capacity": CAPACITY if enabled(s) else {},
    }
