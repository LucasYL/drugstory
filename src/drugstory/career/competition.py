"""Seeded rivals with visible milestones, finite commercial impact and no approval inflation."""

from . import challenge
from .model import log, rand

MARKETS = {
    "blood": "血液疾病",
    "neuro": "神经疾病",
    "rare": "罕见疾病",
    "infection": "感染与预防",
    "pressure": "血压管理",
    "lipid": "血脂管理",
    "pain": "疼痛管理",
    "sugar": "血糖管理",
    "allergy": "过敏症状",
    "inflammation": "炎症疾病",
    "lung": "肺癌",
}
STYLES = {
    "scale": {
        "name": "规模制造",
        "text": "偏好成熟市场，推进快；用低价和供货能力竞争。",
        "weeks": [28, 32, 24],
        "odds": [0.88, 0.83, 0.94],
        "phases": ["工艺开发", "等效性验证", "质量审评"],
        "strength": 1.1,
    },
    "pioneer": {
        "name": "前沿创新",
        "text": "偏好新机制，失败较多；成功时更容易拿到创新荣誉。",
        "weeks": [32, 40, 56, 64, 16],
        "odds": [0.86, 0.74, 0.47, 0.70, 0.93],
        "phases": ["临床前", "I 期", "II 期", "III 期", "审评"],
        "strength": 1.35,
    },
    "partner": {
        "name": "合作整合",
        "text": "收购较成熟的证据，风险居中；周期和合作方向会变化。",
        "weeks": [36, 52, 16],
        "odds": [0.68, 0.76, 0.94],
        "phases": ["概念验证", "确认试验", "审评"],
        "strength": 0.95,
    },
}


def initialize(s):
    result = []
    for i, (name, style, market) in enumerate(
        [("银叶制药", "scale", "lipid"), ("赤杉研究所", "pioneer", "inflammation"), ("蓝鲸药业", "partner", "lung")]
    ):
        rival = {
            "id": str(i),
            "name": name,
            "style": style,
            "market": market,
            "pipeline_market": market,
            "active": False,
            "cycles": 0,
            "stage": 0,
            "status": "developing",
            "last_update": "公布研发方向",
            "year_points": 0,
            "history": [],
            "portfolio": [],
            "launch": 0,
            "end": 0,
        }
        start_stage(s, rival)
        result.append(rival)
    s["rivals"] = result


def start_stage(s, r):
    spec = STYLES[r["style"]]
    duration = max(
        12,
        round(
            spec["weeks"][r["stage"]] * rand(s, "rival-duration", r["id"], r["cycles"], r["stage"]).uniform(0.8, 1.25)
        ),
    )
    if challenge.enabled(s):
        duration = max(10, round(duration * 0.85))
    r["due"] = s["week"] + duration
    remaining = sum(spec["weeks"][r["stage"] + 1 :])
    r["eta_low"] = r["due"] + round(remaining * 0.8)
    r["eta_high"] = r["due"] + round(remaining * 1.3) + 12
    r["launch"] = (r["eta_low"] + r["eta_high"]) // 2
    r["phase"] = spec["phases"][r["stage"]]


def restart(s, r):
    r["cycles"] += 1
    r["stage"] = 0
    r["status"] = "developing"
    markets = (
        ["pressure", "lipid", "pain", "sugar", "allergy", "inflammation"]
        if r["style"] == "scale"
        else ["lung", "inflammation", "lipid"]
    )
    r["pipeline_market"] = rand(s, "rival-market", r["id"], r["cycles"]).choice(markets)
    start_stage(s, r)
    r["last_update"] = "新计划启动：" + MARKETS[r["pipeline_market"]]
    log(s, f"竞争情报：{r['name']}{r['last_update']}，先观察证据与预计窗口。")


def step(s):
    for r in s["rivals"]:
        for d in r["portfolio"]:
            if d["active"] and s["week"] >= d["end"]:
                d["active"] = False
        r["active"] = any(d["active"] for d in r["portfolio"])
        if s["week"] < r["due"]:
            continue
        if r["status"] == "rebuilding":
            restart(s, r)
            continue
        spec = STYLES[r["style"]]
        rng = rand(s, "rival-result", r["id"], r["cycles"], r["stage"])
        roll = rng.random()
        odds = min(0.96, spec["odds"][r["stage"]] + (0.04 if challenge.enabled(s) else 0))
        if roll > odds:
            r["status"] = "rebuilding"
            r["due"] = s["week"] + rng.randint(24, 56)
            r["last_update"] = r["phase"] + "未获支持，调整方向"
        elif not r.get("delayed") and rng.random() < 0.16:
            r["due"] = s["week"] + rng.randint(8, 20)
            r["delayed"] = True
            r["eta_low"] += 12
            r["eta_high"] += 20
            r["last_update"] = r["phase"] + "进度延迟，等待补充数据"
        else:
            r["delayed"] = False
            r["year_points"] += 8
            if r["stage"] == len(spec["phases"]) - 1:
                r["market"] = r["pipeline_market"]
                r["active"] = True
                r["end"] = s["week"] + rng.randint(192, 288)
                r["portfolio"].append(
                    {
                        "market": r["market"],
                        "active": True,
                        "end": r["end"],
                        "strength": spec["strength"] * (1.25 if challenge.enabled(s) else 1),
                        "launched": s["week"],
                    }
                )
                r["last_update"] = MARKETS[r["market"]] + "产品上市"
                r["year_points"] += 30
                r["status"] = "rebuilding"
                r["due"] = s["week"] + rng.randint(32, 64)
            else:
                r["last_update"] = r["phase"] + "取得支持证据"
                r["stage"] += 1
                start_stage(s, r)
        event = {"week": s["week"], "text": r["last_update"]}
        r["history"].append(event)
        log(s, f"竞争情报：{r['name']}{r['last_update']}。市场份额会变化，临床标准不变。")


# 先发优势：对手在我方产品之后才上市，先占住的医院和渠道不容易丢，它的影响只按这个比例算
FIRST_MOVER = 0.6


def pressure(s, market, since=None):
    """同市场对手的竞争强度（0–3）。since 是我方产品的上市周，比它晚上市的对手产品按 FIRST_MOVER 计。"""
    total = 0
    for r in s["rivals"]:
        active = [d for d in r.get("portfolio", []) if d["active"] and d["market"] == market]
        total += sum(
            d["strength"] * (FIRST_MOVER if since is not None and d.get("launched", 0) > since else 1) for d in active
        )
        # Historical test/import records can have a single public active product.
        if not r.get("portfolio") and r["active"] and r["market"] == market:
            total += 1
    return min(3.0, total)


def public(s):
    return [
        {
            **{
                k: r[k]
                for k in (
                    "id",
                    "name",
                    "style",
                    "phase",
                    "status",
                    "market",
                    "pipeline_market",
                    "active",
                    "eta_low",
                    "eta_high",
                    "last_update",
                    "year_points",
                )
            },
            "style_name": STYLES[r["style"]]["name"],
            "description": STYLES[r["style"]]["text"],
            "market_name": MARKETS[r["pipeline_market"]],
            "history": r["history"][-5:],
            "products": [
                {"market": MARKETS[d["market"]], "remaining": max(0, d["end"] - s["week"])}
                for d in r["portfolio"]
                if d["active"]
            ],
        }
        for r in s["rivals"]
    ]
