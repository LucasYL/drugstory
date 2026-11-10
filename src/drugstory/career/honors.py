"""Annual contests, verifiable scientific legacy and a persistent trophy cabinet."""

from . import challenge
from .content import CATALOG, PROFESSIONS
from .model import ability, busy, earn, find, log, rand
from .science import observe, selected
from .units import pts, pts_map

AWARDS = {
    "progress": {
        "name": "年度研发进展奖",
        "prize": 200,
        "floor": 34,
        "description": "看本年实际通过的研发阶段，越往后的阶段分越高；合作项目的进展也算。不需要当年有药上市。",
    },
    "quality": {
        "name": "年度品质与供应奖",
        "prize": 180,
        "floor": 38,
        "description": "用新产品和实际供货证明稳定质量；不能只靠库存现金参赛。",
    },
    "mentorship": {
        "name": "年度育才奖",
        "prize": 160,
        "floor": 30,
        "description": "奖励本年的晋阶、项目成长和同专业带教。",
    },
    "innovation": {
        "name": "年度突破药物奖",
        "prize": 300,
        "floor": 44,
        "description": "本年创新药获批，比较临床获益证据与研究难度。",
    },
}
# 本年通过一个阶段计多少研发进展分；越靠后的阶段越难，分越高。
PROGRESS = {
    "formulation": 4,
    "quality": 4,
    "be": 6,
    "design": 6,
    "bridge": 9,
    "confirm": 12,
    "optimize": 8,
    "preclinical": 9,
    "I": 12,
    "II": 18,
    "III": 26,
    "review": 12,
}
# 对手的领先线每年抬高，让后期的奖更难拿。
YEARLY_RISE = 2.5
LEGACIES = {"science": "星火生命科学大奖", "access": "普惠药业桂冠", "academy": "薪火研究院"}


def counters(s):
    return {
        "ranks": sum(h["rank"] - h["tier"] for h in s["heroes"]),
        "mentors": sum(len(h["mentored"]) for h in s["heroes"]),
        "cases": sum(len(h["cases"]) for h in s["heroes"]),
        "sales": s["income"].get("sales", 0),
        "milestones": s["income"].get("milestones", 0),
    }


