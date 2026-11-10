"""主动技能：每人一个，带冷却。见习伙伴晋升精英后解锁，精英以上的伙伴加入时就有。

技能只用九种原语（缩短工期、立刻复核、改善一项指标、多一个候选、调门槛、救回差一点的失败、
带教经验、改善在售产品、立刻交付服务），数据写在 data/abilities.json 的 active 字段。
所有检查都在修改之前；随机都用带键随机。界面只读 ``usable`` / ``view`` 的结果。
"""

from __future__ import annotations

import math

from . import talents
from .content import CATALOG, CLINICAL, PATHS, STAGES, TARGETS
from .model import ACTIVE, ability, available_money, check, find, hero, spend

UNLOCK_RANK = 2


def spec(key):
    return talents.ABILITIES[key]["active"]


def unlocked(h):
    return h["employed"] and (h["tier"] >= 2 or h["rank"] >= UNLOCK_RANK)


def ready_in(s, h):
    return max(0, h.get("skill_ready", 0) - s["week"])


def _clinical_running(p):
    return p["status"] == "running" and not p.get("experiment") and (p.get("execution") or {}).get("key") in CLINICAL


def _next_stage(p):
    """「下一阶段」：准备开工时就是当前阶段，拿到结果后是下一阶段。"""
    path = PATHS[p["kind"]]
    if p["status"] == "ready":
        return path[p["index"]]
    if p["status"] == "result" and p["results"] and p["results"][-1]["passed"] and p["index"] + 1 < len(path):
        return path[p["index"] + 1]
    return None


def _preclinical(p):
    """候选还能改：下一个要做的阶段还在临床之前（仿制药是等效性做完之前）。"""
    if p.get("chosen") is None or p["status"] not in ("ready", "result", "problem"):
        return False
    upcoming = p["index"] + (1 if p["status"] == "result" else 0)
    return upcoming < (3 if p["kind"] == "generic" else 2)


def project_problem(s, h, p):
    """这个技能能不能用在项目 p 上；不能就返回原因。"""
    a = spec(h["id"])
    k, prm = a["kind"], a["params"]
    used = p.get("skills_used", [])
    if k == "rescue":
        if p["status"] != "failed" or not p["results"] or p.get("reanalyzed"):
            return "没有可以重新分析的失败"
        r = p["results"][-1]
        if r["key"] not in CLINICAL or s["week"] - r["week"] > prm["weeks"]:
            return "只能救 8 周内的临床失败"
        if any(r["limits"][x] - r["values"][x] > prm["margin"] for x in r["failures"]):
            return "差得太多，重新分析也救不回来"
        return None
    if p["status"] not in ACTIVE:
        return "项目已经结束"
    if k == "shorten":
        if prm.get("member") and h["id"] not in p["team"]:
            return f"{h['name']}不在这个项目的团队里"
        if prm.get("experiment"):
            return None if p["status"] == "running" and p.get("experiment") and p["left"] > 1 else "没有在做的专项研究"
        if prm.get("clinical"):
            return None if _clinical_running(p) and p["left"] > 2 else "没有进行中的临床阶段"
        build = (
            p["status"] == "running" and not p.get("experiment") and p.get("execution", {}).get("category") == "build"
        )
        return None if build and p["left"] > 1 else "没有进行中的开发阶段"
    if k == "reveal":
        if prm.get("clinical"):
            return None if _clinical_running(p) else "没有进行中的临床阶段"
        if p.get("chosen") is None or p["status"] != "ready":
            return "只能在准备开工时复核"
        if f"{h['id']}" in used:
            return "这个项目已经复核过一次"
        return None
    if k == "improve":
        if f"{h['id']}" in used:
            return "这个项目已经用过一次"
        if not _preclinical(p):
            return "只能在临床前改候选"
        return None
    if k == "candidate":
        if p["status"] != "selecting":
            return "只能在选候选时用"
        if prm.get("failed_target"):
            target = CATALOG[p["catalog"]].get("target")
            failed = any(
                q["status"] in ("failed", "terminated") and CATALOG[q["catalog"]].get("target") == target
                for q in s["projects"]
                if q["id"] != p["id"]
            )
            if not failed:
                return "同靶点还没有失败过"
        return None if f"{h['id']}" not in used else "这个项目已经用过一次"
    if k == "limit":
        stage = _next_stage(p)
        if stage is None:
            return "没有待开工的阶段"
        if prm.get("stage") and prm["stage"] != stage:
            return f"下一阶段不是{STAGES[prm['stage']]['name']}"
        return None if stage not in p.get("adjust_next", {}) else "下一阶段已经用过技能"
    if k == "marker":
        if p["kind"] != "innovative" or p.get("chosen") is None or p["status"] != "ready":
            return "只能在创新药准备开工时用"
        if p["index"] > PATHS["innovative"].index("II"):
            return "人群分层要在 II 期方案定之前"
        c = p["candidates"][p["chosen"]]
        return None if c["marker"]["observations"] == 0 else "已经做过分层研究"
    return "这个技能不用在项目上"


