"""Transactional player actions and one shared weekly simulation."""

from __future__ import annotations

import copy
import inspect

from . import challenge, development, events, honors, patents, product_design, readouts, stories, trial_choices
from . import economy as e
from . import science as sc
from .content import CATALOG, CLINICAL, FACILITIES, PATHS, PLANS, PROMOTION, RANKS, ROSTER, STAGES, STATS
from .model import (
    ACTIVE,
    DECISIONS,
    ability,
    available_money,
    busy,
    check,
    earn,
    find,
    free_team,
    gain_work,
    hero,
    log,
    new_game,
    payroll,
    power,
    spend,
)


def catalog_requirements(s, key):
    spec = CATALOG[key]
    checks = [("市场进入时间已到", s["week"] >= spec["available_week"])]
    if spec["kind"] == "improved":
        prof = spec["profession"]
        checks += [
            ("相关专业知识 15", s["knowledge"][prof] >= 15),
            (
                "制剂或药代能力 50",
                any(h["employed"] and h["profession"] == prof and ability(h) >= 50 for h in s["heroes"]),
            ),
        ]
    if spec["difficulty"]:
        checks += [
            ("生物或药化知识 45", max(s["knowledge"]["bio"], s["knowledge"]["chem"]) >= 45),
            ("专业研究院", s["facility"] >= 2),
            (
                "一位生物或药化大师",
                any(h["employed"] and h["rank"] >= 3 and h["profession"] in ("bio", "chem") for h in s["heroes"]),
            ),
        ]
    if spec["kind"] == "innovative":
        checks += [
            (f"科研知识 {spec['knowledge']}", max(s["knowledge"]["bio"], s["knowledge"]["chem"]) >= spec["knowledge"]),
            (
                f"药化或生物设备 {spec['equipment_level']} 级",
                max(s["equipment"]["bio"], s["equipment"]["chem"]) >= spec["equipment_level"],
            ),
        ]
    return checks


def start_project(s, catalog: str, heroes: list, design: str = "standard", work_focus: str = "balanced"):
    check(work_focus in development.FOCUSES, "请选择开发重心")
    check(design in ("standard", "validated"), "请选择产品验证路线")
    check(design == "standard" or product_design.profile(catalog), "该方案没有专项产品验证路线")
    check(catalog in CATALOG, "请选择研究路线")
    check(all(ok for _, ok in catalog_requirements(s, catalog)), "还没有满足这条路线的研究条件")
    check(not any(p["catalog"] == catalog and p["status"] in ACTIVE for p in s["projects"]), "同一方案已有在研计划")
    check(not e.catalog_in_market(s, catalog), "该方案已有在售产品，请探索不同方案或等待换代窗口")
    free_team(s, heroes)
    c = CATALOG[catalog]
    relevant = ("proc", "chem") if c["kind"] != "innovative" else ("bio", "chem")
    check(max(power(s, heroes, prof) for prof in relevant) >= 25, "需要有对应专业的发现或制剂负责人")
    available_money(s, 70)
    spend(s, 70, "discovery")
    pid = str(s["next_id"])
    s["next_id"] += 1
    p = {
        "id": pid,
        "name": c["name"],
        "catalog": catalog,
        "design": design,
        "work_focus": work_focus,
        "readings": [],
        "kind": c["kind"],
        "status": "screening",
        "started": s["week"],
        "ended": None,
        "index": 0,
        "candidates": [],
        "chosen": None,
        "team": heroes,
        "contributors": list(heroes),
        "left": 8,
        "cost_per_week": 0,
        "spent": 70.0,
        "results": [],
        "repairs": 0,
        "population": "standard",
        "mode": "internal",
        "entered_I": None,
        "clinical_started": False,
        "experiment": None,
        "feedback": "正在筛选候选与整理参比资料。",
    }
    sc.generate_candidates(s, p)
    s["projects"].append(p)
    log(s, f"启动 {p['name']}：8 周筛选，费用 ¥70 万。")


