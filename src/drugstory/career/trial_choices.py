"""One pre-outcome operations decision during each substantial clinical stage."""

from .model import available_money, check, log, spend

STAGES = {"I", "II", "III", "bridge", "confirm"}
KEEP = {
    "key": "keep",
    "name": "按既定方案继续",
    "cost": 0,
    "weeks": 0,
    "noise": 1,
    "text": "保持原预算、入组范围和精度，完成当前试验。",
}
CHOICES = {
    "I": [
        KEEP,
        {
            "key": "monitor",
            "name": "补充剂量监测",
            "cost": 60,
            "weeks": 3,
            "noise": 0.8,
            "stat": "safety",
            "text": "多 3 周、60 万；安全观察误差减少 20%，不改变候选安全性质。",
        },
    ],
    "II": [
        KEEP,
        {
            "key": "representative",
            "name": "补齐代表性中心",
            "cost": 120,
            "weeks": 4,
            "noise": 0.82,
            "text": "多 4 周、120 万；平衡不同中心的入组，全部观察误差减少 18%。",
        },
        {
            "key": "regional",
            "name": "限定中心网络",
            "cost": 0,
            "weeks": -3,
            "noise": 1,
            "reach": 0.85,
            "text": "缩短 3 周，限定后续研究的中心网络；上市覆盖缩小 15%，没有药效加成。III 期沿用。",
        },
    ],
    "III": [
        KEEP,
        {
            "key": "audit",
            "name": "独立数据核查",
            "cost": 180,
            "weeks": 6,
            "noise": 0.78,
            "text": "多 6 周、180 万；观察误差减少 22%，更清楚地面对好消息和坏消息。",
        },
        {
            "key": "remote",
            "name": "集中远程随访",
            "cost": 100,
            "weeks": -6,
            "noise": 1.12,
            "text": "投入 100 万、缩短 6 周；随访方式更快但误差增加 12%。",
        },
    ],
    "bridge": [
        KEEP,
        {
            "key": "support",
            "name": "加强给药记录",
            "cost": 70,
            "weeks": 4,
            "noise": 0.82,
            "stat": "exposure",
            "text": "多 4 周、70 万；改善实际给药记录，暴露观察误差减少 18%。",
        },
    ],
    "confirm": [
        KEEP,
        {
            "key": "support",
            "name": "补充患者随访",
            "cost": 90,
            "weeks": 4,
            "noise": 0.82,
            "text": "多 4 周、90 万；改善使用与症状记录，观察误差减少 18%。",
        },
    ],
}


def initialize(p):
    key = p["execution"]["key"]
    p["execution"]["checkpoint_at"] = p["left"] // 2 if key in STAGES else None
    p["execution"]["checkpoint_done"] = False


def reached(p):
    e = p.get("execution", {})
    return (
        not p.get("experiment")
        and e.get("checkpoint_at") == p["left"]
        and not e.get("checkpoint_done")
        and p["left"] > 0
    )


def view(p):
    if p["status"] != "checkpoint":
        return None
    return {
        "title": "试验进行到一半：怎样把后半程做扎实？",
        "text": "当前只讨论执行和入组安排，尚未查看最终疗效结果。人员保持占用，决定前研发计时暂停。",
        "choices": CHOICES[p["execution"]["key"]],
    }


def resolve(s, p, choice):
    from .science import phase_probability

    check(p["status"] == "checkpoint", "当前没有临床中途决策")
    e = p["execution"]
    option = next((c for c in CHOICES[e["key"]] if c["key"] == choice), None)
    check(option is not None and not e["checkpoint_done"], "请选择尚未处理的研究安排")
    available_money(s, option["cost"])
    spend(s, option["cost"], "trial_operations")
    old_left = p["left"]
    p["left"] = max(1, old_left + option["weeks"])
    p["cost_per_week"] *= old_left / p["left"]  # Preserve the remaining reserved budget exactly.
    p["spent"] += option["cost"]
    e["cost"] += option["cost"]
    e["weeks"] += p["left"] - old_left
    for stat in e["noise_by_stat"]:
        if not option.get("stat") or option["stat"] == stat:
            e["noise_by_stat"][stat] *= option["noise"]
    e["noise"] = sum(e["noise_by_stat"].values()) / len(e["noise_by_stat"])
    e["probability"] = phase_probability(p, e["key"], e["plan"], e["noise_by_stat"])
    e["checkpoint_done"] = True
    p["trial_reach"] = min(p.get("trial_reach", 1), option.get("reach", 1))
    p.setdefault("trial_history", []).append({"week": s["week"], "stage": e["key"], **option})
    p["status"] = "running"
    p["deferred"] = False
    log(s, f"{p['name']}：选择{option['name']}，剩余 {p['left']} 周；新增支出 ¥{option['cost']} 万。")
