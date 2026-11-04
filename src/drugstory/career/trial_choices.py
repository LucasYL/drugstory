"""Interim information supports continuation or futility stopping, never a paid reroll."""

from .content import STAGES as STAGE_INFO
from .model import check, log

STAGES = {"I", "II", "III", "bridge", "confirm"}
KEEP = {
    "key": "keep",
    "name": "按既定方案继续",
    "cost": 0,
    "weeks": 0,
    "noise": 1,
    "text": "继续收集剩余批次，按开工时约定的全部证据判断；不会重新抽取已有数据。",
}
STOP = {
    "key": "stop",
    "name": "提前止损",
    "cost": 0,
    "weeks": 0,
    "noise": 1,
    "text": "保留已取得的证据，停止项目并释放人员与未支出预算；不计为临床失败或获批。",
}


def initialize(p):
    e = p["execution"]
    e["checkpoint_at"] = e["weeks"] - ((e["weeks"] + 1) // 2) if e["key"] in STAGES else None
    e["checkpoint_done"] = False


def reached(p):
    e = p.get("execution", {})
    return (
        not p.get("experiment")
        and e.get("checkpoint_at") == p["left"]
        and not e.get("checkpoint_done")
        and p["left"] > 0
    )


def view(p):
    from .readouts import forecast

    if p["status"] != "checkpoint":
        return None
    probability = forecast(p)
    return {
        "title": "期中证据已到：继续研究，还是提前止损？",
        "text": "目前取得两批初步读数。不能据此提前宣布成功；扩大样本与人群方案需要在开工前确定。",
        "choices": [KEEP, STOP],
        "chance": round(100 * probability) if probability is not None else None,
    }


def resolve(s, p, choice):
    check(p["status"] == "checkpoint" and not p["execution"]["checkpoint_done"], "当前没有临床中途决策")
    check(choice in ("keep", "stop"), "期中只能继续既定方案或提前止损")
    p["execution"]["checkpoint_done"] = True
    p.setdefault("trial_history", []).append({"week": s["week"], "stage": p["execution"]["key"], "key": choice})
    if choice == "stop":
        from .engine import terminate

        terminate(s, p["id"])
    else:
        p.update(status="running", deferred=False)
        log(s, p["name"] + "继续" + STAGE_INFO[p["execution"]["key"]]["name"] + "，既有读数保留，等待剩余证据。")