def choose_candidate(s, project: str, candidate: int):
    p = find(s["projects"], project)
    check(
        p["status"] == "selecting" and type(candidate) is int and 0 <= candidate < len(p["candidates"]),
        "请从当前候选中选择",
    )
    p["chosen"], p["status"] = candidate, "ready"
    p["deferred"] = False
    p["feedback"] = "候选已确定。先看证据与未知项，再决定是否投入下一阶段。"


def internal_usage(s):
    return sum(p["clinical_started"] and p["mode"] == "internal" and p["status"] in ACTIVE for p in s["projects"])


def run_phase(s, project: str, heroes: list, plan: str = "standard", mode: str = "internal"):
    p = find(s["projects"], project)
    check(p["status"] == "ready", "这个项目还不能开始下一阶段")
    check(plan in PLANS and mode in ("internal", "cro"), "请选择正确的研究方案")
    key = sc.stage_key(p)
    cro = mode == "cro"
    check(not cro or key in CLINICAL, "外部 CRO 承担临床研究；这一阶段请安排本公司对应专业负责人")
    free_team(s, heroes, allow_empty=cro)
    if key in CLINICAL:
        check(power(s, heroes, "clinical", cro) >= 28, "临床阶段需要临床负责人，或选择外部 CRO")
        if not cro and not (p["clinical_started"] and p["mode"] == "internal"):
            check(internal_usage(s) < FACILITIES[s["facility"]]["slots"], "自营临床席位已满，可等待或选择 CRO")
    else:
        check(
            max(power(s, heroes, role) for role in STAGES[key]["roles"]) >= 25,
            "需要本阶段对应专业的负责人；CRO 只提供临床能力",
        )
    if plan == "focused":
        check(key in ("II", "III") and sc.focused_available(s, p, heroes), "需要有效的分层证据和临床能力 55")
    if key == "II":
        p["population"] = "focused" if plan == "focused" else "standard"
    if key == "III":
        check((plan == "focused") == (p["population"] == "focused"), "III 期须延续 II 期确定的人群")
    execution = sc.plan_phase(s, p, heroes, plan, mode)
    available_money(s, execution["cost"])
    p.update(
        status="running",
        team=heroes,
        left=execution["weeks"],
        execution=execution,
        cost_per_week=execution["cost"] / execution["weeks"],
        mode=mode,
    )
    development.initialize(s, p)
    readouts.initialize(p)
    trial_choices.initialize(p)
    p["deferred"] = False
    p["contributors"] = sorted(set(p["contributors"] + heroes))
    if key in CLINICAL:
        p["clinical_started"] = True
    if key == "I" and p["entered_I"] is None:
        p["entered_I"] = s["week"]
    events.emit(
        s,
        "phase_started",
        actors=heroes,
        project=p["id"],
        room=STAGES[key]["room"],
        data={
            "name": p["name"],
            "stage": STAGES[key]["name"],
            "weeks": execution["weeks"],
            "executor": mode,
            "note": "，由外包 CRO 执行" if cro else "",
        },
    )


def continue_project(s, project: str):
    p = find(s["projects"], project)
    check(p["status"] == "result" and p["results"][-1]["passed"], "先查看本阶段结果")
    check(p["index"] + 1 < len(PATHS[p["kind"]]), "已完成审评，请安排上市")
    p["index"] += 1
    p["status"] = "ready"


def experiment(s, project: str, method: str, stat: str, heroes: list):
    p = find(s["projects"], project)
    free_team(s, heroes)
    plan = sc.experiment_plan(s, p, method, stat, heroes)
    available_money(s, plan["cost"])
    p.update(
        status="running", experiment=plan, team=heroes, left=plan["weeks"], cost_per_week=plan["cost"] / plan["weeks"]
    )
    p["deferred"] = False
    p["contributors"] = sorted(set(p["contributors"] + heroes))
    log(s, f"{p['name']}安排{plan['name']}，需要 {plan['weeks']} 周。")


