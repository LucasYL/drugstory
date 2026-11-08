"""Smart defaults so a player can act in one click.

Everything here reads public state only: who is free, abilities, ranks and public beliefs.
Nothing is mutated. A one-click plan is tried on a copy through ``engine.execute`` — the
same entry the web page, CLI and simulations use — so a button is only offered when the
command would really succeed, and its weeks, cost and chance are the ones the engine uses.
"""

from __future__ import annotations

import copy

from . import economy as e
from . import science as sc
from .content import CLINICAL, EXPERIMENTS, PATHS, PROFESSIONS, STAGES
from .model import ability, busy, power
from .units import pts


def chance_range(probability):
    mid = round(probability * 100)
    return f"约 {max(0, mid - 8)}–{min(99, mid + 8)}%"


def level(probability):
    """先说高中低，精确数字放在后面。"""
    if probability is None:
        return None
    return "高" if probability >= 0.65 else "中" if probability >= 0.35 else "低"


def free_heroes(s):
    occupied = busy(s)
    return [h for h in s["heroes"] if h["employed"] and h["id"] not in occupied]


def recommended_team(s, p):
    """Strongest free specialist for each role of the project's current stage, plus the execution mode."""
    from . import engine

    stage = sc.stage_key(p)
    available = free_heroes(s)
    result = []
    for role in STAGES[stage]["roles"]:
        options = [h for h in available if h["profession"] == role]
        if options:
            result.append(max(options, key=ability)["id"])
    mode = "cro" if stage in CLINICAL and not any(h["profession"] == "clinical" for h in available) else "internal"
    if (
        stage in CLINICAL
        and engine.internal_usage(s) >= engine.clinical_slots(s)
        and not (p["clinical_started"] and p["mode"] == "internal")
    ):
        mode = "cro"
    return result, mode


def screening_team(s, kind):
    """Strongest free hero in each profession that matters for screening this kind of project."""
    relevant = ("bio", "chem") if kind == "innovative" else ("chem", "proc")
    available = free_heroes(s)
    team = []
    for profession in relevant:
        options = [h for h in available if h["profession"] == profession]
        if options:
            team.append(max(options, key=ability)["id"])
    return team


def reserved(s):
    """People the waiting decisions would use by default; services avoid them when they can."""
    held = set()
    for p in s["projects"]:
        if p.get("deferred"):
            continue
        if p["status"] == "ready":
            held.update(recommended_team(s, p)[0])
        elif p["status"] == "result" and sc.stage_key(p) != "review":
            held.update(recommended_team(s, {**p, "index": p["index"] + 1, "status": "ready"})[0])
    return held


def service_picks(s):
    """One suggested person per open order: the weakest qualified free hero.

    Service pay does not depend on ability, so the strongest people stay free for research.
    Orders with the fewest qualified people pick first, so nobody is suggested twice, and
    people the waiting decisions need are used only when nobody else qualifies.
    """
    available = free_heroes(s)
    held = reserved(s)
    orders = [o for o in e.orders(s) if not o["taken"]]

    def qualified(order):
        return [h for h in available if h["profession"] == order["profession"] and ability(h) >= order["requirement"]]

    picks, used = {}, set()
    for order in sorted(orders, key=lambda o: (len(qualified(o)), o["id"])):
        options = [h for h in qualified(order) if h["id"] not in used]
        if not options:
            need = f"需要{PROFESSIONS[order['profession']]}能力 ≥ {order['requirement']} 的空闲伙伴"
            picks[order["id"]] = {"hero": None, "note": need}
            continue
        spare = [h for h in options if h["id"] not in held]
        choice = min(spare or options, key=lambda h: (ability(h), h["rank"], h["id"]))
        used.add(choice["id"])
        picks[order["id"]] = {
            "hero": choice["id"],
            "note": None if spare else "会占用待开工项目的推荐负责人",
        }
    return picks


def _try(s, command, args):
    from . import engine

    try:
        return engine.execute(s, command, args), None
    except ValueError as error:
        return None, str(error)


def quick(s, p):
    """The default next step for a project waiting on the player, already checked by the engine.

    Deferred projects get one too, so the page can show "可以开工了" as soon as people are free.
    """
    if p["status"] not in ("ready", "result", "problem"):
        return None
    key = sc.stage_key(p)
    if p["status"] == "problem":
        if p["repairs"] >= 1:
            return None
        options = [h for h in free_heroes(s) if h["profession"] in ("proc", "chem")]
        team = [max(options, key=ability)["id"]] if options else []
        args = {"project": p["id"], "heroes": team}
        _, error = _try(s, "rework", args)
        return {
            "command": "rework",
            "args": args,
            "label": "补正一次再验证",
            "roles": ["proc", "chem"],
            "stage": STAGES[key]["name"],
            "weeks": 8,
            "cost": 100,
            "chance": None,
            "ok": error is None,
            "error": error,
        }
    if p["status"] == "result" and key == "review":
        args = {"project": p["id"], "name": p["name"]}
        _, error = _try(s, "launch", args)
        return {
            "command": "launch",
            "args": args,
            "label": "上市",
            "roles": [],
            "stage": "上市准备",
            "weeks": 0,
            "cost": 80 if p["kind"] == "generic" else 180,
            "chance": None,
            "ok": error is None,
            "error": error,
        }
    if p["status"] == "result" and not p["results"][-1]["passed"]:
        return None
    target = {**p, "index": p["index"] + 1, "status": "ready"} if p["status"] == "result" else p
    stage = sc.stage_key(target)
    team, mode = recommended_team(s, target)
    plan = "focused" if stage == "III" and p.get("population") == "focused" else "standard"
    command = "continue_and_run" if p["status"] == "result" else "run_phase"
    args = {"project": p["id"], "heroes": team, "plan": plan, "mode": mode}
    simulated, error = _try(s, command, args)
    plan_view = {"weeks": None, "cost": None, "chance": None, "level": None}
    if simulated is not None:
        execution = next(q for q in simulated["projects"] if q["id"] == p["id"])["execution"]
        plan_view = {
            "weeks": execution["weeks"],
            "cost": execution["cost"],
            "chance": chance_range(execution["probability"]),
            "level": level(execution["probability"]),
        }
    return {
        "command": command,
        "args": args,
        "label": ("继续：" if p["status"] == "result" else "开工：") + STAGES[stage]["name"],
        "roles": [] if mode == "cro" else list(STAGES[stage]["roles"]),
        "stage": STAGES[stage]["name"],
        **plan_view,
        "ok": error is None,
        "error": error,
    }


