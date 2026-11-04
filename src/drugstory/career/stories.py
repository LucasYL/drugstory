"""Authored personal projects: work together, make a choice, keep a permanent legacy."""

from .content import PROFESSIONS, ROSTER
from .model import ability, available_money, busy, check, free_team, gain_work, hero, log, spend

# Every character has an authored professional question, not a random stat request.
STORIES = {
    "beaker": ("最后一管也要一样", "烧杯仔发现，交给别人的操作记录总差一小步。他想让新人也能复现自己的实验。", "proc"),
    "pill": ("第一千粒药", "小药丸守着第一批样品：样品合格，还不等于一千粒都一样。", "chem"),
    "sprout": ("模型之外的病人", "豆芽博士想知道，培养皿中的发现怎样才能回答患者的问题。", "clinical"),
    "bubble": ("没有被圈出的异常", "泡泡鼠找到了被平均值掩盖的小异常，想建立一套交叉核对流程。", "clinical"),
    "ruler": ("曲线里的空白", "刻度喵注意到失访者从漂亮曲线里消失了，决定追踪缺失数据的来处。", "bio"),
    "catalyst": ("第二条合成路线", "催化巧手不想让项目只依赖一条漂亮却脆弱的路线，准备和工艺伙伴一起拆解。", "proc"),
    "shield": ("红灯之前", "排雷队长希望把警报提前到正式试验之前，让临床团队理解安全信号。", "clinical"),
    "crystal": ("雨季也能交货", "晶体匠把不同储存条件下的样品摆成一排，想解决稳定性与供货的矛盾。", "tox"),
    "scout": ("靶点的反例", "靶点猎手主动收集不支持假说的模型，想找出机制成立的边界。", "chem"),
    "curve": ("两家中心的分歧", "曲线侦探遇到两家中心完全不同的趋势，决定先核查流程再解释结果。", "tox"),
    "wizard": ("魔术也要有说明书", "分子魔术师愿意公开自己的失败路线，让优化经验变成可交接的方法。", "proc"),
    "judge": ("剂量边界备忘录", "毒理判官准备把停止规则讲给临床伙伴听，让每一次加量都有依据。", "clinical"),
    "forge": ("长效的最后一公里", "制剂宗师想确认便利的给药方式在实际使用中仍然可靠。", "clinical"),
    "bridge": ("跨过转化断桥", "转化领航者要把模型、暴露和病人证据放到同一张桌上。", "tox"),
    "strategist": ("入组地图上的空白", "临床军师想知道被排除在试验外的人群，会怎样改变结论的适用范围。", "bio"),
    "star": ("把望远镜交给后来者", "靶点星君准备把多年机制笔记变成团队能共同使用的研究工具。", "chem"),
    "alchemist": ("炼金王的公开配方", "分子炼金王邀请工艺伙伴质疑自己的设计，希望留下可复现的体系。", "proc"),
    "guardian": ("守望者的第二双眼", "生命守望者想建立独立复核，让重大决定不只依赖一个专家。", "clinical"),
    "architect": ("一座不会停摆的药厂", "药剂造物主想把工艺与安全交接做成一张任何班组都能读懂的地图。", "tox"),
    "oracle": ("给未来的一封统计信", "终局观测者决定留下分析计划与反例，提醒后来者别把偶然当作发现。", "bio"),
}
CHOICES = {
    "verify": {
        "name": "交叉复现",
        "weeks": 12,
        "cost": 140,
        "text": (
            "与指定专业伙伴同阶段工作时，相关专业指标的观察误差减少 8%。"
            "临床专业作用于临床观察，其他专业作用于对应指标。"
        ),
    },
    "handoff": {
        "name": "联合交接",
        "weeks": 8,
        "cost": 80,
        "text": "先建立共用操作流程；与指定专业伙伴承担相关阶段时，阶段费用减少 5%。",
    },
}


def options(s, h):
    title, story, role = STORIES[h["id"]]
    project_work = sum(v for k, v in h["work"].items() if k.startswith(("g_", "i_", "n_")))
    requirements = [
        ("经营至少一年", s["week"] >= 48),
        ("专业能力至少 40", ability(h) >= 40),
        ("完成一个项目或参与三次研究阶段", bool(h["cases"]) or project_work >= 3),
    ]
    running = next((j for j in s["jobs"] if j.get("owner") == h["id"] and j["kind"] == "personal"), None)
    peers = [x for x in s["heroes"] if x["employed"] and x["profession"] == role and x["id"] not in busy(s)]
    return {
        "title": title,
        "story": story,
        "partner_role": role,
        "partner_name": PROFESSIONS[role],
        "checks": [{"text": t, "ok": ok} for t, ok in requirements],
        "unlocked": all(ok for _, ok in requirements),
        "done": h.get("personal"),
        "running": {"left": running["left"]} if running else None,
        "partners": [x["id"] for x in peers],
        "choices": CHOICES,
    }


def begin(s, character: str, partner: str, choice: str):
    h, peer = hero(s, character), hero(s, partner)
    info = options(s, h)
    check(info["unlocked"] and not info["done"] and not info["running"], "个人课题尚未解锁、已经完成或正在进行")
    check(choice in CHOICES and peer["profession"] == info["partner_role"], "请选择课题需要的伙伴与研究方式")
    free_team(s, [character, partner])
    c = CHOICES[choice]
    available_money(s, c["cost"])
    spend(s, c["cost"], "personal_projects")
    s["jobs"].append(
        {
            "kind": "personal",
            "owner": character,
            "choice": choice,
            "heroes": [character, partner],
            "name": h["name"] + " · " + info["title"],
            "left": c["weeks"],
        }
    )
    log(s, f"{h['name']}与{peer['name']}开始个人课题「{info['title']}」，选择{c['name']}。")


def finish(s, job):
    h = hero(s, job["owner"])
    h["personal"] = {"choice": job["choice"], "partner": job["heroes"][1], "week": s["week"]}
    gain_work(s, job["heroes"], "personal-" + h["id"], 12)
    log(s, f"个人课题完成：{h['name']}留下「{STORIES[h['id']][0]}」。协作能力已解锁，也可抵一项晋阶履历要求。")


def active(s, ids):
    roles = {h["profession"] for h in s["heroes"] if h["id"] in ids and h["employed"]}
    return [
        h
        for h in s["heroes"]
        if h["employed"] and h["id"] in ids and h.get("personal") and STORIES[h["id"]][2] in roles
    ]


assert set(STORIES) == set(ROSTER)