def finish_case(s, p):
    # Project-level credit is awarded once, including honest negative results and disclosed licensing.
    if p.get("credited"):
        return
    p["credited"] = True
    ids = [key for key in p["contributors"] if any(h["id"] == key and h["employed"] for h in s["heroes"])]
    if p["results"]:
        gain_work(s, ids, "case-" + p["catalog"], 6, p["id"])
    p["ended"] = s["week"]


def terminate(s, project: str):
    p = find(s["projects"], project)
    check(p["status"] in ACTIVE, "项目已经结束")
    p["status"] = "terminated"
    p["cost_per_week"] = 0
    finish_case(s, p)
    log(s, f"终止 {p['name']}。已取得的证据保留，诚实止损不扣口碑。")


def defer(s, project: str, waiting: int = 1):
    p = find(s["projects"], project)
    check(p["status"] in DECISIONS and waiting in (0, 1), "只能暂缓等待决策的项目")
    p["deferred"] = bool(waiting)
    log(s, f"{p['name']}已{'暂缓决策，可推进其他业务' if waiting else '恢复提醒'}。未开工阶段不收研发费。")


def switch_candidate(s, project: str, candidate: int):
    p = find(s["projects"], project)
    check(p["status"] in ("ready", "problem") and p["index"] < 2, "临床前早期才可更换候选")
    check(
        type(candidate) is int and 0 <= candidate < len(p["candidates"]) and candidate != p["chosen"], "请选择另一候选"
    )
    used = p.setdefault("used_candidates", [p["chosen"]])
    check(candidate not in used, "已经放弃的候选不能来回切换刷结果")
    available_money(s, 60)
    spend(s, 60, "research")
    p["spent"] += 60
    s["research_archive"].append({"project": project, "candidate": p["chosen"], "results": copy.deepcopy(p["results"])})
    used.append(candidate)
    p.update(chosen=candidate, index=0, status="ready", results=[], repairs=0)
    log(s, f"{p['name']}改用另一候选，需要重新验证；原候选的证据保留。")


def rework(s, project: str, heroes: list):
    p = find(s["projects"], project)
    check(p["status"] == "problem" and p["repairs"] < 1, "没有可以补正的工艺或等效性问题")
    free_team(s, heroes)
    check(max(power(s, heroes, "proc"), power(s, heroes, "chem")) >= 35, "补正需要制剂或药化能力 35")
    available_money(s, 100)
    p.update(
        status="running",
        team=heroes,
        left=8,
        cost_per_week=12.5,
        experiment={"kind": "rework", "stat": p["results"][-1]["failures"][0]},
    )
    p["deferred"] = False
    p["contributors"] = sorted(set(p["contributors"] + heroes))


def launch(s, project: str, name: str = ""):
    p = find(s["projects"], project)
    check(
        p["status"] == "result" and p["results"][-1]["key"] == "review" and p["results"][-1]["passed"],
        "需要先通过上市审评",
    )
    check(isinstance(name, str) and len(name.strip()) <= 30, "药名请控制在 30 个字以内")
    available_money(s, 80 if p["kind"] == "generic" else 180)
    launch_cost = 80 if p["kind"] == "generic" else 180
    spend(s, launch_cost, "launch")
    p["spent"] += launch_cost
    p["status"] = "approved"
    d = e.make_product(s, p, name=name.strip() or p["name"])
    finish_case(s, p)
    events.emit(
        s,
        "product_launched",
        actors=list(p["contributors"]),
        project=p["id"],
        room=STAGES["review"]["room"],
        data={
            "name": d["name"],
            "kind": p["kind"],
            "text": "采用委托生产，收入随市场导入逐步形成；角色履历与公司口碑提升。",
        },
    )