def _strongest_free(s, profession, minimum=0):
    options = [h for h in free_heroes(s) if h["profession"] == profession and ability(h) >= minimum]
    return max(options, key=ability) if options else None


def advice(s, p):
    """研究顾问：在关键时刻提示真正有用的打法。

    只读公开证据（候选的证据范围和门槛），不读隐藏真值，也不抽新的随机数。
    边界测试里，按证据挑候选并对获益做定向优化，阿尔茨海默获批从 2/40 变成 23/40；
    游戏以前没有告诉玩家这一点。
    """
    if p["kind"] != "innovative" or p["status"] != "ready" or p.get("experiment") or p.get("chosen") is None:
        return []
    tips = []
    c = sc.selected(p)
    remaining = PATHS["innovative"][p["index"] :]
    effect_gate = max((sc.limits(p, k).get("effect", 0) for k in remaining), default=0)
    margin = c["belief"]["effect"]["mean"] - effect_gate
    now = sc.outlook(p)
    lead = _strongest_free(s, "bio")
    if effect_gate and p["index"] < 2 and margin < 9 and c["optimized"] < 2 and c["checks"].get("refineeffect", 0) == 0:
        gap = f"还差 {pts(-margin)}" if margin < 0 else f"只高出 {pts(margin)}"
        text = f"获益离后期门槛{gap}。临床前先做一次定向优化·获益，后面每一期都更有把握。"
        tip = {"kind": "refine", "text": text, "command": None, "args": None, "ok": False, "after": None}
        if lead:
            delta = 3 + power(s, [lead["id"]], "bio") / 20
            probe = copy.deepcopy(p)
            pc = sc.selected(probe)
            pc["belief"]["effect"]["mean"] = min(98, pc["belief"]["effect"]["mean"] + delta)
            pc["belief"]["safety"]["mean"] = max(10, pc["belief"]["safety"]["mean"] - delta / 2)
            after = sc.outlook(probe)
            args = {"project": p["id"], "method": "refine", "stat": "effect", "heroes": [lead["id"]]}
            _, error = _try(s, "experiment", args)
            spec = EXPERIMENTS["refine"]
            tip.update(
                command="experiment",
                args=args,
                ok=error is None,
                error=error,
                text=text + f"按公开证据，后续全部通过的机会约从 {round(now * 100)}% 到 {round(after * 100)}%。",
                label=f"定向优化·获益 · {spec['weeks']} 周 · ¥{spec['cost']} 万 · {lead['name']}",
                after=round(after * 100),
            )
        else:
            tip["text"] = text + "需要一位空闲的生物伙伴。"
        tips.append(tip)
    clinical = max((ability(h) for h in s["heroes"] if h["employed"] and h["profession"] == "clinical"), default=0)
    marker_lead = _strongest_free(s, "bio", 55)
    if (
        p["index"] <= PATHS["innovative"].index("II")
        and c["marker"]["observations"] == 0
        and margin < 15
        and marker_lead
        and clinical >= 55
    ):
        args = {"project": p["id"], "method": "marker", "stat": "effect", "heroes": [marker_lead["id"]]}
        _, error = _try(s, "experiment", args)
        spec = EXPERIMENTS["marker"]
        tips.append(
            {
                "kind": "marker",
                "text": (
                    "可以先做人群分层研究：如果找到获益更好的人群，III 期能分层入组，获益门槛更容易过。"
                    "结果也可能不支持分层。"
                ),
                "command": "experiment",
                "args": args,
                "ok": error is None,
                "error": error,
                "label": f"人群分层研究 · {spec['weeks']} 周 · ¥{spec['cost']} 万 · {marker_lead['name']}",
                "after": None,
            }
        )
    if p["index"] >= 2 and now < 0.15:
        tips.append(
            {
                "kind": "stop",
                "text": (
                    f"按公开证据，后续全部通过的机会约 {round(now * 100)}%。可以考虑授权或止损，把钱留给下一个项目。"
                ),
                "command": None,
                "args": None,
                "ok": False,
                "after": None,
            }
        )
    return tips


def view(s):
    """Suggestions shown next to the buttons they prefill."""
    return {
        "services": service_picks(s),
        "screen": {kind: screening_team(s, kind) for kind in ("generic", "improved", "innovative")},
        "idle": [h["id"] for h in free_heroes(s)],
    }
