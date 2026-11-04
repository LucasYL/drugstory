"""Optional bounded commercial challenge; scientific approval limits are unchanged."""

from .model import check

MODES = {
    "standard": {"name": "舒展经营", "text": "适合体验人物、研发与年度荣誉；没有额外平台维护或总市场容量限制。"},
    "competition": {
        "name": "产业竞逐",
        "text": "对手研发更快、市场总容量有限；从扩建后承担公开的平台维护费，可选择维护投入。审批标准不变。",
    },
}
POLICIES = {
    "lean": {
        "name": "节约维护",
        "factor": 0.65,
        "noise": 1.08,
        "fee": 1,
        "text": "维护费 ×0.65；校准精度下降，研究观察误差增加 8%。",
    },
    "balanced": {"name": "常规维护", "factor": 1, "noise": 1, "fee": 0.97, "text": "按标准维护，阶段费减少 3%。"},
    "frontier": {
        "name": "精密平台",
        "factor": 1.65,
        "noise": 0.92,
        "fee": 0.95,
        "text": "维护费 ×1.65；观察误差减少 8%，阶段费减少 5%。",
    },
}
CAPACITY = {"pressure": 90, "lipid": 190, "pain": 110, "sugar": 95, "allergy": 85, "inflammation": 210, "lung": 250}


def enabled(s):
    return s.get("difficulty", "standard") == "competition"


def policy(s):
    return POLICIES[s.get("platform_policy", "balanced")]


def upkeep(s):
    if not enabled(s):
        return 0
    # Fixed, public scale schedule, never a percentage of accumulated wealth.
    return [0, 5, 16, 36][s["facility"]] * policy(s)["factor"]


def set_policy(s, policy_name: str):
    check(enabled(s), "平台维护策略仅用于产业竞逐模式")
    check(policy_name in POLICIES, "请选择维护策略")
    s["platform_policy"] = policy_name


def view(s):
    return {
        "mode": s.get("difficulty", "standard"),
        "modes": MODES,
        "policy": s.get("platform_policy", "balanced"),
        "policies": POLICIES,
        "upkeep": round(upkeep(s), 2),
        "capacity": CAPACITY if enabled(s) else {},
    }