def license_project(s, project: str, terms: str):
    p = find(s["projects"], project)
    quote = e.quote(s, p, terms)
    check(quote is not None, "当前证据或阶段还没有可接受的授权报价")
    available_money(s, max(0, quote["owner_commitment"] - quote["upfront"]))
    earn(s, quote["upfront"], "upfront")
    p["status"] = "licensed"
    p["index"] += 1
    d = {
        **quote,
        "id": f"deal-{project}",
        "project": project,
        "status": "developing",
        "signed": s["week"],
        "partner": "青岚伙伴" if int(project) % 2 else "远星伙伴",
        "paid": [],
        "royalties": 0.0,
        "weekly_royalty": 0.0,
        "owner_spent": 0.0,
        "received_milestones": 0.0,
    }
    s["deals"].append(d)
    start_partner_phase(s, p, d)
    finish_case(s, p)
    s["reputation"] += 3
    events.emit(
        s,
        "deal_signed",
        project=p["id"],
        data={"name": p["name"], "terms": quote["name"], "upfront": quote["upfront"], "partner": d["partner"]},
    )


def start_partner_phase(s, p, d):
    key = sc.stage_key(p)
    plan = "focused" if p["population"] == "focused" and key in ("II", "III") else "standard"
    d["execution"] = sc.plan_phase(s, p, [], plan, key=key, partner=True)
    d["left"] = d["execution"]["weeks"]
    d["cost_per_week"] = d["execution"]["cost"] / d["left"]
    d["remaining_cost"] = sum(
        sc.plan_phase(s, p, [], plan=plan if k in ("II", "III") else "standard", key=k, partner=True)["cost"]
        for k in PATHS[p["kind"]][p["index"] :]
    )
    if key == "I" and p["entered_I"] is None:
        p["entered_I"] = s["week"]


def hire(s, character: str):
    check(character in ROSTER, "没有这个角色")
    check(not any(h["id"] == character and h["employed"] for h in s["heroes"]), "角色已在公司")
    check(all(ok for _, ok in e.recruit_requirements(s, character)), "还未满足角色加入条件")
    check(ROSTER[character]["tier"] < 3 or character in s["connections"], "先完成这位专家的合作课题")
    check(headcount(s) + 3 <= FACILITIES[s["facility"]]["capacity"], "场地容纳不下新团队，请先扩建")
    cost = e.recruit_cost(character)
    available_money(s, cost)
    spend(s, cost, "recruitment")
    prior = next((h for h in s["heroes"] if h["id"] == character), None)
    if prior:
        prior["employed"] = True
    else:
        from .model import make_hero

        s["heroes"].append(make_hero(character))
    log(s, f"{RANKS[ROSTER[character]['tier']]}·{ROSTER[character]['name']}加入研究社。")


def dismiss(s, character: str):
    h = hero(s, character)
    check(character not in busy(s), "先完成正在负责的任务")
    check(sum(h["employed"] for h in s["heroes"]) > 1, "至少保留一位角色维持公司")
    cost = 25 * h["rank"]
    available_money(s, cost)
    spend(s, cost, "severance")
    h["employed"] = False
    log(s, f"{h['name']}暂离公司，履历保留，可以在满足条件时重新邀请。")


def headcount(s):
    return sum(h["members"] + 1 for h in s["heroes"] if h["employed"])


def resize(s, character: str, members: int):
    h = hero(s, character)
    check(type(members) is int and 0 <= members <= 6, "成员人数应为 0 至 6")
    check(character not in busy(s), "任务期间暂不改变团队配置")
    check(headcount(s) - h["members"] + members <= FACILITIES[s["facility"]]["capacity"], "场地容量不足")
    cost = abs(members - h["members"]) * 4
    available_money(s, cost)
    spend(s, cost, "staffing")
    h["members"] = members


def train(s, character: str):
    h = hero(s, character)
    free_team(s, [character])
    check(ability(h) < [0, 48, 66, 83, 97][h["rank"]], "当前阶位能力已接近上限，需要真实项目和晋阶")
    cost = 40 + h["rank"] * 20
    available_money(s, cost)
    spend(s, cost, "training")
    s["jobs"].append({"kind": "train", "name": h["name"] + "专业培训", "heroes": [character], "left": 6})


