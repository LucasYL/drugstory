"""Small, explicit character traits and mutually exclusive career specializations."""

from .content import ROSTER

TRAITS = {
    "thrift": ("精打细算", "负责非临床研究时，阶段费减少 5%。"),
    "quality": ("批次守护", "参与研究时，工艺指标的观察误差减少 6%。"),
    "learner": ("越学越会", "专业培训额外获得 2 点经验。"),
    "safety": ("风险嗅觉", "参与研究时，安全指标的观察误差减少 6%。"),
    "clinical": ("数据直觉", "参与临床时，观察误差减少 5%。"),
    "refine": ("精修匠心", "定向优化额外改善 1 点，同时承担对应的性质代价。"),
    "speed": ("调度能手", "担任本阶段相关专业负责人时，工期减少 8%。"),
    "screen": ("线索捕手", "参与候选筛选时，初始证据误差减少 10%。"),
    "mentor": ("薪火传承", "导师课题给学习者额外增加 5 点经验。"),
}
ASSIGNMENTS = dict(
    zip(
        ROSTER,
        [
            "thrift",
            "quality",
            "learner",
            "safety",
            "clinical",
            "refine",
            "safety",
            "speed",
            "screen",
            "clinical",
            "refine",
            "safety",
            "quality",
            "screen",
            "speed",
            "screen",
            "mentor",
            "safety",
            "quality",
            "clinical",
        ],
        strict=True,
    )
)
FOCUS = {
    "precision": {
        "name": "深研专长",
        "description": "对应专业指标的观察误差减少 10%；临床专业作用于临床阶段全部指标。",
    },
    "efficiency": {
        "name": "组织专长",
        "description": "担任相关专业负责人时，阶段工期减少 8%；与角色特质合计最多减少 15%。",
    },
}


def trait(key):
    name = ASSIGNMENTS.get(key, "mentor")
    return {"key": name, "name": TRAITS[name][0], "description": TRAITS[name][1]}


def has(s, ids, kind):
    return any(ASSIGNMENTS.get(h["id"]) == kind for h in s["heroes"] if h["id"] in ids and h["employed"])
