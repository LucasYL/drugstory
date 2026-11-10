"""Evidence-only playtester. No cash/stat injection or access to candidate truth."""

from __future__ import annotations

import copy

from . import economy as e
from . import engine as g
from . import incidents, investments, skills
from . import science as sc
from .content import CATALOG, CLINICAL, FACILITIES, PATHS, ROSTER, STATS
from .model import ACTIVE, ability, busy, committed, new_game
from .view import recommended_team


def attempt(s, command, **args):
    try:
        return g.execute(s, command, args)
    except ValueError:
        return None


def use_skills(s, cash):
    """证据型玩家用主动技能：决定卡上能用的就用（留足周转金），产品和带教类技能有机会就用。"""
    for p in s["projects"]:
        for k in skills.usable(s, p):
            if cash > k["cost"] + 800:
                result = attempt(s, "use_skill", **k["args"])
                if result:
                    return result
    for h in s["heroes"]:
        if not h["employed"] or "active" not in skills.talents.ABILITIES.get(h["id"], {}):
            continue
        a = skills.view(s, h)
        if a["scope"] in ("product", "none") and a["choices"] and cash > a["cost"] + 800:
            result = attempt(s, "use_skill", **a["choices"][0]["args"])
            if result:
                return result
    return None


SURPLUS = 8000  # 可用现金超过这个数，才把多余的钱花在长远投入上
RESERVE = 3000  # 花完以后至少留下


def spend_surplus(s, cash):
    """证据型玩家的花钱顺序：产线 → 病房 → 学者计划 → 患者援助。只看公开数据。"""
    if cash <= SURPLUS:
        return None
    room = cash - RESERVE
    own = sorted(
        (d for d in s["products"] if d["active"] and not d["partner"]), key=lambda d: (-d["last_revenue"], d["id"])
    )
    for d in own:
        if investments.line_problem(s, d) is None and investments.line_cost(s, d) <= room:
            return attempt(s, "build_line", product=d["id"])
    if investments.ward_problem(s) is None and room >= investments.WARD_COST:
        return attempt(s, "build_ward")
    if investments.fellowship_problem(s) is None and room >= investments.FELLOWSHIP_COST:
        return attempt(s, "fund_fellowship")
    for d in own:
        if not d.get("access"):
            return attempt(s, "access_program", product=d["id"], on=1)
    return None