def promote(s, character: str):
    h = hero(s, character)
    free_team(s, [character])
    check(h["rank"] < 4 and all(ok for _, ok in e.promotion_requirements(s, h)), "还未满足晋阶所需经验、履历或平台")
    cost = PROMOTION[h["rank"] + 1]["cost"]
    available_money(s, cost)
    spend(s, cost, "promotion")
    h["rank"] += 1
    events.emit(s, "character_promoted", actors=[character], data={"name": h["name"], "rank": RANKS[h["rank"]]})


def mentor(s, teacher: str, pupil: str):
    a, b = hero(s, teacher), hero(s, pupil)
    free_team(s, [teacher, pupil])
    check(
        a["rank"] >= 2 and a["rank"] > b["rank"] and a["profession"] == b["profession"],
        "需要同专业、阶位更高的精英或以上导师",
    )
    check(teacher not in b["mentored"], "这位导师的入门课题已经完成")
    available_money(s, 60)
    spend(s, 60, "training")
    s["jobs"].append({"kind": "mentor", "name": a["name"] + "带教" + b["name"], "heroes": [teacher, pupil], "left": 10})


def collaborate(s, character: str, researcher: str):
    check(character in ROSTER and ROSTER[character]["tier"] >= 3, "请选择尚未加入的高阶专家")
    check(
        character not in s["connections"] and not any(j.get("target") == character for j in s["jobs"]),
        "合作已经完成或正在进行",
    )
    check(all(ok for _, ok in e.recruit_requirements(s, character)), "尚未达到合作所需的平台与成果")
    free_team(s, [researcher])
    h = hero(s, researcher)
    check(h["profession"] == ROSTER[character]["profession"] and ability(h) >= 45, "需要同专业能力 45 的合作负责人")
    available_money(s, 120)
    spend(s, 120, "collaboration")
    s["jobs"].append(
        {
            "kind": "connect",
            "name": "与" + ROSTER[character]["name"] + "联合课题",
            "heroes": [researcher],
            "target": character,
            "left": 10,
        }
    )


def take_service(s, order: str, character: str):
    offer = next((o for o in e.orders(s) if o["id"] == order), None)
    check(offer is not None and not offer["taken"], "该订单已接受或已经过期")
    free_team(s, [character])
    h = hero(s, character)
    check(h["profession"] == offer["profession"] and ability(h) >= offer["requirement"], "专业或能力不符合交付要求")
    available_money(s, offer["cost"])
    spend(s, offer["cost"], "service_cost")
    s["service_orders"].append(order)
    s["jobs"].append(
        {
            "kind": "service",
            "name": offer["name"],
            "heroes": [character],
            "left": offer["weeks"],
            "profession": offer["profession"],
            "reward": offer["reward"],
        }
    )


def upgrade(s):
    check(s["facility"] < len(FACILITIES) - 1, "已是最高场地")
    c = FACILITIES[s["facility"] + 1]
    available_money(s, c["cost"])
    spend(s, c["cost"], "facility")
    s["facility"] += 1
    events.emit(s, "facility_upgraded", data={"name": c["name"], "level": s["facility"], "rent": c["rent"]})


