"""阶段目标：五个章节、疾病地图和患者组织委托。

章节只决定提示和奖励，不锁住玩家：提前做到后面的事照样算。所有判断只读已经发生的公开结果。
委托按种子和时间确定，不读候选真值；没完成没有惩罚。
"""

from __future__ import annotations

from .content import CATALOG, TARGETS
from .model import earn, log, rand


def _own(s, kind=None):
    return [d for d in s["products"] if not d["partner"] and (kind is None or d["kind"] == kind)]


def _approved(s):
    return list(s["products"])


def _passed(s, key, kind="innovative"):
    return any(r["key"] == key and r["passed"] for p in s["projects"] if p["kind"] == kind for r in p["results"])


def _masters(s):
    return {h["profession"] for h in s["heroes"] if h["employed"] and h["rank"] >= 3}


def _hard(s):
    return [d for d in _approved(s) if d["kind"] == "innovative" and CATALOG[d["catalog"]].get("difficulty")]


def _alzheimer(s):
    return [d for d in _approved(s) if CATALOG[d["catalog"]].get("target_id") == "abeta"]


CHAPTERS = [
    {
        "name": "街角药坊",
        "when": "第 1–2 年",
        "goal": ("第一款药上市（仿制药最快）", lambda s: bool(_approved(s))),
        "stars": [
            ("交付 6 单技术服务", lambda s: s["services_done"] >= 6),
            ("现金从没转负", lambda s: s["minimum_cash"] >= 0),
        ],
        "reward": 300,
        "text": "街坊的第一笔信任：起步基金到账。更多伙伴和更难的药在等你。",
    },
    {
        "name": "第一位专家",
        "when": "第 2–4 年",
        "goal": (
            "一位伙伴晋升精英，并有两款药上市",
            lambda s: any(h["employed"] and h["rank"] >= 2 for h in s["heroes"]) and len(_approved(s)) >= 2,
        ),
        "stars": [
            ("搬进联合研发所", lambda s: s["facility"] >= 1),
            ("完成一次带教", lambda s: any(h["mentored"] for h in s["heroes"])),
        ],
        "reward": 600,
        "text": "行业开始注意到你们。创新药的路已经铺开，对手也在看着。",
    },
    {
        "name": "第一款新药",
        "when": "第 4–8 年",
        "goal": ("一款创新药通过 II 期", lambda s: _passed(s, "II")),
        "stars": [
            ("一款创新药获批", lambda s: any(d["kind"] == "innovative" for d in _approved(s))),
            ("一项核心专利获得授权", lambda s: any((p.get("patent") or {}).get("granted") for p in s["projects"])),
        ],
        "reward": 1500,
        "text": "从仿制走到创新。更难的疾病在地图上亮着，传奇也开始愿意来看看。",
    },
    {
        "name": "攻坚",
        "when": "第 8–14 年",
        "goal": ("攻克一种难治疾病（高难创新药获批）", lambda s: bool(_hard(s))),
        "stars": [
            ("一款药通过独立复核", lambda s: any(r["passed"] for r in s.get("proofs", []))),
            (
                "三种专业都有大师",
                lambda s: len({h["profession"] for h in s["heroes"] if h["employed"] and h["rank"] >= 3}) >= 3,
            ),
        ],
        "reward": 3000,
        "text": "最后的难题出现在地图最深处：阿尔茨海默病。看看你凑不凑得齐四道关的人。",
    },
    {
        "name": "最后的难题",
        "when": "第 14 年起",
        "goal": ("阿尔茨海默病获批", lambda s: bool(_alzheimer(s))),
        "stars": [
            ("累计帮助 100 万人次", lambda s: sum(d.get("patients", 0) for d in s["products"]) >= 1_000_000),
            ("一位自家培养的传奇", lambda s: any(h["tier"] == 1 and h["rank"] >= 4 for h in s["heroes"])),
        ],
        "reward": 0,
        "text": "很多人说这道题没有答案。你们给出了一个。",
    },
]

# 疾病地图：每个治疗领域一句患者的话，攻克该领域任一疾病后亮起
STORIES = {
    "pressure": "以前每天量三次血压，现在一周量一次就放心了。",
    "lipid": "爸爸的体检单上，那一行终于不再是红的。",
    "pain": "能睡一整晚了。这是我两年来第一次睡一整晚。",
    "sugar": "我又能和孩子们一起吃生日蛋糕了，少吃一点就好。",
    "allergy": "春天不再是我最怕的季节。",
    "inflammation": "我又能拧开瓶盖了。听起来很小，对我很大。",
    "lung": "医生说，这次的片子比上次好。",
    "blood": "化疗的间隔变长了，我有时间陪女儿上完这学期。",
    "neuro": "妈妈今天叫出了我的名字。",
    "rare": "全世界只有几百个和我一样的孩子。现在我们有药了。",
    "infection": "整个病房，没有一个人再被转进 ICU。",
}
TIERS = {"common": "常见病", "novel": "新药", "hard": "难治", "final": "最后的难题"}