def problem(s, h, project="", product="", target=""):
    """技能现在能不能用；不能就返回原因。"""
    if not unlocked(h):
        return "晋升精英后解锁"
    if ready_in(s, h):
        return f"还要等 {ready_in(s, h)} 周"
    a = spec(h["id"])
    if s["cash"] - _committed(s) < a["cost"]:
        return f"可用现金需要 ¥{a['cost']} 万"
    scope = a["scope"]
    if scope == "project":
        p = next((x for x in s["projects"] if x["id"] == project), None)
        return "请选择项目" if p is None else project_problem(s, h, p)
    if scope == "product":
        d = next((x for x in s["products"] if x["id"] == product), None)
        if d is None or d["partner"] or not d["active"]:
            return "请选择在售的自主产品"
        return None if h["id"] not in d.get("skills_used", []) else "这款产品已经改过一次"
    if scope == "target":
        if target not in TARGETS:
            return "请选择靶点"
        keys = [k for k, c in CATALOG.items() if c.get("target_id") == target]
        return None if any(k not in s["notebook"] for k in keys) else "这个靶点已经全部记下了"
    if h["id"] == "pill":
        return (
            None if any(j["kind"] == "service" and h["id"] in j["heroes"] for j in s["jobs"]) else "她手上没有技术服务"
        )
    if h["id"] == "star":
        return None if _pupil(s, h) else "没有同专业、阶位更低的伙伴"
    return None


def _committed(s):
    from .model import committed

    return committed(s)


def _pupil(s, h):
    options = [x for x in s["heroes"] if x["employed"] and x["profession"] == h["profession"] and x["rank"] < h["rank"]]
    return min(options, key=lambda x: (x["rank"], x["xp"], x["id"])) if options else None