def choose(s, novice=False, remaining=960):
    cash = s["cash"] - committed(s)
    if not novice and (result := use_skills(s, cash)):
        return result
    if not novice and (result := spend_surplus(s, cash)):
        return result
    for p in s["projects"]:
        pid, status = p["id"], p["status"]
        if status == "checkpoint":
            return g.execute(s, "trial_decision", {"project": pid, "choice": "keep"})
        if status == "selecting":
            scores = []
            for i in range(len(p["candidates"])):
                probe = copy.copy(p)
                probe["chosen"] = i
                scores.append(sc.outlook(probe))
            return g.execute(
                s, "choose_candidate", {"project": pid, "candidate": 1 if novice else scores.index(max(scores))}
            )
        if status == "result":
            if sc.stage_key(p) == "review":
                result = attempt(s, "launch", project=pid)
                if result:
                    return result
            elif s["scenario"] == "licensing" and (q := e.quote(s, p, "cash")):
                if novice or q["upfront"] >= 450:
                    return g.execute(s, "license_project", {"project": pid, "terms": "cash"})
            else:
                return g.execute(s, "continue_project", {"project": pid})
        if status == "problem":
            for option in incidents.options(s, p):
                if option["command"] == "rework_expert" and option["ok"]:
                    result = attempt(s, "rework_expert", **option["args"])
                    if result:
                        return result
            ids = [
                h["id"]
                for h in s["heroes"]
                if h["employed"] and h["id"] not in busy(s) and h["profession"] in ("chem", "proc")
            ][:2]
            result = attempt(s, "rework", project=pid, heroes=ids)
            if result:
                return result
            return g.execute(s, "terminate", {"project": pid})
        if status == "ready":
            ids, mode = recommended_team(s, p)
            key, candidate = sc.stage_key(p), sc.selected(p)
            if not novice and p["index"] < 2 and cash > 550 and candidate["optimized"] < 2:
                # Pick the weakest supported property; subsequent clinical evidence can still invalidate it.
                margins = {
                    stat: candidate["belief"][stat]["mean"]
                    - max((sc.limits(p, k).get(stat, 0) for k in PATHS[p["kind"]]), default=0)
                    for stat in STATS
                }
                stat = min(margins, key=margins.get)
                role = sc.STAT_ROLE[stat]
                team = [
                    h["id"] for h in s["heroes"] if h["employed"] and h["profession"] == role and h["id"] not in busy(s)
                ][:1]
                if margins[stat] < 9 and candidate["checks"].get("refine" + stat, 0) == 0:
                    result = attempt(s, "experiment", project=pid, method="refine", stat=stat, heroes=team)
                    if result:
                        return result
            # Avoid paying for a low-evidence late program merely to improve a bot's launch count.
            if not novice and key in ("II", "III") and sc.outlook(p) < 0.10:
                return g.execute(s, "terminate", {"project": pid})
            plan = "focused" if key == "III" and p["population"] == "focused" else "standard"
            if not novice and key in CLINICAL and cash > 2000 and plan != "focused":
                estimate = sc.plan_phase(s, p, ids, "standard", mode)
                if sc.phase_probability(p, key, "standard", estimate["noise_by_stat"]) >= 0.65:
                    plan = "expanded"
            result = attempt(s, "run_phase", project=pid, heroes=ids, plan=plan, mode=mode)
            if result:
                return result
        if status in ("ready", "result") and not p.get("deferred"):
            return g.execute(s, "defer", {"project": pid})

    employed = [h for h in s["heroes"] if h["employed"]]
    owned = {h["profession"] for h in employed}
    free = [h for h in employed if h["id"] not in busy(s)]
    products = [d for d in s["products"] if not d["partner"] and d["active"]]
    if "proc" not in owned and cash > 500:
        return g.execute(s, "hire", {"character": "pill"})
    missing = [prof for prof in ("tox", "clinical", "bio", "chem") if prof not in owned]
    if missing and len(products) >= (1 if missing[0] == "tox" else 2) and cash > 900:
        key = next(key for key, c in ROSTER.items() if c["profession"] == missing[0] and c["tier"] == 1)
        result = attempt(s, "hire", character=key)
        if result:
            return result
    for h in free:
        if h["rank"] < 4 and all(ok for _, ok in e.promotion_requirements(s, h)) and cash > 900:
            result = attempt(s, "promote", character=h["id"])
            if result:
                return result
    if (
        s["facility"] < (2 if novice else 3)
        and len(products) >= 2
        and cash > FACILITIES[s["facility"] + 1]["cost"] + (2400 if products else 3000)
    ):
        return g.execute(s, "upgrade")

    active = [p for p in s["projects"] if p["status"] in ACTIVE]
    if len(active) < (1 if novice else 2) and cash > 650:
        generic_owned = sum(d["kind"] == "generic" for d in products)
        priority = ["generic"]
        if generic_owned >= 3:
            priority = (
                ["improved", "innovative", "generic"]
                if s["scenario"] in ("foundation", "platform")
                else ["innovative", "generic", "improved"]
            )
        if generic_owned >= 5:
            priority = ["innovative", "improved", "generic"]
        if any(d["kind"] == "generic" and not e.catalog_in_market(s, d["catalog"]) for d in products):
            priority = ["generic", "improved", "innovative"]
        for kind in priority:
            if kind != "generic" and cash < (2200 if kind == "innovative" else 1100):
                continue
            choices = [
                c for c in CATALOG.values() if c["kind"] == kind and (kind != "innovative" or "__" not in c["key"])
            ]
            # Rotate therapeutic areas, so repeated launches do not sidestep market crowding.
            choices.sort(key=lambda c: sum(p["catalog"] == c["key"] for p in s["projects"]))
            for spec in choices:
                roles = ("proc", "chem") if kind != "innovative" else ("bio", "chem")
                team = [h["id"] for h in free if h["profession"] in roles][:2]
                result = attempt(s, "start_project", catalog=spec["key"], heroes=team)
                if result:
                    return result

    if cash > 6000:
        for profession in ("bio", "chem", "proc"):
            if s["equipment"][profession] < 2:
                result = attempt(s, "upgrade_equipment", profession=profession)
                if result:
                    return result
    # Invite visibly stronger specialists after meeting the published conditions.
    if not novice and cash > 4200 and len(employed) < 8:
        for key, spec in sorted(ROSTER.items(), key=lambda pair: -pair[1]["tier"]):
            if spec["tier"] < 2 or any(h["id"] == key for h in employed):
                continue
            best = max((ability(h) for h in employed if h["profession"] == spec["profession"]), default=0)
            if spec["ability"] < best + 8 or not all(ok for _, ok in e.recruit_requirements(s, key)):
                continue
            if spec["tier"] >= 3 and key not in s["connections"]:
                for h in free:
                    if h["profession"] == spec["profession"]:
                        result = attempt(s, "collaborate", character=key, researcher=h["id"])
                        if result:
                            return result
            else:
                result = attempt(s, "hire", character=key)
                if result:
                    return result
    # Training advances ability, but cannot substitute for the project cases required by promotion.
    if cash > 1200:
        for h in free:
            target = 55 if h["rank"] >= 2 else 44
            if ability(h) < target:
                result = attempt(s, "train", character=h["id"])
                if result:
                    return result
    for offer in e.orders(s):
        if not offer["taken"]:
            options = [h for h in free if h["profession"] == offer["profession"]]
            if options:
                result = attempt(s, "take_service", order=offer["id"], character=options[0]["id"])
                if result:
                    return result
    # A conservative operator can reduce optional headcount if the fixed cost is no longer sustainable.
    if cash < 180 and not active:
        for h in sorted(free, key=lambda h: h["rank"], reverse=True):
            if h["profession"] not in ("proc", "chem") and len(employed) > 2:
                result = attempt(s, "dismiss", character=h["id"])
                if result:
                    return result
    return g.execute(s, "advance", {"weeks": 48 if remaining >= 48 else 4 if remaining >= 4 else 1})


def play(seed=42, scenario="foundation", novice=False, weeks=960):
    s = new_game(seed, scenario)
    for _ in range(4000):
        if s["week"] >= weeks or s["game_over"]:
            return s
        s = choose(s, novice, weeks - s["week"])
    raise RuntimeError("Bot did not advance within 4000 decisions")
