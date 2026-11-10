"""任期与研究所评级：五项评分、S–D 评级和任期结束的结算。

评分只读已经发生的公开结果（上市、销量、晋阶、奖项、现金），不读候选真值，不抽随机数。
任期结束那一周把评级定格在 ``s["final"]``；之后可以继续经营，但定格的评级不再变化。
"""

from __future__ import annotations

import math

from .content import CATALOG, PATHS

TERMS = (10, 20)
WEIGHTS = {"patients": 0.30, "science": 0.25, "legacy": 0.20, "finance": 0.15, "reputation": 0.10}
NAMES = {
    "patients": "惠及患者",
    "science": "科学突破",
    "legacy": "团队传承",
    "finance": "经营稳健",
    "reputation": "行业声誉",
}
GRADES = [
    (85, "S", "改变一个时代的研究所"),
    (70, "A", "业内标杆"),
    (55, "B", "可靠的新药公司"),
    (40, "C", "站稳脚跟"),
    (0, "D", "仍在路上"),
]
ENDINGS = {
    "patients": ("普惠药业", "你的药走进了千家万户。很多人不知道研究所的名字，但每天都在吃你们做的药。"),
    "science": ("星火生命科学大奖", "你们攻下了别人不敢碰的难题。教科书的下一版，会写到这间研究所。"),
    "legacy": ("薪火研究院", "从街角实验室走出来的人，如今各自带着自己的团队。研究所最好的作品是人。"),
}
# 评级不到 B 时用朴素一些的结局，大奖的名字留给真正做到的人。
MODEST = {
    "patients": ("街坊药房", "几款可靠的药稳稳供着货。研究所不大，但附近的人都信得过它。"),
    "science": ("小有突破", "有过一次让同行侧目的结果。下一次，也许就是真正的突破。"),
    "legacy": ("师徒工作室", "人慢慢带出来了。他们会把这里学到的东西，带到下一个地方。"),
}
# 结局看哪一项比一般水平更突出；一般水平取 v0.11 三种自动玩家 96 局的平均分（团队传承人人都会有一些）。
TYPICAL = {"patients": 54, "science": 47, "legacy": 69}
# 每周销售额（万元）折算成患者人次：仿制药便宜，同样的销售额能覆盖更多人。
PATIENTS_PER_WAN = {"generic": 40, "improved": 20, "innovative": 6}
# 二十年任期的满分参照；十年任期按比例折半。按 v0.11 模拟校准，见 design/v11-playtest.md。
FULL = {"patients": 16_000_000, "science": 300, "legacy": 220, "reputation": 160}


def term_weeks(s):
    return s.get("term", 20) * 48


def weekly_patients(d, revenue):
    return revenue * PATIENTS_PER_WAN[d["kind"]]


def weighted_patients(s):
    """难治疾病和创新药加权：一位难治疾病患者比一位常见病患者更难被帮到。"""
    total = 0.0
    for d in s["products"]:
        spec = CATALOG[d["catalog"]]
        weight = 1 + (1.5 if d["kind"] == "innovative" else 0.5 if d["kind"] == "improved" else 0)
        weight += 2 * spec.get("difficulty", 0)
        total += d.get("patients", 0) * weight
    return total


def science_points(s):
    points = 0
    for d in s["products"]:
        spec = CATALOG[d["catalog"]]
        if d["kind"] == "generic":
            points += 2
        elif d["kind"] == "improved":
            points += 6
        else:
            points += 15 + 20 * spec.get("difficulty", 0)
            if spec.get("target_id") == "abeta":
                points += 40
    points += 8 * sum(r["passed"] for r in s.get("proofs", []))
    return points


def _ratio_curve(value, full):
    """0 到满分的平方根曲线：前期进步看得见，后期越来越难。"""
    if full <= 0:
        return 0.0
    return 100 * min(1.0, math.sqrt(max(0.0, value) / full))


def legacy_points(s):
    employed = [h for h in s["heroes"] if h["employed"]]
    home = [h for h in s["heroes"] if h["tier"] == 1 or h.get("prodigy")]
    return (
        sum(15 for h in home if h["rank"] >= 3)
        + sum(15 for h in home if h["rank"] >= 4)
        + 6 * sum(len(h["mentored"]) for h in s["heroes"])
        + 5 * sum(bool(h.get("personal")) for h in s["heroes"])
        + 10 * len(s.get("inheritances", []))
        + 2 * sum(h["rank"] - h["tier"] for h in employed if h["tier"] > 1)
    )