def tier(c):
    if c.get("target_id") == "abeta":
        return "final"
    if c["kind"] != "innovative":
        return "common"
    return "hard" if TARGETS[c["target_id"]]["difficulty"] >= 1.2 else "novel"


def disease_map(s):
    """仿制药的适应证算常见病；改良药不新增疾病，不上地图。"""
    rows = {}
    for c in CATALOG.values():
        if c["kind"] == "improved":
            continue
        disease = c.get("indication") or c["name"]
        rows.setdefault(
            disease, {"disease": disease, "market": c["market"], "tier": tier(c), "cured": False, "story": None}
        )
    for d in s["products"]:
        c = CATALOG[d["catalog"]]
        row = rows.get(c.get("indication") or c["name"])
        if row:
            row["cured"] = True
            row["story"] = STORIES.get(c["market"])
    order = {"common": 0, "novel": 1, "hard": 2, "final": 3}
    return sorted(rows.values(), key=lambda r: (order[r["tier"]], r["market"], r["disease"]))


# ---------------- 患者组织委托 ----------------
BOUNTY_EVERY = 96  # 大约每两年一条
BOUNTY_FROM = 96


def _bounty_candidates(s):
    cured = {CATALOG[d["catalog"]].get("indication") for d in s["products"]}
    taken = {b["disease"] for b in s.get("bounties", [])}
    pool = []
    for c in CATALOG.values():
        disease = c.get("indication")
        if not disease or disease in cured or disease in taken or c.get("target_id") == "abeta":
            continue
        if c["kind"] != "innovative":
            continue  # 改良药的「适应证」是改良方向，不是疾病；仿制药的病早就有药
        pool.append((disease, c))
    return sorted({d: c for d, c in pool}.items())


def offer_bounty(s):
    if s["week"] < BOUNTY_FROM or s["week"] % BOUNTY_EVERY:
        return
    pool = _bounty_candidates(s)
    if not pool:
        return
    disease, c = rand(s, "bounty", s["week"]).choice(pool)
    hard = tier(c) == "hard"
    years = 8 if hard else 6
    reward = 2500 if hard else 1500
    bounty = {
        "id": f"bounty-{s['week']}",
        "disease": disease,
        "market": c["market"],
        "kind": c["kind"],
        "offered": s["week"],
        "deadline": s["week"] + years * 48,
        "reward": reward,
        "status": "open",
    }
    s.setdefault("bounties", []).append(bounty)
    from .events import emit

    emit(s, "bounty_offered", data={"disease": disease, "years": years, "reward": reward})


def settle_bounties(s):
    from .events import emit

    for b in s.get("bounties", []):
        if b["status"] != "open":
            continue
        if any(CATALOG[d["catalog"]].get("indication") == b["disease"] for d in s["products"]):
            b["status"] = "done"
            b["done"] = s["week"]
            earn(s, b["reward"], "bounties")
            s["reputation"] += 5
            s.setdefault("bounties_done", []).append(b["id"])
            from . import chronicle

            chronicle.add(s, "bounty", f"完成患者组织的委托：「{b['disease']}」")
            emit(s, "bounty_completed", data={"disease": b["disease"], "reward": b["reward"]})
        elif s["week"] > b["deadline"]:
            b["status"] = "expired"
            log(s, f"患者组织关于「{b['disease']}」的委托到期了。没有惩罚，这个领域以后仍然可以做。")


# ---------------- 章节推进 ----------------


def update(s):
    """每次操作后检查：当前章节的主线完成就记录星级、发奖励、进入下一章。"""
    from .events import emit

    s.setdefault("chapter", 0)
    s.setdefault("chapter_log", [])
    while s["chapter"] < len(CHAPTERS):
        c = CHAPTERS[s["chapter"]]
        if not c["goal"][1](s):
            break
        stars = 1 + sum(bool(check(s)) for _, check in c["stars"])
        s["chapter_log"].append({"chapter": s["chapter"], "name": c["name"], "week": s["week"], "stars": stars})
        if c["reward"]:
            earn(s, c["reward"], "chapters")
        s["reputation"] += 2 * stars
        from . import chronicle

        chronicle.add(s, "chapter", f"完成第 {s['chapter'] + 1} 章「{c['name']}」，{stars} 星")
        emit(s, "chapter_completed", data={"name": c["name"], "stars": stars, "reward": c["reward"]})
        s["chapter"] += 1


def view(s):
    index = s.get("chapter", 0)
    current = None
    if index < len(CHAPTERS):
        c = CHAPTERS[index]
        current = {
            "index": index + 1,
            "name": c["name"],
            "when": c["when"],
            "goal": c["goal"][0],
            "stars": [{"text": t, "ok": bool(check(s))} for t, check in c["stars"]],
            "reward": c["reward"],
            "text": c["text"],
        }
    rows = disease_map(s)
    return {
        "current": current,
        "done": s.get("chapter_log", []),
        "total": len(CHAPTERS),
        "map": rows,
        "cured": sum(r["cured"] for r in rows),
        "tiers": TIERS,
        "bounties": [b for b in s.get("bounties", []) if b["status"] == "open"][-3:],
        "bounty_history": [b for b in s.get("bounties", []) if b["status"] != "open"][-5:],
    }
