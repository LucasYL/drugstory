"""成长建议：把「下一步可以做什么」放到玩家眼前，跟着当前章节走。

只读公开状态，不改状态、不抽随机数。带命令的建议按引擎的前提条件检查过（见 ``blocker``），
按钮上的操作能直接成功；做不了的只在和章节直接相关时保留，并写出原因。

``moments`` 给引擎用：第一次出现某个成长机会时（有人可以晋阶、买得起下一档场地……），
引擎记下它并发 ``growth_ready`` 事件，「下一件事」会在那一周停下。
"""

from __future__ import annotations

from . import assist, gates
from . import economy as e
from .content import CATALOG, FACILITIES, KINDS, PROMOTION, RANKS, ROSTER
from .model import ACTIVE, ability, busy, committed

RESERVE = 300  # 万：建议花钱时至少留下的周转金
ROUTES = ("generic", "improved", "innovative")
BLURB = {"generic": "稳，回本快", "improved": "中等风险，利润更高", "innovative": "高风险，高回报"}


def _cash(s):
    return s["cash"] - committed(s)


RUNWAY = 52  # 周：建议花钱后，按新的每周开销至少还能撑一年


def burn(s):
    """每周净支出（负数表示收支为正），和快照里的口径一致。"""
    profit = sum(e.expected_sales(s, d)[1] for d in s["products"] if not d["partner"])
    royalty = sum(d["weekly_royalty"] for d in s["deals"])
    return e.costs_per_week(s) - profit - royalty


def sustainable(s, cost, weekly=0.0, runway=RUNWAY):
    """花掉 cost、每周多出 weekly 的开销以后，现金还能不能撑过 runway 周。"""
    after = _cash(s) - cost
    rate = burn(s) + weekly
    return after >= RESERVE and (rate <= 0 or after / rate >= runway)


def _item(
    key, kind, title, text, *, chapter=False, command=None, args=None, route=None, hero=None, tab=None, catalog=None
):
    return {
        "catalog": catalog,
        "key": key,
        "kind": kind,
        "title": title,
        "text": text,
        "chapter": chapter,
        "command": command,
        "args": args,
        "route": route,
        "hero": hero,
        "tab": tab,
        "ok": True,
        "error": None,
    }


def _occupied(s, key):
    from .model import ACTIVE

    return any(p["catalog"] == key and p["status"] in ACTIVE for p in s["projects"]) or e.catalog_in_market(s, key)


def startable(s, kind, first=False):
    """这条路线现在能开始的项目（条件满足、没有在研或在售）。first=True 时找到一个就返回。"""
    from .engine import catalog_requirements

    out = []
    for k, c in CATALOG.items():
        if c["kind"] == kind and all(ok for _, ok in catalog_requirements(s, k)) and not _occupied(s, k):
            out.append(k)
            if first:
                break
    return out


def best_innovative(s, hard=False):
    """引导推荐哪条创新药路线：只看公开信息。

    跳过做失败或止损过的组合；组合手记里记过「适配」的优先，其次是主流路线；难度低、市场大的优先。
    """
    from .content import ROUTES as MAINSTREAM
    from .content import TARGETS

    tried = {p["catalog"] for p in s["projects"] if p["status"] in ("failed", "terminated")}

    def score(key):
        c = CATALOG[key]
        note = s["notebook"].get(key)
        known = note["tier"] if note else None
        mainstream = c.get("modality_id") in MAINSTREAM.get(c.get("target_id"), [])
        target = TARGETS.get(c.get("target_id"), {})
        return (
            known is not None and known >= 1,
            known if known is not None else (0.5 if mainstream else -3),
            -c.get("difficulty", 0),
            -target.get("difficulty", 1),
            target.get("market", 0),
            key,
        )

    options = [
        k
        for k in startable(s, "innovative")
        if (not hard or CATALOG[k].get("difficulty"))
        and k not in tried
        and (s["notebook"].get(k) or {}).get("tier", 0) >= 0
    ]
    return max(options, key=score) if options else None