def initialize(s):
    s.update(awards=[], nominations=[], festivals=[], achievements=[], proofs=[], legacies=[])
    s["season"] = {"year": s["week"] // 48 + 1, "entry": None, "baseline": counters(s)}


def phase_value(p, key, stat):
    return next((r["values"].get(stat, 0) for r in reversed(p["results"]) if r["key"] == key and r["passed"]), 0)


def rival_score(s, r, category):
    affinity = {
        "scale": {"quality": 1.15, "mentorship": 0.8, "progress": 0.85, "innovation": 0.65},
        "pioneer": {"quality": 0.8, "mentorship": 1, "progress": 1.1, "innovation": 1.2},
        "partner": {"quality": 0.9, "mentorship": 0.95, "progress": 1.15, "innovation": 1},
    }[r["style"]][category]
    # Seeded variation is visible as each year's field; never reads the player's hidden candidate.
    year = s["season"]["year"]
    base = rand(s, "annual-field", year, r["id"], category).uniform(24, 44)
    base += 6 if challenge.enabled(s) else 0
    rise = YEARLY_RISE * max(0, year - 2)
    return round(min(88, (base + min(20, r["year_points"] * 0.4)) * affinity + rise), 1)


def categories(s):
    base = s["season"]["baseline"]
    now = counters(s)
    year = s["season"]["year"]
    start = (year - 1) * 48
    new = [d for d in s["products"] if not d["partner"] and d["launched"] >= start]
    novel = [d for d in s["products"] if d["kind"] == "innovative" and d["launched"] >= start]
    # 本年通过的阶段：自有项目和授权出去的项目都算（公开的阶段结果，不读真值）。
    passed = [r for p in s["projects"] for r in p["results"] if r["week"] >= start and r["passed"]]
    progress = sum(PROGRESS.get(r["key"], 6) for r in passed)
    quality = max((phase_value(find(s["projects"], d["project"]), "review", "quality") for d in new), default=0)
    innovation = max(
        (
            24
            + 24 * CATALOG[d["catalog"]]["difficulty"]
            + max(0, phase_value(find(s["projects"], d["project"]), "III", "effect") - 75) * 1.5
            for d in novel
        ),
        default=0,
    )
    scores = {
        "quality": min(
            90, 10 + len(new) * 6 + max(0, quality - 60) * 0.5 + min(20, (now["sales"] - base["sales"]) / 200)
        ),
        "mentorship": min(
            90,
            (now["ranks"] - base["ranks"]) * 12
            + (now["mentors"] - base["mentors"]) * 18
            + min(20, (now["cases"] - base["cases"]) * 1.2),
        ),
        "progress": min(90, 10 + progress + min(15, (now["milestones"] - base["milestones"]) / 80)) if passed else 0,
        "innovation": min(95, innovation),
    }
    gates = {
        "quality": bool(new) and now["sales"] - base["sales"] >= 250,
        "mentorship": now["mentors"] > base["mentors"] or now["ranks"] - base["ranks"] >= 2,
        "progress": bool(passed),
        "innovation": bool(novel),
    }
    hints = {
        "quality": "本年有自主新品，且产品销售回款至少 250 万",
        "mentorship": "本年完成一次带教，或累计晋升至少两个阶位",
        "progress": "本年至少通过一个研发阶段（自有或合作项目）",
        "innovation": "本年有自主或合作创新药获批",
    }
    rows = []
    for key, spec in AWARDS.items():
        benchmark = max([spec["floor"], *[rival_score(s, r, key) for r in s["rivals"]]])
        score = round(scores[key], 1)
        rows.append(
            {
                "key": key,
                **spec,
                "score": score,
                "eligible": year >= 2 and gates[key],
                "requirement": hints[key] + "；第 2 年起自动参评",
                "benchmark": benchmark,
                "gap": round(max(0.0, benchmark - score), 1),
                "repeat": any(a["category"] == key for a in s["awards"]),
                "field": [{"name": r["name"], "score": rival_score(s, r, key)} for r in s["rivals"]],
            }
        )
    return rows


def proof_options(s):
    options = []
    occupied = busy(s)
    for d in s["products"]:
        if d["kind"] != "innovative" or not CATALOG[d["catalog"]]["difficulty"]:
            continue
        p = find(s["projects"], d["project"])
        prior = [r for r in s["proofs"] if r["product"] == d["id"]]
        done = len(prior)
        running = next((j for j in s["jobs"] if j.get("product") == d["id"]), None)
        if done >= 2 or any(not r["passed"] for r in prior):
            continue
        roles = ("bio", "clinical") if done == 0 else ("clinical", "tox")
        ids = []
        for role in roles:
            people = [
                h
                for h in s["heroes"]
                if h["employed"]
                and h["id"] not in occupied
                and h["profession"] == role
                and h["rank"] >= 3
                and ability(h) >= 60
            ]
            if people:
                ids.append(max(people, key=ability)["id"])
        checks = [
            (f"III 期获益观察至少 {pts(76)}", phase_value(p, "III", "effect") >= 76),
            (f"III 期安全观察至少 {pts(64)}", phase_value(p, "III", "safety") >= 64),
            ("产品仍在市场", d["active"]),
            ("两位对应专业大师，能力至少 60", len(ids) == 2),
            ("没有正在进行的验证", not running),
        ]
        options.append(
            {
                "product": d["id"],
                "name": d["name"],
                "step": done,
                "title": "独立多中心复核" if done == 0 else "长期获益随访",
                "weeks": 52 if done == 0 else 48,
                "cost": 1400 if done == 0 else 900,
                "roles": "、".join(PROFESSIONS[r] for r in roles),
                "checks": [{"text": t, "ok": ok} for t, ok in checks],
                "available": all(ok for _, ok in checks),
                "recommended": ids,
                "running": {"left": running["left"], "heroes": running["heroes"]} if running else None,
            }
        )
    return options


def finish_proof(s, job):
    d = find(s["products"], job["product"])
    p = find(s["projects"], d["project"])
    c = selected(p)
    values = {}
    limits = {"effect": 75 if job["step"] == 0 else 76, "safety": 62 if job["step"] == 0 else 65}
    for stat in limits:
        # Independent public validation has its own saved evidence; cannot repeatedly buy rerolls.
        offset = c["subgroup"] if p.get("population") == "focused" and stat == "effect" else 0
        values[stat] = round(observe(s, p, c, stat, 4, f"independent-{job['step']}", offset), 1)
    passed = all(values[k] >= v for k, v in limits.items())
    record = {
        "product": d["id"],
        "name": d["name"],
        "step": job["step"],
        "week": s["week"],
        "passed": passed,
        "values": values,
        "limits": limits,
        "heroes": job["heroes"],
    }
    s["proofs"].append(record)
    log(
        s,
        f"{job['name']}完成：{'得到独立支持' if passed else '未能复现足够获益与安全证据'}。"
        "结果留档，同一产品不能反复重抽。",
    )


def legacy_progress(s):
    employed = [h for h in s["heroes"] if h["employed"]]
    masters = {h["profession"] for h in employed if h["rank"] >= 3}
    home = [h for h in employed if h["tier"] == 1]
    mentor_pairs = sum(len(h["mentored"]) for h in s["heroes"])
    wins = {a["category"] for a in s["awards"]}
    verified = [
        d
        for d in s["products"]
        if d["kind"] == "innovative"
        and CATALOG[d["catalog"]]["difficulty"]
        and len([r for r in s["proofs"] if r["product"] == d["id"] and r["passed"]]) == 2
        and s["week"] - d["launched"] >= 72
    ]
    own = [d for d in s["products"] if not d["partner"]]
    rows = {
        "science": [
            ("一款高难创新药通过两轮独立验证，并上市至少 72 周", bool(verified)),
            ("三种专业大师", len(masters) >= 3),
            ("至少一位从见习培养的传奇", any(h["rank"] == 4 for h in home)),
            ("完成两组导师带教", mentor_pairs >= 2),
            ("赢得两类年度奖", len(wins) >= 2),
            ("经营至少八年", s["week"] >= 384),
        ],
        "access": [
            ("自主产品覆盖四个治疗领域", len({d["market"] for d in own}) >= 4),
            ("两款不同方案改良药", len({d["catalog"] for d in own if d["kind"] == "improved"}) >= 2),
            ("三位从见习培养的大师", sum(h["rank"] >= 3 for h in home) >= 3),
            ("两届品质与供应奖", sum(a["category"] == "quality" for a in s["awards"]) >= 2),
            ("累计实际供货回款 12000 万", s["income"].get("sales", 0) >= 12000),
        ],
        "academy": [
            ("五种专业都有大师", len(masters) == 5),
            ("两位从见习培养的传奇", sum(h["rank"] == 4 for h in home) >= 2),
            ("完成三组导师带教", mentor_pairs >= 3),
            ("赢得两类年度奖", len(wins) >= 2),
            ("五种专业知识均达到 75", min(s["knowledge"].values()) >= 75),
        ],
    }
    return [
        {
            "key": key,
            "name": LEGACIES[key],
            "won": any(item["key"] == key for item in s["legacies"]),
            "checks": [{"text": t, "ok": ok} for t, ok in checks]
            + [{"text": "现金为正，公司仍在经营", "ok": s["cash"] > 0 and not s["game_over"]}],
        }
        for key, checks in rows.items()
    ]


ACHIEVEMENTS = {
    "first_product": "第一粒药",
    "first_elite": "小队初成",
    "first_patent": "第一项专利",
    "facility_1": "搬进联合研发所",
    "team_6": "六人小队",
    "first_master": "专家坐镇",
    "first_license": "第一笔授权",
    "first_innovation": "新药诞生",
    "first_award": "第一次上台",
    "first_mentor": "薪火相传",
    "facility_2": "搬进专业研究院",
    "notebook_10": "十条组合手记",
    "products_5": "五款产品同时在售",
    "sales_1e4": "累计销售额一亿",
    "lab_top": "顶级实验室",
    "team_10": "十人研究社",
    "partner_success": "跨过边界",
    "innovation_3": "三款创新药",
    "first_legend": "传奇坐镇",
    "facility_3": "搬进星火科学城",
    "replicated": "经得起复核",
}


def achievement_ready(s):
    employed = [h for h in s["heroes"] if h["employed"]]
    own = [d for d in s["products"] if not d["partner"]]
    return {
        "first_product": bool(s["products"]),
        "first_elite": any(h["rank"] >= 2 for h in s["heroes"]),
        "first_patent": any((p.get("patent") or {}).get("granted") for p in s["projects"]),
        "facility_1": s["facility"] >= 1,
        "team_6": len(employed) >= 6,
        "first_master": any(h["rank"] >= 3 for h in s["heroes"]),
        "first_license": bool(s["deals"]),
        "first_innovation": any(d["kind"] == "innovative" for d in s["products"]),
        "first_award": bool(s["awards"]),
        "first_mentor": any(h["mentored"] for h in s["heroes"]),
        "facility_2": s["facility"] >= 2,
        "notebook_10": len(s["notebook"]) >= 10,
        "products_5": sum(d["active"] for d in own) >= 5,
        "sales_1e4": s["income"].get("sales", 0) >= 10000,
        "lab_top": any(level >= 3 for level in s["equipment"].values()),
        "team_10": len(employed) >= 10,
        "partner_success": any(d["status"] == "approved" for d in s["deals"]),
        "innovation_3": sum(d["kind"] == "innovative" for d in own) >= 3,
        "first_legend": any(h["rank"] >= 4 for h in s["heroes"]),
        "facility_3": s["facility"] >= 3,
        "replicated": any(r["passed"] for r in s["proofs"]),
    }


def update(s):
    from .events import emit

    ready = achievement_ready(s)
    for key, name in ACHIEVEMENTS.items():
        if ready[key] and not any(a["key"] == key for a in s["achievements"]):
            s["achievements"].append({"key": key, "name": name, "week": s["week"]})
            emit(s, "milestone_reached", data={"key": key, "title": name})


def annual(s):
    """年末自动评选：所有符合条件的成果都参评，每年最多颁一个大奖，其余胜出的类别记为提名。"""
    if s["week"] % 48 or s["season"]["year"] != s["week"] // 48:
        return
    from .events import emit

    year = s["season"]["year"]
    entries = categories(s)
    winners = [c for c in entries if c["eligible"] and c["score"] >= c["benchmark"]]
    # 得分最高的一类拿奖；同分时奖金高的优先，保证结果确定。
    grand = max(winners, key=lambda c: (c["score"], c["prize"], c["key"])) if winners else None
    results = []
    for c in entries:
        rival = max(c["field"], key=lambda r: r["score"])
        won = grand is not None and c["key"] == grand["key"]
        nominated = c in winners and not won
        reason = (
            "尚未开放评选"
            if year < 2
            else "未满足年度成果要求"
            if not c["eligible"]
            else "本届获奖"
            if won
            else "胜出，记为提名（每年只颁一个大奖）"
            if nominated
            else "本届成果分低于领先线"
        )
        results.append(
            {
                "category": c["key"],
                "name": c["name"],
                "winner": "你的研究社"
                if won or nominated
                else rival["name"]
                if year >= 2 and rival["score"] >= c["floor"]
                else "本届空缺",
                "your_score": c["score"],
                "leading_score": c["benchmark"],
                "reason": reason,
                "won": won,
                "nominated": nominated,
            }
        )
        if nominated:
            s.setdefault("nominations", []).append(
                {"year": year, "category": c["key"], "name": c["name"], "score": c["score"]}
            )
            s["reputation"] += 1
    if grand:
        prize = grand["prize"] // 2 if grand["repeat"] else grand["prize"]
        earn(s, prize, "awards")
        s["reputation"] += 3
        s["awards"].append(
            {"year": year, "category": grand["key"], "name": grand["name"], "score": grand["score"], "prize": prize}
        )
        from . import chronicle

        chronicle.add(s, "award", f"获得第 {year} 届{grand['name']}")
        emit(
            s,
            "award_won",
            actors=[h["id"] for h in s["heroes"] if h["employed"]],
            data={"name": grand["name"], "year": year, "prize": prize},
        )
    for goal in legacy_progress(s):
        if not goal["won"] and all(c["ok"] for c in goal["checks"]):
            s["legacies"].append(
                {
                    "key": goal["key"],
                    "name": goal["name"],
                    "year": year,
                    "week": s["week"],
                    "heroes": [h["name"] for h in s["heroes"] if h["employed"] and h["rank"] >= 3],
                }
            )
            s["reputation"] += 20
            from . import chronicle
            from .events import emit

            chronicle.add(s, "legacy", f"获得终局荣誉「{goal['name']}」")

            emit(
                s,
                "legacy_reached",
                actors=[h["id"] for h in s["heroes"] if h["employed"]],
                data={"name": goal["name"], "year": year},
            )
    s["festivals"].append({"year": year, "results": results})
    log(s, f"第 {year} 年研究大会结束。前往荣誉室查看入围、获奖与差距。")
    s["season"] = {"year": year + 1, "entry": None, "baseline": counters(s)}
    from . import goals

    goals.close_year(s)
    goals.offer(s, year + 1)
    for r in s["rivals"]:
        r["year_points"] = 0
    update(s)


def view(s):
    return {
        "year": s["season"]["year"],
        "deadline": s["season"]["year"] * 48,
        "categories": categories(s),
        "awards": s["awards"],
        "nominations": s.get("nominations", []),
        "legacy_awards": s["legacies"],
        "festivals": s["festivals"][-5:],
        "achievements": s["achievements"],
        "legacies": legacy_progress(s),
        "proofs": [{**r, "values": pts_map(r["values"]), "limits": pts_map(r["limits"])} for r in s["proofs"]],
        "studies": proof_options(s),
    }
