"""年度目标：每届研究大会后，从三个目标里选一个当作明年的事。

目标只读已经发生的公开结果；出题按种子和年份确定（带键随机），不读候选真值。
不选、没完成都没有惩罚。完成后发奖金和声誉，也计入评级的「行业声誉」。
"""

from __future__ import annotations

from .content import PATHS
from .model import check, earn, rand


def _baseline(s):
    """记下年初的数，年末或完成时拿来比。"""
    return {
        "ranks": sum(h["rank"] - h["tier"] for h in s["heroes"]),
        "mentors": sum(len(h["mentored"]) for h in s["heroes"]),
        "heroes": len(s["heroes"]),
        "personal": sum(bool(h.get("personal")) for h in s["heroes"]),
        "services": s["services_done"],
        "cash": s["cash"],
        "minimum_cash": s["minimum_cash"],
        "patents": sum(1 for p in s["projects"] if (p.get("patent") or {}).get("granted")),
        "bounties": len(s.get("bounties_done", [])),
        "honors": len(s.get("awards", [])) + len(s.get("nominations", [])),
        "facility": s["facility"],
        "equipment": sum(s["equipment"].values()),
    }


def _since(s, g):
    return g["start"]


def _passed(s, g):
    return [r for p in s["projects"] for r in p["results"] if r["week"] >= g["start"] and r["passed"]]


def _launched(s, g, kind=None):
    return [
        d
        for d in s["products"]
        if not d["partner"] and d["launched"] >= g["start"] and (kind is None or d["kind"] == kind)
    ]


def _now(s):
    return _baseline(s)


def _active(s, kind=None):
    from .model import ACTIVE

    return [p for p in s["projects"] if p["status"] in ACTIVE and (kind is None or p["kind"] == kind)]


def _promotion_close(s):
    from .economy import promotion_requirements

    return any(
        h["employed"] and h["rank"] < 4 and sum(not ok for _, ok in promotion_requirements(s, h)) <= 2
        for h in s["heroes"]
    )


def _mentor_pair(s):
    people = [h for h in s["heroes"] if h["employed"]]
    return any(
        t["rank"] >= 2 and u["profession"] == t["profession"] and u["rank"] < t["rank"] and t["id"] not in u["mentored"]
        for t in people
        for u in people
    )


def _can_hire(s):
    from . import guide
    from .content import ROSTER

    return any(guide._recruitable(s, k) for k in ROSTER)


def _personal_ready(s):
    from . import stories

    return any(h["employed"] and not h.get("personal") and stories.options(s, h)["unlocked"] for h in s["heroes"])


def _late_projects(s):
    return [p for p in _active(s) if p["index"] >= len(PATHS[p["kind"]]) - 2]


def _bounty_live(s):
    from .content import CATALOG

    open_ = {b["disease"] for b in s.get("bounties", []) if b["status"] == "open"}
    return any(CATALOG[p["catalog"]].get("indication") in open_ for p in _active(s))


def _can_expand(s):
    from .content import FACILITIES
    from .development import EQUIPMENT_COST

    cash = s["cash"]
    nxt = FACILITIES[s["facility"] + 1]["cost"] if s["facility"] < len(FACILITIES) - 1 else None
    lab = min((EQUIPMENT_COST[v + 1] for v in s["equipment"].values() if v < 3), default=None)
    return any(x is not None and cash >= x + 300 for x in (nxt, lab))