def _first_missing(s, kind):
    """这条路线最容易补上的那个未满足条件。"""
    from .engine import catalog_requirements

    best = None
    for k, c in CATALOG.items():
        if c["kind"] != kind or _occupied(s, k):
            continue
        missing = [label for label, ok in catalog_requirements(s, k) if not ok]
        if missing and (best is None or len(missing) < len(best)):
            best = missing
    return best[0] if best else None


def _promotable(s):
    occupied = busy(s)
    ready = [
        h
        for h in s["heroes"]
        if h["employed"] and h["rank"] < 4 and all(ok for _, ok in e.promotion_requirements(s, h))
    ]
    return sorted(ready, key=lambda h: (h["id"] in occupied, PROMOTION[h["rank"] + 1]["cost"], h["id"]))


def promote_items(s, chapter=False, reason="", professions=None, rank=None):
    out = []
    for h in _promotable(s):
        if professions and h["profession"] not in professions:
            continue
        if rank and h["rank"] + 1 < rank:
            continue
        nxt = RANKS[h["rank"] + 1]
        cost = PROMOTION[h["rank"] + 1]["cost"]
        out.append(
            _item(
                f"promote:{h['id']}",
                "promote",
                f"晋阶{h['name']}",
                f"{reason + ' · ' if reason else ''}升为{nxt} · ¥{cost:,} 万",
                chapter=chapter,
                command="promote",
                args={"character": h["id"]},
            )
        )
    return out


def _in_flight(s, kinds):
    return any(p["kind"] in kinds and p["status"] in ACTIVE for p in s["projects"])


def project_items(s, chapter=False, reason="", only=None, hard=False):
    """开始下一个项目：按「仿制 → 改良 → 创新」挑第一条有可开始项目的路线。

    创新药同时只建议一个（在研时不再推第二个），并且要先有预算。
    """
    innovative_ok = can_afford_innovative(s) and not _in_flight(s, ("innovative",))
    routes = [only] if only else [r for r in ROUTES if r != "innovative" or innovative_ok]
    if only == "innovative" and not innovative_ok:
        return []
    for kind in routes:
        if startable(s, kind, first=True):
            team = assist.screening_team(s, kind)
            pick = best_innovative(s, hard) if kind == "innovative" else None
            if kind == "innovative" and not pick:
                continue
            spec = CATALOG[pick] if pick else None
            item = _item(
                f"project:{kind}",
                "project",
                f"开始一个{KINDS[kind]}项目" if not spec else f"试试{spec['indication']}：{spec['modality']}",
                reason or BLURB[kind],
                chapter=chapter,
                route=kind,
                catalog=pick,
            )
            if not team:
                item.update(ok=False, error="没有空闲的对应专业伙伴")
            return [item]
    kind = routes[0] if only else next((k for k in ROUTES if _first_missing(s, k)), "improved")
    missing = _first_missing(s, kind)
    if not missing:
        return []
    item = _item(
        f"project:{kind}",
        "project",
        f"{KINDS[kind]}还差一步",
        f"{reason + ' · ' if reason else ''}还差：{missing}",
        chapter=chapter,
        route=kind,
    )
    item.update(ok=False, error=f"还差：{missing}")
    return [item]


def upgrade_items(s, chapter=False, reason="", optional=False):
    """optional：只是章节的星（锦上添花），要求撑两年而不是一年。"""
    if s["facility"] >= len(FACILITIES) - 1:
        return []
    nxt = FACILITIES[s["facility"] + 1]
    runway = RUNWAY * 2 if optional else RUNWAY
    if not sustainable(s, nxt["cost"], nxt["rent"] - FACILITIES[s["facility"]]["rent"], runway):
        if optional:
            return []
        if not chapter:
            return []
        item = _item(
            f"upgrade:{s['facility'] + 1}",
            "upgrade",
            f"扩建为{nxt['name']}",
            f"{reason + ' · ' if reason else ''}¥{nxt['cost']:,} 万，还要攒一攒",
            chapter=True,
            command="upgrade",
            args={},
        )
        item.update(ok=False, error="先攒一攒：扩建后现金要能撑一年以上")
        return [item]
    return [
        _item(
            f"upgrade:{s['facility'] + 1}",
            "upgrade",
            f"扩建为{nxt['name']}",
            f"{reason + ' · ' if reason else ''}能容纳 {nxt['capacity']} 人 · ¥{nxt['cost']:,} 万",
            chapter=chapter,
            command="upgrade",
            args={},
        )
    ]