def finish_phase(s, p):
    result = sc.evaluate(s, p, p["execution"], p["repairs"])
    p["results"].append(result)
    key = result["key"]
    events.emit(
        s,
        "phase_finished",
        actors=p["team"],
        project=p["id"],
        room=STAGES[key]["room"],
        data={
            "name": p["name"],
            "stage": STAGES[key]["name"],
            "passed": result["passed"],
            "executor": p.get("mode", "internal") if key in CLINICAL else "internal",
            "outcome": "取得支持证据" if result["passed"] else "未取得支持证据",
        },
        journal=False,
    )
    gain_work(s, p["team"], p["catalog"] + "-" + key, 6 if key in CLINICAL else 5)
    if result["passed"]:
        p["status"] = "result"
        s["milestones"] += 1
        patents.maybe_file(s, p, key)
        p["feedback"] = f"{STAGES[key]['name']}完成，取得本阶段支持证据；后续阶段仍有新的未知项。"
        log(s, p["name"] + "：" + p["feedback"])
    else:
        failures = result["failures"]
        repairable = set(failures) <= {"quality", "exposure"} and (p["kind"] == "generic" or key == "review")
        close = all(result["values"][stat] >= result["limits"][stat] - 9 for stat in failures)
        p["status"] = "problem" if repairable and close and p["repairs"] < 1 else "failed"
        p["feedback"] = "本次未建立足够证据：" + "、".join(STATS[k] for k in failures)
        p["feedback"] += (
            "。可补正一次，须改善实际工艺再验证。"
            if p["status"] == "problem"
            else "。保留研究记录与角色经验，建议停止这一候选并评估其他路线。"
        )
        if p["status"] == "failed":
            finish_case(s, p)
        log(s, p["name"] + "：" + p["feedback"])
    p["cost_per_week"] = 0


def partner_step(s):
    for d in s["deals"]:
        if d["status"] != "developing":
            continue
        p = find(s["projects"], d["project"])
        charge = d["cost_per_week"] * d["cost_share"]
        spend(s, charge, "codevelopment")
        d["owner_spent"] += charge
        d["remaining_cost"] = max(0, d["remaining_cost"] - d["cost_per_week"])
        d["left"] -= 1
        if d["left"] > 0:
            continue
        result = sc.evaluate(s, p, d["execution"])
        p["results"].append(result)
        key = result["key"]
        # Each contract delivers each phase's report exactly once, not repeated royalty XP.
        for prof in STAGES[key]["roles"]:
            s["knowledge"][prof] += 2
        if not result["passed"]:
            d.update(status="failed", remaining_cost=0, cost_per_week=0)
            log(s, f"授权反馈：{p['name']}在{STAGES[key]['name']}未获支持证据。首付款保留，后续未触发款项不支付。")
            continue
        milestone = {"I": "human_milestone", "II": "proof_milestone", "review": "approval_milestone"}.get(key)
        if milestone and milestone not in d["paid"]:
            earn(s, d[milestone], "milestones")
            d["received_milestones"] += d[milestone]
            d["paid"].append(milestone)
        s["milestones"] += 1
        if key == "review":
            d.update(status="approved", remaining_cost=0, cost_per_week=0)
            e.make_product(s, p, partner=True)
            s["reputation"] += 5
            log(s, f"授权产品 {p['name']}获批，成功里程碑到账，开始按销售额收取分成。")
        else:
            p["index"] += 1
            start_partner_phase(s, p, d)
            log(s, f"授权反馈：{p['name']}完成{STAGES[key]['name']}，合作方继续开发。")