def dimensions(s, pace=False):
    """五项 0–100 分。pace=True 时按已过去的任期比例缩放满分参照，用来估计「按当前进度」的评级。"""
    weeks = term_weeks(s)
    span = s["term"] / 20 if "term" in s else 1.0
    if pace:
        span *= max(0.25, min(1.0, s["week"] / weeks))
    ratio = s["cash"] / max(1.0, s["capital"])
    finance = 0.0
    if not s["game_over"]:
        finance = 60 * min(1.0, max(0.0, math.log(max(ratio, 1e-9)) / math.log(1 + 15 * span)))
        finance += 25 if s["minimum_cash"] >= 0 else max(0.0, 25 * (1 + s["minimum_cash"] / s["capital"]))
        finance += 15 if s["cash"] > 0 else 0
    reputation_points = _reputation_points(s)
    return {
        "patients": round(_ratio_curve(weighted_patients(s), FULL["patients"] * span), 1),
        "science": round(_ratio_curve(science_points(s), FULL["science"] * span), 1),
        "legacy": round(_ratio_curve(legacy_points(s), FULL["legacy"] * span), 1),
        "finance": round(min(100.0, finance), 1),
        "reputation": round(_ratio_curve(reputation_points, FULL["reputation"] * span), 1),
    }


def grade(total):
    return next((g, title) for floor, g, title in GRADES if total >= floor)


def summarize(s, pace=False):
    dims = dimensions(s, pace)
    total = round(sum(dims[k] * w for k, w in WEIGHTS.items()), 1)
    letter, title = grade(total)
    lead = max(("patients", "science", "legacy"), key=lambda k: (dims[k] - TYPICAL[k], k))
    ending, text = (ENDINGS if total >= 55 else MODEST)[lead]
    return {
        "total": total,
        "grade": letter,
        "title": title,
        "dimensions": [
            {"key": k, "name": NAMES[k], "weight": round(w * 100), "score": dims[k]} for k, w in WEIGHTS.items()
        ],
        "ending": ending,
        "ending_text": text,
    }


def highlights(s):
    """结算画面的代表作：最重要的药、最得力的人。"""
    best = max(
        s["products"],
        key=lambda d: (d.get("patients", 0) * (3 if d["kind"] == "innovative" else 1), d["launched"]),
        default=None,
    )
    people = [h for h in s["heroes"] if h["employed"]]
    star = max(people, key=lambda h: (h["rank"] - h["tier"], len(h["cases"]), h["id"]), default=None)
    return {
        "product": best["name"] if best else None,
        "patients": round(sum(d.get("patients", 0) for d in s["products"])),
        "hero": star["name"] if star else None,
        "approved": sum(1 for d in s["products"] if not d["partner"]),
        "innovative": sum(1 for d in s["products"] if d["kind"] == "innovative"),
    }


def finish_term(s):
    """任期结束那一周定格评级；停业也会提前结算。只结算一次。"""
    if s.get("final") or "term" not in s:
        return
    ended = s["week"] >= term_weeks(s)
    if not ended and not s["game_over"]:
        return
    from .events import emit
    from .model import log

    result = summarize(s)
    s["final"] = {
        **result,
        "week": s["week"],
        "early": bool(s["game_over"] and not ended),
        "highlights": highlights(s),
    }
    from . import chronicle

    chronicle.add(s, "term", f"任期结束：评级 {result['grade']}「{result['title']}」，结局「{result['ending']}」")
    emit(
        s,
        "term_ended",
        actors=[h["id"] for h in s["heroes"] if h["employed"]],
        data={"grade": result["grade"], "title": result["title"], "ending": result["ending"]},
    )
    if s["final"]["early"]:
        log(s, f"研究所提前停业，任期评级定格为 {result['grade']}（{result['title']}）。")


EARLY = 96  # 周：前两年先打基础，不急着给字母


def _span(s):
    return s["term"] / 20 * max(0.25, min(1.0, s["week"] / term_weeks(s)))