def needs_space(s):
    """真的需要扩建：有人只差场地就能晋阶，或者场地已经容不下新伙伴。"""
    from .engine import headcount

    for h in s["heroes"]:
        if h["employed"] and h["rank"] < 4:
            missing = [label for label, ok in e.promotion_requirements(s, h) if not ok]
            if missing and all(label.startswith("场地") for label in missing):
                return True
    return headcount(s) + 3 > FACILITIES[s["facility"]]["capacity"] and any(_recruitable(s, k) for k in ROSTER)


def mentor_items(s, chapter=False, reason=""):
    occupied = busy(s)
    free = [h for h in s["heroes"] if h["employed"] and h["id"] not in occupied]
    for t in sorted(free, key=lambda h: -h["rank"]):
        if t["rank"] < 2:
            continue
        for u in free:
            if u["profession"] == t["profession"] and u["rank"] < t["rank"] and t["id"] not in u["mentored"]:
                return [
                    _item(
                        f"mentor:{t['id']}:{u['id']}",
                        "mentor",
                        f"{t['name']}带教{u['name']}",
                        f"{reason + ' · ' if reason else ''}10 周 · ¥60 万",
                        chapter=chapter,
                        command="mentor",
                        args={"teacher": t["id"], "pupil": u["id"]},
                    )
                ]
    return []


def _recruitable(s, key):
    if any(h["id"] == key and (h["employed"] or h.get("retired")) for h in s["heroes"]):
        return False
    return all(ok for _, ok in e.recruit_requirements(s, key))


def team_can_grow(s):
    """团队跟着收入长：伙伴人数不超过「3 + 在售的自主产品数」。"""
    selling = sum(1 for d in s["products"] if d["active"] and not d["partner"])
    return sum(h["employed"] for h in s["heroes"]) < 3 + selling


INNOVATIVE_BUDGET = 2000  # 万：一条创新药路线约 2,800 万、三年；先有这么多可用现金再开始


def can_afford_innovative(s):
    return _cash(s) >= INNOVATIVE_BUDGET + RESERVE or -burn(s) >= 20


def hire_items(s, chapter=False, reason="", keys=None):
    from .engine import headcount

    owned = {h["profession"] for h in s["heroes"] if h["employed"]}
    room = headcount(s) + 3 <= FACILITIES[s["facility"]]["capacity"]
    if not chapter and not team_can_grow(s):
        return []
    out = []
    pool = keys or sorted(ROSTER, key=lambda k: (ROSTER[k]["profession"] in owned, ROSTER[k]["tier"], k))
    for key in pool:
        c = ROSTER[key]
        if not _recruitable(s, key):
            continue
        cost = e.recruit_cost(key)
        if c["tier"] >= 3 and key not in s["connections"]:
            researcher = next(
                (
                    h
                    for h in s["heroes"]
                    if h["employed"]
                    and h["profession"] == c["profession"]
                    and ability(h) >= 45
                    and h["id"] not in busy(s)
                ),
                None,
            )
            if researcher and sustainable(s, 120):
                out.append(
                    _item(
                        f"collaborate:{key}",
                        "collaborate",
                        f"和{c['name']}做合作课题",
                        f"{reason + ' · ' if reason else ''}{researcher['name']}负责 · 10 周 · ¥120 万，之后可以邀请",
                        chapter=chapter,
                        command="collaborate",
                        args={"character": key, "researcher": researcher["id"]},
                    )
                )
            continue
        salary = 1.3 + c["tier"] * 0.65 + c["ability"] * 0.018 + 2 * 0.42
        if not room or not sustainable(s, cost, salary):
            continue
        why = reason or ("补上空缺的专业" if c["profession"] not in owned else f"「{c['nickname']}」")
        out.append(
            _item(
                f"hire:{key}",
                "hire",
                f"邀请{c['name']}",
                f"{why} · ¥{cost:,} 万",
                chapter=chapter,
                command="hire",
                args={"character": key},
            )
        )
    return out