def advance(s, weeks: int = 4):
    check(type(weeks) is int and weeks in (1, 4, 48), "可推进 1 周、4 周或下一件事")
    check(
        not any(p["status"] in DECISIONS and not p.get("deferred") for p in s["projects"]),
        "先处理或暂缓待决定项目，再推进时间",
    )
    for _ in range(weeks):
        s["week"] += 1
        spend(s, payroll(s), "payroll")
        spend(s, FACILITIES[s["facility"]]["rent"], "rent")
        spend(s, challenge.upkeep(s), "platform_maintenance")
        spend(s, development.upkeep(s), "equipment_upkeep")
        for job in list(s["jobs"]):
            job["left"] -= 1
            if job["left"] <= 0:
                e.finish_job(s, job)
                s["jobs"].remove(job)
        for p in s["projects"]:
            if p["status"] not in ("screening", "running"):
                continue
            spend(s, p["cost_per_week"], "research")
            p["spent"] += p["cost_per_week"]
            p["left"] -= 1
            if p["status"] == "running" and not p.get("experiment"):
                development.tick(s, p)
                readouts.tick(s, p)
            if p["status"] == "running" and trial_choices.reached(p):
                p["status"] = "checkpoint"
                p["deferred"] = False
                log(s, p["name"] + "到达临床中途检查点，请选择后半程安排。")
            if p["left"] > 0:
                continue
            if p["status"] == "screening":
                p["status"] = "selecting"
                spec = CATALOG[p["catalog"]]
                if spec["kind"] == "innovative":
                    s["notebook"][p["catalog"]] = {
                        "tier": spec["combo_tier"],
                        "reason": spec["combo_reason"],
                        "week": s["week"],
                    }
                log(s, f"{p['name']}的候选资料准备好了。请比较证据和未知项。")
            elif p["experiment"]:
                if p["experiment"]["kind"] == "rework":
                    c = sc.selected(p)
                    stat = p["experiment"]["stat"]
                    c["truth"][stat] = min(98, c["truth"][stat] + 6)
                    c["belief"][stat]["mean"] += 6
                    p["repairs"] += 1
                    message = "工艺补正完成，下一次验证仍需实际投入，不能保证通过。"
                else:
                    message = sc.finish_experiment(s, p)
                gain_work(s, p["team"], p["catalog"] + "-" + p["experiment"]["kind"], 3)
                p.update(status="ready", experiment=None, cost_per_week=0, feedback=message)
                log(s, p["name"] + "：" + message)
            else:
                finish_phase(s, p)
        partner_step(s)
        patents.tick(s)
        e.market_step(s)
        honors.annual(s)
        s["minimum_cash"] = min(s["minimum_cash"], s["cash"])
        if s["week"] % 4 == 0:
            s["negative_months"] = s["negative_months"] + 1 if s["cash"] < 0 else 0
            if s["negative_months"] >= 3:
                s["game_over"] = True
                log(s, "连续三个月月底现金为负，公司停止经营。研究记录保留，可在新局调整路线。")
        if not s["career_done"] and s["week"] >= 960:
            s["career_done"] = True
            log(s, f"二十年经营回顾：当前总分 {e.company_score(s)}，可以继续经营。")
        if s["game_over"] or any(p["status"] in DECISIONS and not p.get("deferred") for p in s["projects"]):
            break


def next_event(s):
    """Stop when someone becomes available, including non-blocking jobs and partner data."""
    remaining = [48 - s["week"] % 48, *[j["left"] for j in s["jobs"]]]
    remaining += [p["left"] for p in s["projects"] if p["status"] in ("screening", "running")]
    remaining += [d["left"] for d in s["deals"] if d["status"] == "developing"]
    for _ in range(min([48, *remaining])):
        prior_event = s["event_seq"]
        advance(s, 1)
        if any(ev["id"] > prior_event and ev["type"] in ("work_completed", "evidence_received") for ev in s["events"]):
            break
        if s["game_over"] or any(p["status"] in DECISIONS and not p.get("deferred") for p in s["projects"]):
            break


def nominate(s, category: str):
    check(category in honors.AWARDS, "请选择年度奖项")
    option = next(c for c in honors.categories(s) if c["key"] == category)
    check(option["eligible"], option["requirement"])
    check(s["week"] % 48 < 46, "本届报名已截止，请准备下一年")
    s["season"]["entry"] = category
    log(s, f"已报名{option['name']}。本年只选一个方向；第 46 周起锁定，年末按实际成果评选。")


def independent_study(s, product: str, heroes: list):
    option = next((v for v in honors.proof_options(s) if v["product"] == product), None)
    check(option is not None and option["available"], "这款产品尚未满足独立验证条件，或已有不能重复的验证结果")
    free_team(s, heroes)
    roles = ("bio", "clinical") if option["step"] == 0 else ("clinical", "tox")
    for role in roles:
        check(
            any(
                hero(s, key)["profession"] == role and hero(s, key)["rank"] >= 3 and ability(hero(s, key)) >= 60
                for key in heroes
            ),
            "需要两位对应专业、能力至少 60 的大师",
        )
    available_money(s, option["cost"])
    spend(s, option["cost"], "independent_research")
    s["jobs"].append(
        {
            "kind": "independent",
            "name": option["name"] + " · " + option["title"],
            "product": product,
            "step": option["step"],
            "heroes": heroes,
            "left": option["weeks"],
        }
    )
    log(s, f"启动{option['title']}：{option['weeks']} 周、¥{option['cost']} 万；阴性结果同样留档。")


