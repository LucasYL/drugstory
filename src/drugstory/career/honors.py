"""Annual contests, verifiable scientific legacy and a persistent trophy cabinet."""

from . import challenge
from .content import CATALOG, PROFESSIONS
from .model import ability, busy, earn, find, log, rand
from .science import observe, selected

AWARDS = {
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
    "partnership": {
        "name": "年度转化合作奖",
        "prize": 220,
        "floor": 32,
        "description": "看合作项目获得的新临床证据与实际里程碑，不按合同总额评奖。",
    },
    "innovation": {
        "name": "年度突破药物奖",
        "prize": 300,
        "floor": 44,
        "description": "本年创新药获批，比较临床获益证据与研究难度。",
    },
}
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
    s.update(awards=[], festivals=[], achievements=[], proofs=[], legacies=[])
    s["season"] = {"year": s["week"] // 48 + 1, "entry": None, "baseline": counters(s)}


def phase_value(p, key, stat):
    return next((r["values"].get(stat, 0) for r in reversed(p["results"]) if r["key"] == key and r["passed"]), 0)


def rival_score(s, r, category):
    affinity = {
        "scale": {"quality": 1.15, "mentorship": 0.8, "partnership": 0.8, "innovation": 0.65},
        "pioneer": {"quality": 0.8, "mentorship": 1, "partnership": 0.95, "innovation": 1.2},
        "partner": {"quality": 0.9, "mentorship": 0.95, "partnership": 1.2, "innovation": 1},
    }[r["style"]][category]
    # Seeded variation is visible as each year's field; never reads the player's hidden candidate.
    base = rand(s, "annual-field", s["season"]["year"], r["id"], category).uniform(24, 44)
    base += 6 if challenge.enabled(s) else 0
    return round(min(80, (base + min(20, r["year_points"] * 0.4)) * affinity), 1)


def categories(s):
    base = s["season"]["baseline"]
    now = counters(s)
    year = s["season"]["year"]
    start = (year - 1) * 48
    new = [d for d in s["products"] if not d["partner"] and d["launched"] >= start]
    novel = [d for d in s["products"] if d["kind"] == "innovative" and d["launched"] >= start]
    phase_reports = [
        r
        for p in s["projects"]
        if p["status"] == "licensed"
        for r in p["results"]
        if r["week"] >= start and r["passed"] and r["key"] in ("I", "II", "III", "review")
    ]
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
            90, 15 + len(new) * 7 + max(0, quality - 60) * 0.6 + min(25, (now["sales"] - base["sales"]) / 160)
        ),
        "mentorship": min(
            90,
            (now["ranks"] - base["ranks"]) * 12
            + (now["mentors"] - base["mentors"]) * 18
            + min(20, (now["cases"] - base["cases"]) * 1.2),
        ),
        "partnership": min(90, len(phase_reports) * 9 + min(40, (now["milestones"] - base["milestones"]) / 55)),
        "innovation": min(95, innovation),
    }
    gates = {
        "quality": bool(new) and now["sales"] - base["sales"] >= 250,
        "mentorship": now["mentors"] > base["mentors"] or now["ranks"] - base["ranks"] >= 2,
        "partnership": bool(phase_reports),
        "innovation": bool(novel),
    }
    hints = {
        "quality": "本年有自主新品，且产品销售回款至少 250 万",
        "mentorship": "本年完成一次带教，或累计晋升至少两个阶位",
        "partnership": "本年取得合作项目 I 期以后支持证据",
        "innovation": "本年有自主或合作创新药获批",
    }
    return [
        {
            "key": key,
            **spec,
            "score": round(scores[key], 1),
            "eligible": year >= 2 and gates[key],
            "requirement": hints[key] + "；第 2 年起接受参评",
            "benchmark": max([spec["floor"], *[rival_score(s, r, key) for r in s["rivals"]]]),
            "field": [{"name": r["name"], "score": rival_score(s, r, key)} for r in s["rivals"]],
        }
        for key, spec in AWARDS.items()
    ]


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
            ("III 期获益观察至少 78", phase_value(p, "III", "effect") >= 78),
            ("III 期安全观察至少 66", phase_value(p, "III", "safety") >= 66),
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
    limits = {"effect": 77 if job["step"] == 0 else 78, "safety": 64 if job["step"] == 0 else 67}
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


def update(s):
    milestones = {
        "first_product": ("第一粒药", bool(s["products"])),
        "first_elite": ("小队初成", any(h["rank"] >= 2 for h in s["heroes"])),
        "first_master": ("专家坐镇", any(h["rank"] >= 3 for h in s["heroes"])),
        "first_innovation": ("新药诞生", any(d["kind"] == "innovative" for d in s["products"])),
        "partner_success": ("跨过边界", any(d["status"] == "approved" for d in s["deals"])),
        "first_mentor": ("薪火相传", any(h["mentored"] for h in s["heroes"])),
        "first_award": ("第一次上台", bool(s["awards"])),
        "replicated": ("经得起复核", any(r["passed"] for r in s["proofs"])),
    }
    for key, (name, ready) in milestones.items():
        if ready and not any(a["key"] == key for a in s["achievements"]):
            s["achievements"].append({"key": key, "name": name, "week": s["week"]})
            log(s, "成长纪念：" + name + "。已收入荣誉室。")


def annual(s):
    if s["week"] % 48 or s["season"]["year"] != s["week"] // 48:
        return
    year = s["season"]["year"]
    entries = categories(s)
    entry = s["season"]["entry"]
    results = []
    for c in entries:
        rival = max(c["field"], key=lambda r: r["score"])
        won = entry == c["key"] and c["eligible"] and c["score"] >= c["benchmark"]
        reason = (
            "尚未开放评选"
            if year < 2
            else "未报名"
            if entry != c["key"]
            else "未满足年度成果要求"
            if not c["eligible"]
            else "本届胜出"
            if won
            else "本届成果分低于领先对手或入围线"
        )
        results.append(
            {
                "category": c["key"],
                "name": c["name"],
                "winner": "你的研究社"
                if won
                else rival["name"]
                if year >= 2 and rival["score"] >= c["floor"]
                else "本届空缺",
                "your_score": c["score"],
                "leading_score": c["benchmark"],
                "reason": reason,
                "won": won,
            }
        )
        if won:
            repeated = any(a["category"] == c["key"] for a in s["awards"])
            prize = 50 if repeated else c["prize"]
            earn(s, prize, "awards")
            s["reputation"] += 3
            s["awards"].append(
                {"year": year, "category": c["key"], "name": c["name"], "score": c["score"], "prize": prize}
            )
            log(s, f"年度颁奖：研究社获得{c['name']}！奖金 ¥{prize} 万，作品和培养记录已刻入奖杯室。")
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
            log(s, "终局荣誉达成：" + goal["name"] + "！研究社的成果与培养传承被正式认可。")
    s["festivals"].append({"year": year, "entry": entry, "results": results})
    log(s, f"第 {year} 年研究大会结束。前往荣誉室查看入围、获奖与差距。")
    s["season"] = {"year": year + 1, "entry": None, "baseline": counters(s)}
    for r in s["rivals"]:
        r["year_points"] = 0
    update(s)


def view(s):
    return {
        "year": s["season"]["year"],
        "entry": s["season"]["entry"],
        "deadline": s["season"]["year"] * 48,
        "categories": categories(s),
        "awards": s["awards"],
        "legacy_awards": s["legacies"],
        "festivals": s["festivals"][-5:],
        "achievements": s["achievements"],
        "legacies": legacy_progress(s),
        "proofs": s["proofs"],
        "studies": proof_options(s),
    }