# key: (标题, 条件说明, 目标数或 None, 当前数(s, g), 可行(s), 奖金, 声誉, 只在年末判断)
GOALS = {
    "progress3": (
        "推进三步",
        "本年通过 3 个研发阶段（自有或合作项目）",
        3,
        lambda s, g: len(_passed(s, g)),
        lambda s: bool(_active(s)),
        250,
        2,
        False,
    ),
    "promote": (
        "更进一步",
        "本年至少一位伙伴晋阶",
        1,
        lambda s, g: _now(s)["ranks"] - g["base"]["ranks"],
        _promotion_close,
        200,
        0,
        False,
    ),
    "mentor": (
        "传帮带",
        "本年完成一次带教",
        1,
        lambda s, g: _now(s)["mentors"] - g["base"]["mentors"],
        _mentor_pair,
        200,
        0,
        False,
    ),
    "hire": (
        "新面孔",
        "本年邀请一位新伙伴",
        1,
        lambda s, g: _now(s)["heroes"] - g["base"]["heroes"],
        _can_hire,
        150,
        0,
        False,
    ),
    "personal": (
        "自己的题目",
        "本年完成一个个人课题",
        1,
        lambda s, g: _now(s)["personal"] - g["base"]["personal"],
        _personal_ready,
        250,
        0,
        False,
    ),
    "launch2": (
        "双喜",
        "本年两款药上市",
        2,
        lambda s, g: len(_launched(s, g)),
        lambda s: len(_late_projects(s)) >= 2,
        400,
        2,
        False,
    ),
    "improved": (
        "改得更好",
        "本年一款改良药上市",
        1,
        lambda s, g: len(_launched(s, g, "improved")),
        lambda s: bool(_active(s, "improved")),
        500,
        0,
        False,
    ),
    "first_human": (
        "第一次进人体",
        "本年一款创新药通过 I 期",
        1,
        lambda s, g: sum(1 for r in _passed(s, g) if r["key"] == "I"),
        lambda s: any(p["index"] in (1, 2) for p in _active(s, "innovative")),
        500,
        2,
        False,
    ),
    "services4": (
        "接满单",
        "本年交付 4 单技术服务",
        4,
        lambda s, g: _now(s)["services"] - g["base"]["services"],
        lambda s: any(h["employed"] for h in s["heroes"]),
        150,
        0,
        False,
    ),
    "steady": (
        "稳住现金",
        "年末现金不低于年初，且全年没转负",
        None,
        lambda s, g: int(
            s["cash"] >= g["base"]["cash"]
            and (s["minimum_cash"] >= 0 or s["minimum_cash"] >= g["base"]["minimum_cash"])
        ),
        lambda s: s["cash"] > 0,
        200,
        0,
        True,
    ),
    "patent": (
        "拿到专利",
        "本年一项专利获得授权",
        1,
        lambda s, g: _now(s)["patents"] - g["base"]["patents"],
        lambda s: any((p.get("patent") or {}).get("granted") is None and p.get("patent") for p in s["projects"]),
        300,
        0,
        False,
    ),
    "bounty": (
        "回信",
        "本年完成一封患者组织委托",
        1,
        lambda s, g: _now(s)["bounties"] - g["base"]["bounties"],
        _bounty_live,
        0,
        3,
        False,
    ),
    "podium": (
        "上台",
        "本年获得年度大奖或提名",
        1,
        lambda s, g: _now(s)["honors"] - g["base"]["honors"],
        lambda s: s["week"] >= 48,
        300,
        0,
        True,
    ),
    "expand": (
        "扩建",
        "本年搬进下一档场地，或升级一间实验室",
        1,
        lambda s, g: (_now(s)["facility"] - g["base"]["facility"]) + (_now(s)["equipment"] - g["base"]["equipment"]),
        _can_expand,
        300,
        0,
        False,
    ),
}
REPUTATION_POINTS = 5  # 每完成一个年度目标，评级「行业声誉」多算的点数


def spec(key):
    title, text, target, _, _, cash, reputation, year_end = GOALS[key]
    return {
        "key": key,
        "title": title,
        "text": text,
        "target": target,
        "cash": cash,
        "reputation": reputation,
        "year_end": year_end,
    }


def offer(s, year):
    """研究大会之后为下一年出三个题。第 2 年起。"""
    feasible = sorted(k for k, g in GOALS.items() if g[4](s))
    picks = rand(s, "goals", year).sample(feasible, min(3, len(feasible)))
    s["year_goal"] = {
        "year": year,
        "start": s["week"],
        "offers": picks,
        "picked": None,
        "done": False,
        "base": _baseline(s),
    }
    if picks:
        from .events import emit

        emit(s, "goals_offered", data={"year": year, "titles": "、".join(GOALS[k][0] for k in picks)})


def pick(s, goal):
    g = s.get("year_goal")
    check(g is not None and g["picked"] is None, "今年的目标已经选好了，或者还没到出题的时候")
    check(goal in g["offers"], "请从给出的三个目标里选")
    g["picked"] = goal
    from .model import log

    log(s, f"今年的目标：{GOALS[goal][0]}——{GOALS[goal][1]}。")


def progress(s):
    g = s.get("year_goal")
    if not g or not g["picked"]:
        return None
    _, _, target, current, *_ = GOALS[g["picked"]]
    return current(s, g), target


def _complete(s, g):
    from . import chronicle
    from .events import emit

    title, _, _, _, _, cash, reputation, _ = GOALS[g["picked"]]
    g["done"] = True
    if cash:
        earn(s, cash, "goals")
    s["reputation"] += reputation
    s.setdefault("goal_log", []).append({"year": g["year"], "key": g["picked"], "title": title, "week": s["week"]})
    chronicle.add(s, "goal", f"完成第 {g['year']} 年的目标「{title}」")
    emit(s, "goal_completed", data={"title": title, "cash": cash})


def update(s, year_end=False):
    """每次操作后、以及年末颁奖之后检查今年选的目标。"""
    g = s.get("year_goal")
    if not g or not g["picked"] or g["done"]:
        return
    _, _, target, current, _, _, _, at_year_end = GOALS[g["picked"]]
    if at_year_end and not year_end:
        return
    if current(s, g) >= (target or 1):
        _complete(s, g)


def close_year(s):
    """年末：判断只在年末算的目标，记下这一年的结果。"""
    g = s.get("year_goal")
    if not g:
        return
    update(s, year_end=True)
    if g["picked"]:
        s.setdefault("goal_history", []).append(
            {"year": g["year"], "key": g["picked"], "title": GOALS[g["picked"]][0], "done": g["done"]}
        )


def view(s):
    g = s.get("year_goal")
    current = None
    offers = []
    if g:
        if g["picked"]:
            prog = progress(s)
            current = {
                **spec(g["picked"]),
                "year": g["year"],
                "done": g["done"],
                "progress": list(prog) if prog and prog[1] else None,
            }
        else:
            offers = [spec(k) for k in g["offers"]]
    return {
        "current": current,
        "offers": offers,
        "year": g["year"] if g else None,
        "done": len(s.get("goal_log", [])),
        "history": s.get("goal_history", [])[-6:],
    }