def personal_items(s):
    from . import stories

    out = []
    for h in s["heroes"]:
        if not h["employed"]:
            continue
        info = stories.options(s, h)
        if info["unlocked"] and not info["done"] and not info["running"]:
            out.append(
                _item(
                    f"personal:{h['id']}",
                    "personal",
                    f"{h['name']}的个人课题",
                    f"「{info['title']}」· 完成后招牌能力升级",
                    hero=h["id"],
                )
            )
    return out


def service_items(s):
    occupied = busy(s)
    idle = [h for h in s["heroes"] if h["employed"] and h["id"] not in occupied]
    picks = [v for v in assist.service_picks(s).values() if v["hero"]]
    if idle and picks:
        return [_item("services", "services", f"{len(idle)} 位伙伴空闲", "可以接技术服务赚周转金", tab="services")]
    return []


# ---------------- 章节的推进手段 ----------------


def _chapter(s):
    from .chapters import CHAPTERS

    index = s.get("chapter", 0)
    return (index, CHAPTERS[index]) if index < len(CHAPTERS) else (index, None)


def chapter_items(s):
    index, c = _chapter(s)
    if c is None:
        return []
    tag = f"第 {index + 1} 章需要"
    name = c["name"]
    out = []
    if name == "第一位专家":
        if not any(h["employed"] and h["rank"] >= 2 for h in s["heroes"]):
            out += promote_items(s, True, tag + "一位精英")
        if len(s["products"]) < 2 and not any(
            p["status"] not in ("approved", "failed", "terminated", "licensed") for p in s["projects"]
        ):
            out += project_items(s, True, tag + "两款药上市")
        if s["facility"] < 1:
            out += upgrade_items(s, True, "第 2 章的星：搬进联合研发所", optional=True)
        if not any(h["mentored"] for h in s["heroes"]):
            out += mentor_items(s, True, "第 2 章的星：完成一次带教")
    elif name == "第一款新药":
        if not any(p["kind"] == "innovative" and p["status"] not in ("failed", "terminated") for p in s["projects"]):
            if can_afford_innovative(s):
                out += project_items(s, True, tag + "一款创新药通过 II 期", only="innovative")
            elif not any(p["status"] in ACTIVE for p in s["projects"]):
                more = project_items(s, True, "先多一款药攒钱：创新药一条路约 ¥2,800 万、三年")
                out += [x for x in more if x["route"] != "innovative"]
    elif name == "攻坚" and can_afford_innovative(s):
        if s["facility"] < 2:
            out += upgrade_items(s, True, tag + "专业研究院")
        if not any(h["employed"] and h["rank"] >= 3 and h["profession"] in ("bio", "chem") for h in s["heroes"]):
            out += promote_items(s, True, tag + "一位生物或药化大师", professions=("bio", "chem"), rank=3)
        hard = [p for p in s["projects"] if p["kind"] == "innovative" and CATALOG[p["catalog"]].get("difficulty")]
        if not any(p["status"] not in ("failed", "terminated") for p in hard) and s["facility"] >= 2:
            out += project_items(s, True, tag + "攻克一种难治疾病", only="innovative", hard=True)
    elif name == "最后的难题":
        rows = gates.view(s, "n_abeta__mab") or []
        holders = set()
        for g in gates.GATES.values():
            for spec in (g["full"], g["partial"]):
                if spec[0] and spec[0] in ROSTER:
                    holders.add(spec[0])
        missing = [g["name"] for g in rows if g["state"] == "none"]
        if missing:
            out += hire_items(s, True, "阿尔茨海默缺人：" + "、".join(missing), keys=sorted(holders))
    return out