def use(s, character, project="", product="", target=""):
    h = hero(s, character)
    check("active" in talents.ABILITIES.get(character, {}), "这位伙伴没有主动技能")
    error = problem(s, h, project, product, target)
    check(error is None, error or "")
    a = spec(character)
    available_money(s, a["cost"])
    k, prm = a["kind"], a["params"]
    p = find(s["projects"], project) if a["scope"] == "project" else None
    if a["cost"]:
        spend(s, a["cost"], "skills")
    if k == "shorten":
        if prm.get("experiment"):
            cut = p["left"] - 1
        elif prm.get("ratio"):
            cut = math.ceil(p["left"] * prm["ratio"])
        else:
            cut = min(prm["weeks"], p["left"] - 1)
        remaining = p["cost_per_week"] * p["left"] * prm.get("cost", 1)
        new_left = max(1, p["left"] - cut)
        e = p.get("execution") or {}
        if not p.get("experiment") and e.get("checkpoint_at") and not e.get("checkpoint_done"):
            # 不让缩短跳过临床期中的决定点
            e["checkpoint_at"] = min(e["checkpoint_at"], new_left - 1) if new_left > 1 else e["checkpoint_at"]
            if new_left <= 1:
                e["checkpoint_done"] = True
        p["left"] = new_left
        p["cost_per_week"] = remaining / new_left
        text = f"剩余工期 −{cut} 周"
    elif k == "reveal":
        from .science import observe, selected

        c = selected(p)
        n = sum(1 for x in p.get("skills_used", []) if x == character)
        observe(s, p, c, prm["stat"], prm["sigma"], f"skill-{character}-{n}")
        text = "复核完成，范围变窄"
    elif k == "improve":
        from .science import selected

        c = selected(p)
        for stat, amount in {prm["stat"]: prm["amount"], **prm.get("trade", {})}.items():
            actual = min(98, max(10, c["truth"][stat] + amount)) - c["truth"][stat]
            c["truth"][stat] += actual
            c["belief"][stat]["mean"] += actual
        text = "候选改善了"
    elif k == "candidate":
        from .science import make_candidate

        make_candidate(
            s, p, "失败地图上的那条路" if prm.get("effect") else "再筛出的线索", {"effect": prm.get("effect", 0)}
        )
        text = "多了一个候选"
    elif k == "limit":
        stage = _next_stage(p)
        p.setdefault("adjust_next", {})[stage] = {
            "limits": prm.get("limits", {}),
            "minus": prm.get("minus", 0),
            "weeks": prm.get("weeks", 1.0),
        }
        text = f"{STAGES[stage]['name']}：{a['text']}"
    elif k == "rescue":
        p.update(status="problem", ended=None, reanalyzed=True, cost_per_week=0)
        text = "重新分析：这次失败改为可补正"
    elif k == "marker":
        from .model import rand
        from .science import selected

        c = selected(p)
        if talents.has(s, "bridge", [character]) and not c.get("imaging"):
            c["subgroup"] *= 2
            c["imaging"] = True
        sigma = max(3, 9 - ability(h) / 15)
        sample = c["subgroup"] + rand(s, p["id"], "marker-skill").gauss(0, sigma)
        b = c["marker"]
        v = 1 / (1 / b["variance"] + 1 / sigma**2)
        b.update(mean=v * (b["mean"] / b["variance"] + sample / sigma**2), variance=v, observations=1)
        c["checks"]["markereffect"] = c["checks"].get("markereffect", 0) + 1
        text = "人群分层结果到了"
    elif k == "product":
        d = find(s["products"], product)
        if "factor" in prm:
            d["peak"] *= prm["factor"]
        if "margin" in prm:
            d["margin"] = min(0.9, d["margin"] + prm["margin"])
        d.setdefault("skills_used", []).append(character)
        text = f"{d['name']}：{a['text']}"
    elif k == "notebook":
        from .content import CATALOG as _C

        for key, c in _C.items():
            if c.get("target_id") == target and key not in s["notebook"]:
                s["notebook"][key] = {"tier": c["combo_tier"], "reason": c["combo_reason"], "week": s["week"]}
        text = f"{TARGETS[target]['name']}的 12 个组合都记下了"
    elif k == "service":
        from .economy import finish_job

        job = next(j for j in s["jobs"] if j["kind"] == "service" and character in j["heroes"])
        finish_job(s, job)
        s["jobs"].remove(job)
        text = "服务提前交付"
    elif k == "xp":
        u = _pupil(s, h)
        u["xp"] += prm["amount"]
        text = f"{u['name']}经验 +{prm['amount']}"
    if p is not None:
        p.setdefault("skills_used", []).append(character)
    h["skill_ready"] = s["week"] + a["cooldown"]
    talents.trigger(s, character, text, [character])


def usable(s, p):
    """决定卡上能直接用的技能（只读）。"""
    out = []
    for h in s["heroes"]:
        if not h["employed"] or "active" not in talents.ABILITIES.get(h["id"], {}):
            continue
        a = spec(h["id"])
        if a["scope"] != "project" or problem(s, h, project=p["id"]) is not None:
            continue
        out.append(
            {
                "hero": h["id"],
                "hero_name": h["name"],
                "name": a["name"],
                "text": a["text"],
                "cost": a["cost"],
                "args": {"character": h["id"], "project": p["id"]},
            }
        )
    return out


def view(s, h):
    """人物卡上的主动技能：说明、冷却、现在能用在哪些地方。"""
    a = spec(h["id"])
    choices = []
    if unlocked(h) and not ready_in(s, h):
        if a["scope"] == "project":
            choices = [
                {"label": p["name"], "args": {"character": h["id"], "project": p["id"]}}
                for p in s["projects"]
                if problem(s, h, project=p["id"]) is None
            ]
        elif a["scope"] == "product":
            choices = [
                {"label": d["name"], "args": {"character": h["id"], "product": d["id"]}}
                for d in s["products"]
                if problem(s, h, product=d["id"]) is None
            ]
        elif a["scope"] == "target":
            open_targets = [
                t
                for t in TARGETS
                if any(c.get("target_id") == t and k not in s["notebook"] for k, c in CATALOG.items())
                and problem(s, h, target=t) is None
            ]
            choices = [
                {"label": TARGETS[t]["disease"], "args": {"character": h["id"], "target": t}} for t in open_targets[:6]
            ]
        elif problem(s, h) is None:
            choices = [{"label": a["name"], "args": {"character": h["id"]}}]
    return {
        **{k: a[k] for k in ("name", "text", "cost", "cooldown", "scope")},
        "unlocked": unlocked(h),
        "ready_in": ready_in(s, h),
        "choices": choices,
        "note": None if unlocked(h) else "晋升精英后解锁",
    }