def _reputation_points(s):
    from .goals import REPUTATION_POINTS

    return (
        REPUTATION_POINTS * len(s.get("goal_log", []))
        + 12 * len(s.get("awards", []))
        + 4 * len(s.get("nominations", []))
        + 10 * len(s.get("bounties_done", []))
        + 15 * len(s.get("legacies", []))
    )


def _gain(s, key, extra):
    """某一项再多 extra 点（各项自己的单位），按「当前进度」估计这一项和总分各涨多少。"""
    base = {
        "patients": weighted_patients,
        "science": science_points,
        "legacy": legacy_points,
        "reputation": _reputation_points,
    }[key](s)
    full = FULL[key] * _span(s)
    delta = _ratio_curve(base + extra, full) - _ratio_curve(base, full)
    return round(delta, 1), round(delta * WEIGHTS[key], 1)


def levers(s, limit=3):
    """评级卡上的「怎么涨分」：按公开规则算出几条最近的办法，各涨多少。只读。"""
    from . import stories
    from .content import RANKS

    out = []

    def add(dimension, text, key, extra):
        dim, total = _gain(s, key, extra)
        out.append({"dimension": dimension, "text": text, "gain": dim, "total_gain": total})

    home = [h for h in s["heroes"] if h["employed"] and (h["tier"] == 1 or h.get("prodigy")) and 2 <= h["rank"] < 4]
    if home:
        h = max(home, key=lambda h: (h["rank"], h["xp"]))
        add("团队传承", f"把{h['name']}培养成{RANKS[h['rank'] + 1]}", "legacy", 15)
    if any(h["employed"] and h["rank"] >= 2 for h in s["heroes"]):
        add("团队传承", "完成一次带教", "legacy", 6)
    ready = [h for h in s["heroes"] if h["employed"] and not h.get("personal") and stories.options(s, h)["unlocked"]]
    if ready:
        add("团队传承", f"完成{ready[0]['name']}的个人课题", "legacy", 5)
    bounty = next((b for b in s.get("bounties", []) if b["status"] == "open"), None)
    if bounty:
        add("行业声誉", f"完成患者委托「{bounty['disease']}」", "reputation", 10)
    active = [p for p in s["projects"] if p["status"] not in ("approved", "failed", "terminated", "licensed")]
    if active:
        p = max(active, key=lambda p: p["index"] / len(PATHS[p["kind"]]))
        points = {"generic": 2, "improved": 6}.get(p["kind"], 15 + 20 * CATALOG[p["catalog"]].get("difficulty", 0))
        add("科学突破", f"{p['name']}上市", "science", points)
    yearly = 27 * PATIENTS_PER_WAN["generic"] * 48  # 一款仿制药卖一年：峰值周收入 × 患者折算 × 48 周
    add("惠及患者", f"多一款仿制药卖一年（约帮助 {round(yearly / 10000)} 万人次）", "patients", yearly)
    out.sort(key=lambda x: -x["total_gain"])
    out = out[:limit]
    if s["minimum_cash"] < 0 and not s["game_over"]:
        lost = round(25 - max(0.0, 25 * (1 + s["minimum_cash"] / s["capital"])), 1)
        out.append(
            {"dimension": "经营稳健", "text": f"出现过负现金，这一项少了 {lost} 分", "gain": -lost, "total_gain": 0.0}
        )
    return out


def gap_to_next(total):
    """离上一个字母还差几分；已经是 S 时为 None。"""
    higher = [(floor, g) for floor, g, _ in GRADES if floor > total]
    if not higher:
        return None
    floor, letter = min(higher)
    return {"grade": letter, "points": round(floor - total, 1)}


def view(s):
    projected = summarize(s, pace=True)
    return {
        "early": s["week"] < EARLY and not s.get("final"),
        "gap": gap_to_next(projected["total"]),
        "levers": levers(s),
        "term": s.get("term", 20),
        "term_weeks": term_weeks(s),
        "weeks_left": max(0, term_weeks(s) - s["week"]),
        "current": summarize(s),
        "projected": projected,
        "final": s.get("final"),
        "patients": round(sum(d.get("patients", 0) for d in s["products"])),
    }