def suggestions(s, limit=3):
    """按优先级给出最多 limit 条成长建议。"""
    candidates = (
        chapter_items(s)
        + promote_items(s)
        # 没有仿制药或改良药在做时就建议一个：老产品会退市，现金流要接上
        + (project_items(s) if not _in_flight(s, ("generic", "improved")) else [])
        + personal_items(s)
        + hire_items(s)[:1]
        + service_items(s)
    )
    out, seen = [], set()
    for item in candidates:
        if item["key"] in seen:
            continue
        if item["command"] and item["ok"]:
            error = blocker(s, item["command"], item["args"])
            if error:
                item.update(ok=False, error=error)
        if not item["ok"] and not item["chapter"]:
            continue
        seen.add(item["key"])
        out.append(item)
        if len(out) >= limit:
            break
    return out


def blocker(s, command, args):
    """建议里用到的五个命令，直接按引擎的前提条件检查，返回挡住它的原因。

    不在副本上试执行：20 年的存档复制一次要好几毫秒。tests/test_guide.py 用真实引擎核对这里的判断。
    """
    from .engine import headcount

    occupied = busy(s)
    cash = _cash(s)
    people = [args.get(k) for k in ("character", "teacher", "pupil", "researcher") if args.get(k)]
    if command == "hire":
        people = []
    for who in people:
        if who in occupied:
            return f"{ROSTER[who]['name']}正在忙：{occupied[who]}"
    cost = {
        "promote": lambda: PROMOTION[next(h for h in s["heroes"] if h["id"] == args.get("character"))["rank"] + 1][
            "cost"
        ],
        "upgrade": lambda: FACILITIES[s["facility"] + 1]["cost"],
        "hire": lambda: e.recruit_cost(args["character"]),
        "collaborate": lambda: 120,
        "mentor": lambda: 60,
    }[command]()
    if command == "hire" and headcount(s) + 3 > FACILITIES[s["facility"]]["capacity"]:
        return "场地容纳不下新团队，请先扩建"
    if cash < cost:
        return f"扣除已承诺支出后，需要至少 ¥{cost:,.0f} 万"
    return None


# ---------------- 第一次出现的成长时刻 ----------------


def moments(s, seen=()):
    """当前成立的「第一次」成长时刻：(key, 事件数据)。seen 里的 key 已经提示过，跳过不算。"""
    seen = set(seen)
    out = []
    for h in _promotable(s):
        nxt = RANKS[h["rank"] + 1]
        out.append(
            (
                f"promote:{h['id']}:{h['rank'] + 1}",
                {"kind": "promote", "title": f"可以晋阶了：{h['name']}", "text": f"晋阶条件都满足了，可以升为{nxt}。"},
            )
        )
    if s["facility"] < len(FACILITIES) - 1 and needs_space(s):
        nxt = FACILITIES[s["facility"] + 1]
        if _cash(s) >= nxt["cost"] + RESERVE:
            out.append(
                (
                    f"upgrade:{s['facility'] + 1}",
                    {
                        "kind": "upgrade",
                        "title": f"买得起{nxt['name']}了",
                        "text": f"扩建后能容纳 {nxt['capacity']} 人。",
                    },
                )
            )
    for key, c in ROSTER.items():
        if f"hire:{key}" not in seen and (c["tier"] >= 2 or c.get("prodigy")) and _recruitable(s, key):
            out.append(
                (
                    f"hire:{key}",
                    {
                        "kind": "hire",
                        "title": f"{c['name']}愿意来了",
                        "text": f"「{c['nickname']}」的加入条件都满足了。",
                    },
                )
            )
    from . import stories

    for h in s["heroes"]:
        if h["employed"] and not h.get("personal") and f"personal:{h['id']}" not in seen:
            info = stories.options(s, h)
            if info["unlocked"] and not info["running"]:
                out.append(
                    (
                        f"personal:{h['id']}",
                        {
                            "kind": "personal",
                            "title": f"{h['name']}的个人课题可以开始了",
                            "text": f"「{info['title']}」",
                        },
                    )
                )
    if s["products"]:
        for kind in ("improved", "innovative"):
            if f"route:{kind}" not in seen and startable(s, kind, first=True):
                out.append(
                    (
                        f"route:{kind}",
                        {"kind": "route", "title": f"{KINDS[kind]}可以开始了", "text": "新项目里换一条路线看看。"},
                    )
                )
    return out
