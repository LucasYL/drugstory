"""Distinct product constraints and explicit investment into commercial usefulness."""

PROFILES = {
    "g_pressure": (
        "持续供货",
        "review",
        "quality",
        65,
        "备选供应链",
        "supply",
        "单一来源在每第三个季度供货折减 12%；验证双来源后免除此折减。",
    ),
    "g_lipid": (
        "低剂量均匀性",
        "quality",
        "quality",
        70,
        "微量混合验证",
        "quality",
        "含量均匀性要求更高；强化验证通过后，制造利润率增加 3 个百分点。",
    ),
    "g_pain": (
        "溶出一致性",
        "be",
        "exposure",
        68,
        "多条件溶出验证",
        "quality",
        "等效性要求更高；强化验证通过后，制造利润率增加 3 个百分点。",
    ),
    "g_sugar": (
        "储存稳定性",
        "quality",
        "quality",
        68,
        "温湿度稳定验证",
        "stability",
        "稳定性要求更高；强化验证通过后，市场生命周期延长 48 周。",
    ),
    "g_allergy": (
        "小片易服",
        "be",
        "exposure",
        66,
        "服用体验验证",
        "adherence",
        "小片剂仍须证明等效；强化验证通过后，市场导入加快，峰值需求增加 8%。",
    ),
    "g_inflammation": (
        "杂质控制",
        "quality",
        "safety",
        64,
        "杂质谱验证",
        "quality",
        "杂质安全要求更高；强化验证通过后，制造利润率增加 3 个百分点。",
    ),
    "i_long": (
        "长效依从性",
        "confirm",
        "exposure",
        66,
        "给药日记随访",
        "adherence",
        "价值确认还需足够暴露证据；强化随访通过后，市场导入加快，峰值需求增加 8%。",
    ),
    "i_gentle": (
        "耐受性改善",
        "confirm",
        "safety",
        69,
        "主动症状随访",
        "tolerability",
        "耐受改善需更强安全证据；强化随访通过后，峰值需求增加 10%。",
    ),
    "i_delivery": (
        "便携给药",
        "confirm",
        "quality",
        70,
        "使用与运输验证",
        "stability",
        "给药设备需稳定可靠；强化验证通过后，市场生命周期延长 48 周。",
    ),
}


def profile(catalog):
    p = PROFILES.get(catalog)
    if not p:
        return None
    title, stage, stat, limit, enhanced, reward, text = p
    return {
        "title": title,
        "stage": stage,
        "stat": stat,
        "limit": limit,
        "enhanced": enhanced,
        "reward": reward,
        "text": text,
    }


def adjust_limits(p, key, limits):
    spec = profile(p["catalog"])
    if spec and spec["stage"] == key:
        limits[spec["stat"]] = max(limits.get(spec["stat"], 0), spec["limit"])
    return limits


def reward(p):
    spec = profile(p["catalog"])
    if not spec or p.get("design", "standard") != "validated":
        return None
    return spec["reward"] if any(r["key"] == spec["stage"] and r["passed"] for r in p["results"]) else None


def supply_factor(s, d):
    if d["catalog"] == "g_pressure" and d.get("design_reward") != "supply" and s["week"] // 12 % 3 == 2:
        return 0.88
    return 1.0