def personal_project(s, character: str, partner: str, choice: str):
    stories.begin(s, character, partner, choice)


def trial_decision(s, project: str, choice: str):
    trial_choices.resolve(s, find(s["projects"], project), choice)


def upgrade_equipment(s, profession: str):
    development.upgrade(s, profession)


def continue_and_run(s, project: str, heroes: list, plan: str = "standard", mode: str = "internal"):
    continue_project(s, project)
    run_phase(s, project, heroes, plan, mode)


def take_services(s, assignments: list):
    check(1 <= len(assignments) <= 3, "一次安排一至三个服务订单")
    for item in assignments:
        check(isinstance(item, dict) and set(item) == {"order", "character"}, "请检查订单与角色")
        take_service(s, **item)


COMMANDS = {
    fn.__name__: fn
    for fn in [
        start_project,
        choose_candidate,
        run_phase,
        continue_project,
        experiment,
        terminate,
        defer,
        switch_candidate,
        rework,
        launch,
        license_project,
        hire,
        dismiss,
        resize,
        train,
        promote,
        mentor,
        collaborate,
        take_service,
        upgrade,
        upgrade_equipment,
        advance,
        next_event,
        nominate,
        independent_study,
        personal_project,
        trial_decision,
        continue_and_run,
        take_services,
    ]
}


def execute(state, command, args=None):
    check(isinstance(command, str), "操作名称不正确")
    args = {} if args is None else args
    check(isinstance(args, dict), "操作参数必须是对象")
    if command == "new_game":
        inspect.signature(new_game).bind(**args)
        return new_game(**args)
    if command == "save":
        check(not args, "保存不接受参数")
        return copy.deepcopy(state)
    check(not state["game_over"], "公司已经停止经营，可以查看记录或新开一局")
    check(command in COMMANDS, "没有这个操作")
    fn = COMMANDS[command]
    inspect.signature(fn).bind(state, **args)
    for key, value in args.items():
        hint = fn.__annotations__.get(key)
        expected = {"str": str, "list": list, "int": int}.get(hint)
        check(expected is None or type(value) is expected, "操作参数类型不正确")
    candidate = copy.deepcopy(state)
    candidate["transition_events"] = []
    fn(candidate, **args)
    if abs(candidate["cash"] - state["cash"]) >= 0.01:

        def changes(field):
            before = state[field]
            return {
                k: round(v - before.get(k, 0), 2)
                for k, v in candidate[field].items()
                if abs(v - before.get(k, 0)) >= 0.01
            }

        events.emit(
            candidate,
            "cash_changed",
            data={
                "amount": round(candidate["cash"] - state["cash"], 2),
                "income": changes("income"),
                "expense": changes("expense"),
            },
            journal=False,
        )
    for rank in (2, 3, 4):
        field = f"first_rank{rank}"
        if candidate[field] is None and any(h["employed"] and h["rank"] >= rank for h in candidate["heroes"]):
            candidate[field] = candidate["week"]
    _, done = e.objectives(candidate)
    if done and not candidate["objective_done"]:
        candidate["objective_done"] = True
        log(candidate, "公司路线目标达成！获得 100 经营分，可以继续培养团队、探索新项目。")
    honors.update(candidate)
    candidate["actions"].append({"week": state["week"], "command": command, "args": copy.deepcopy(args)})
    return candidate


def replay(seed, scenario, actions, difficulty="standard"):
    s = new_game(seed, scenario, difficulty)
    for entry in actions:
        check(s["week"] == entry["week"], "回放周数不一致")
        s = execute(s, entry["command"], entry["args"])
    return s
