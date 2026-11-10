"""花钱的出口：把多余的现金换成评级上的某一项。

- 自有产线：这款产品改为自产，毛利更高、不受供货折减；占用场地的产线数。
- 患者援助：花掉这款产品销售额的一部分，让更多患者用上（只算惠及患者，不加收入）。
- 青年学者计划：每期加团队传承；第 3 期起每期让一位见习伙伴多 10 经验。
- 临床病房：自营临床席位 +1。
都是公开规则；不读候选真值。
"""

from __future__ import annotations

from . import chronicle, talents
from .content import FACILITIES
from .model import available_money, check, find, log, spend

LINE_COST = {"generic": 500, "improved": 800, "innovative": 1500}
LINE_WEIGHT = {"generic": 1, "improved": 1, "innovative": 2}
LINE_MARGIN = {"generic": 0.10, "improved": 0.06, "innovative": 0.06}
LINE_UPKEEP = 1
ARCHITECT_DISCOUNT = 0.3
ARCHITECT_MARGIN = 0.06
ACCESS_SHARE = 0.12
ACCESS_PATIENTS = 1.6
FELLOWSHIP_COST = 600
FELLOWSHIP_MAX = 5
FELLOWSHIP_LEGACY = 8
FELLOWSHIP_XP = 10
WARD_COST = 1200
WARD_MAX = 2
WARD_UPKEEP = 2


def lines_used(s):
    return sum(
        LINE_WEIGHT[d["kind"]]
        for d in s["products"]
        if d["active"] and not d["partner"] and d.get("production") == "self"
    )


def lines_total(s):
    return FACILITIES[s["facility"]]["lines"]


def line_cost(s, d):
    cost = LINE_COST[d["kind"]]
    return round(cost * (1 - ARCHITECT_DISCOUNT)) if talents.has(s, "architect") else cost


def line_margin(s, d):
    """自有产线多出来的毛利。高铁峰在职时再加一点。"""
    if d["partner"] or d.get("production") != "self":
        return 0.0
    return LINE_MARGIN[d["kind"]] + (ARCHITECT_MARGIN if talents.has(s, "architect") else 0)


def line_problem(s, d):
    """不能建线的原因；能建返回 None。只读。"""
    if d["partner"] or not d["active"]:
        return "只能为在售的自主产品建线"
    if d.get("production") == "self":
        return "已经是自有产线"
    if lines_used(s) + LINE_WEIGHT[d["kind"]] > lines_total(s):
        return "场地放不下更多产线，先搬进下一档场地" if lines_total(s) else "街角实验室没有产线位置"
    return None


def build_line(s, product):
    d = find(s["products"], product)
    problem = line_problem(s, d)
    check(problem is None, problem or "")
    cost = line_cost(s, d)
    available_money(s, cost)
    spend(s, cost, "lines")
    d["production"] = "self"
    chronicle.add(s, "facility", f"为{d['name']}建起自有产线")
    log(s, f"{d['name']}改为自有产线生产：毛利更高，不再受供货折减影响。运营费每周 ¥{LINE_UPKEEP} 万。")


def access_program(s, product, on):
    d = find(s["products"], product)
    check(not d["partner"] and (d["active"] or not on), "只能为在售的自主产品开患者援助")
    check(on in (0, 1), "请选择开或关")
    d["access"] = bool(on)
    log(
        s,
        f"{d['name']}的患者援助计划已{'开启：每周拿出销售额的 12%，让更多患者用上' if on else '关闭'}。",
    )


def access_step(s, d, revenue):
    """每周：援助的花费；每满一年声誉 +1。返回患者人次倍率。"""
    if not d.get("access") or d["partner"] or revenue <= 0:
        return 1.0
    spend(s, revenue * ACCESS_SHARE, "access")
    d["access_weeks"] = d.get("access_weeks", 0) + 1
    if d["access_weeks"] % 48 == 0:
        s["reputation"] += 1
    return ACCESS_PATIENTS


def fellowship_problem(s):
    if s["facility"] < 1:
        return "搬进联合研发所以后才能办"
    if s.get("fellowships", 0) >= FELLOWSHIP_MAX:
        return f"最多办 {FELLOWSHIP_MAX} 期"
    return None


def fund_fellowship(s):
    problem = fellowship_problem(s)
    check(problem is None, problem or "")
    available_money(s, FELLOWSHIP_COST)
    spend(s, FELLOWSHIP_COST, "fellowship")
    s["fellowships"] = s.get("fellowships", 0) + 1
    n = s["fellowships"]
    text = f"第 {n} 期青年学者计划开班"
    if n >= 3:
        juniors = sorted((h for h in s["heroes"] if h["employed"] and h["rank"] == 1), key=lambda h: (h["xp"], h["id"]))
        if juniors:
            juniors[0]["xp"] += FELLOWSHIP_XP
            text += f"，{juniors[0]['name']}带了一期学员，经验 +{FELLOWSHIP_XP}"
    chronicle.add(s, "legacy", text)
    log(s, text + "。")


def ward_problem(s):
    if s.get("wards", 0) >= WARD_MAX:
        return f"最多建 {WARD_MAX} 个临床病房"
    return None


def build_ward(s):
    problem = ward_problem(s)
    check(problem is None, problem or "")
    available_money(s, WARD_COST)
    spend(s, WARD_COST, "wards")
    s["wards"] = s.get("wards", 0) + 1
    chronicle.add(s, "facility", f"第 {s['wards']} 个临床病房启用")
    log(s, f"临床病房启用：自营临床席位 +1，运营费每周 ¥{WARD_UPKEEP} 万。")


def upkeep(s):
    return lines_used(s) * LINE_UPKEEP + s.get("wards", 0) * WARD_UPKEEP


def view(s):
    cash = s["cash"]
    return {
        "lines": {"used": lines_used(s), "total": lines_total(s), "upkeep": LINE_UPKEEP},
        "fellowship": {
            "done": s.get("fellowships", 0),
            "max": FELLOWSHIP_MAX,
            "cost": FELLOWSHIP_COST,
            "problem": fellowship_problem(s),
            "ok": fellowship_problem(s) is None and cash >= FELLOWSHIP_COST,
        },
        "ward": {
            "done": s.get("wards", 0),
            "max": WARD_MAX,
            "cost": WARD_COST,
            "upkeep": WARD_UPKEEP,
            "problem": ward_problem(s),
            "ok": ward_problem(s) is None and cash >= WARD_COST,
        },
        "upkeep": upkeep(s),
    }


def product_view(s, d):
    """产品卡上的两个按钮。"""
    if d["partner"]:
        return None
    return {
        "self": d.get("production") == "self",
        "line_cost": line_cost(s, d),
        "line_problem": line_problem(s, d),
        "line_margin": round(LINE_MARGIN[d["kind"]] + (ARCHITECT_MARGIN if talents.has(s, "architect") else 0), 2),
        "access": bool(d.get("access")),
        "access_share": ACCESS_SHARE,
    }
