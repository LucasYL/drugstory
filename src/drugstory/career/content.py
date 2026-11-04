"""Small authored roster and research catalogue; all amounts are game 万元."""

PROFESSIONS = {
    "bio": "生物与转化",
    "chem": "药化与分子工程",
    "tox": "药代与毒理",
    "proc": "制剂与工艺",
    "clinical": "临床与统计",
}
STATS = {"effect": "获益潜力", "safety": "安全窗口", "exposure": "暴露与等效", "quality": "工艺稳定"}
RANKS = {1: "见习", 2: "精英", 3: "大师", 4: "传奇"}
SKILLS = {"bio": "转化验证", "chem": "分子精修", "tox": "安全窗优化", "proc": "长效制剂", "clinical": "分层入组"}
SCENARIOS = {
    "foundation": {
        "name": "起步药坊",
        "cash": 2600,
        "starters": ["beaker", "pill"],
        "description": "从普通仿制与技术服务起家，慢慢养出第一支专家团队。",
        "goal": "2 款仿制、1 款改良、3 位精英或更高角色，现金为正",
    },
    "independent": {
        "name": "创新研究社",
        "cash": 3200,
        "starters": ["sprout", "beaker"],
        "description": "启动资金较多；先建立证据，挑战自主创新药。",
        "goal": "2 款自主创新药、1 位大师或更高角色，现金为正",
    },
    "licensing": {
        "name": "授权工作室",
        "cash": 2500,
        "starters": ["sprout", "beaker"],
        "description": "用可信数据换合作，以授权回款支持下一次研究。",
        "goal": "3 笔授权、累计首付款 1800 万，现金为正",
    },
    "platform": {
        "name": "技术工坊",
        "cash": 2800,
        "starters": ["pill", "ruler"],
        "description": "服务与改良制剂积累专长，培养能带徒弟的专家。",
        "goal": "3 个专业知识达 30、1 位大师、1 次创新药上市或授权，现金为正",
    },
}

# Recruitment tier is fixed. Career rank can grow, including for the starters.
_ROSTER = [
    ("beaker", "烧杯仔", "chem", 1, 34, "认真配好每一管溶液。"),
    ("pill", "小药丸", "proc", 1, 36, "想把每一批药都做得一样好。"),
    ("sprout", "豆芽博士", "bio", 1, 33, "名字有博士，履历还从零开始。"),
    ("bubble", "泡泡鼠", "tox", 1, 34, "总会多检查一次安全记录。"),
    ("ruler", "刻度喵", "clinical", 1, 35, "不放过曲线上的小偏差。"),
    ("catalyst", "催化巧手", "chem", 2, 52, "有限的优化里，多找一条可行路线。"),
    ("shield", "排雷队长", "tox", 2, 54, "安全窗口要靠证据，不能靠运气。"),
    ("crystal", "晶体匠", "proc", 2, 54, "会做样品，也要能稳定地放大。"),
    ("scout", "靶点猎手", "bio", 2, 53, "先问清楚机制，再决定押哪张牌。"),
    ("curve", "曲线侦探", "clinical", 2, 52, "在漂亮结果里寻找可重复的信号。"),
    ("wizard", "分子魔术师", "chem", 3, 70, "精修分子，同时尊重每一项代价。"),
    ("judge", "毒理判官", "tox", 3, 72, "能修的优化，不能修的及时叫停。"),
    ("forge", "制剂宗师", "proc", 3, 73, "让长效给药成为可验证的产品。"),
    ("bridge", "转化领航者", "bio", 3, 71, "连接实验模型和真实的患者问题。"),
    ("strategist", "临床军师", "clinical", 3, 72, "为正确的人群设计有解释力的试验。"),
    ("star", "靶点星君", "bio", 4, 86, "建立研究平台，让新机制有机会被理解。"),
    ("alchemist", "分子炼金王", "chem", 4, 87, "带出能独立攻关的下一代分子工程师。"),
    ("guardian", "生命守望者", "tox", 4, 87, "突破性药物，也不能跨过安全底线。"),
    ("architect", "药剂造物主", "proc", 4, 88, "从一粒样品，到稳定供给的产品线。"),
    ("oracle", "终局观测者", "clinical", 4, 87, "越大的试验，越需要准确面对不确定性。"),
]
ROSTER = {
    k: {"key": k, "name": n, "profession": p, "tier": r, "ability": a, "story": t} for k, n, p, r, a, t in _ROSTER
}
FACILITIES = [
    {"name": "街角实验室", "cost": 0, "rent": 1.5, "capacity": 18, "slots": 1, "lines": 0},
    {"name": "联合研发所", "cost": 700, "rent": 4, "capacity": 32, "slots": 2, "lines": 2},
    {"name": "专业研究院", "cost": 2400, "rent": 10, "capacity": 56, "slots": 3, "lines": 5},
    {"name": "星火科学城", "cost": 6500, "rent": 24, "capacity": 90, "slots": 4, "lines": 9},
]

# Fictional reference products, explicitly available for generic development.
_GENERICS = [
    ("g_pressure", "稳压片", "血压管理", "pressure", "常规口服片剂"),
    ("g_lipid", "轻脂片", "血脂管理", "lipid", "低剂量片剂含量均匀性"),
    ("g_pain", "舒痛胶囊", "疼痛管理", "pain", "胶囊溶出一致性"),
    ("g_sugar", "平糖片", "血糖管理", "sugar", "大剂量片剂稳定性"),
    ("g_allergy", "晴鼻片", "过敏症状", "allergy", "低剂量口服制剂"),
    ("g_inflammation", "轻炎片", "炎症管理", "inflammation", "口服制剂与杂质控制"),
]
CATALOG = {
    k: {
        "key": k,
        "name": n,
        "kind": "generic",
        "indication": indication,
        "market": market,
        "target": "已知有效成分",
        "modality": "小分子",
        "description": desc,
        "difficulty": 0,
        "knowledge": 0,
        "peak": 27,
        "available_week": 0,
    }
    for k, n, indication, market, desc in _GENERICS
}
for k, n, market, goal, skill in [
    ("i_long", "稳压长效方案", "pressure", "减少给药频次", "proc"),
    ("i_gentle", "舒痛耐受方案", "pain", "改善耐受性", "tox"),
    ("i_delivery", "轻炎给药方案", "inflammation", "改善给药体验", "proc"),
]:
    CATALOG[k] = {
        "key": k,
        "name": n,
        "kind": "improved",
        "indication": goal,
        "market": market,
        "target": "已有治疗改良",
        "modality": "小分子",
        "description": goal + "需补充相应临床证据",
        "difficulty": 0,
        "knowledge": 15,
        "profession": skill,
        "peak": 60,
        "available_week": 0,
    }
for k, n, indication, market, target, modality, hard, peak in [
    ("n_lung", "肺癌精准抑制", "特定突变肺癌", "lung", "EGFR", "小分子", 0, 160),
    ("n_inflammation", "炎症信号抑制", "免疫炎症疾病", "inflammation", "JAK", "小分子", 0, 140),
    ("n_lipid", "降脂抗体计划", "难治性血脂异常", "lipid", "PCSK9", "抗体", 0, 145),
    ("n_resistance", "耐药突破计划", "耐药肺癌", "lung", "新型耐药机制", "分子降解剂", 1, 240),
    ("n_reset", "免疫重置计划", "难治性免疫炎症", "inflammation", "免疫重置机制", "双抗", 1, 220),
    ("n_rna", "长效沉默计划", "遗传性血脂异常", "lipid", "新型调脂机制", "RNA 药物", 1, 230),
]:
    CATALOG[k] = {
        "key": k,
        "name": n,
        "kind": "innovative",
        "indication": indication,
        "market": market,
        "target": target,
        "modality": modality,
        "description": "机制不确定性较高" if hard else "成熟机制的新候选药",
        "difficulty": hard,
        "knowledge": 45 if hard else 0,
        "peak": peak,
        "available_week": 0,
    }
KINDS = {"generic": "普通仿制药", "improved": "改良药", "innovative": "创新药"}
PATHS = {
    "generic": ["formulation", "quality", "be", "review"],
    "improved": ["design", "preclinical", "bridge", "confirm", "review"],
    "innovative": ["optimize", "preclinical", "I", "II", "III", "review"],
}
# Stage evidence is sampled from the candidate, never from accumulated team points.
STAGES = {
    "formulation": {
        "name": "处方与工艺",
        "weeks": 10,
        "cost": 60,
        "roles": ["proc", "chem"],
        "limits": {"quality": 48},
        "noise": 9,
        "question": "能否做出可重复的处方和工艺？",
    },
    "quality": {
        "name": "质量与稳定性",
        "weeks": 8,
        "cost": 40,
        "roles": ["proc", "tox"],
        "limits": {"quality": 62, "safety": 58},
        "noise": 7,
        "question": "不同批次是否一致，能否保持稳定？",
    },
    "be": {
        "name": "生物等效性验证",
        "weeks": 10,
        "cost": 90,
        "roles": ["clinical", "tox"],
        "limits": {"exposure": 64},
        "noise": 6,
        "question": "相对参比制剂，暴露与释放是否符合要求？",
    },
    "design": {
        "name": "改良方案开发",
        "weeks": 16,
        "cost": 140,
        "roles": ["proc", "chem"],
        "limits": {"quality": 52},
        "noise": 10,
        "question": "改良目标能否通过实际制剂实现？",
    },
    "optimize": {
        "name": "候选优化与验证",
        "weeks": 16,
        "cost": 160,
        "roles": ["bio", "chem"],
        "limits": {"effect": 42, "quality": 40},
        "noise": 12,
        "question": "候选的活性和选择性是否值得继续？",
    },
    "preclinical": {
        "name": "临床前与申报准备",
        "weeks": 20,
        "cost": 220,
        "roles": ["tox", "proc"],
        "limits": {"safety": 47, "exposure": 45, "quality": 47},
        "noise": 9,
        "question": "毒理、暴露和生产资料是否支持进入人体试验？",
    },
    "I": {
        "name": "I 期安全与剂量",
        "weeks": 24,
        "cost": 280,
        "roles": ["clinical", "tox"],
        "limits": {"safety": 63, "exposure": 61},
        "noise": 8,
        "question": "人体内是否有可用剂量和安全窗口？",
    },
    "II": {
        "name": "II 期概念验证",
        "weeks": 40,
        "cost": 650,
        "roles": ["clinical", "bio"],
        "limits": {"effect": 70, "safety": 58},
        "noise": 8,
        "question": "目标患者中是否出现可靠的获益信号？",
    },
    "III": {
        "name": "III 期确认获益",
        "weeks": 64,
        "cost": 1350,
        "roles": ["clinical", "proc"],
        "limits": {"effect": 75, "safety": 66},
        "noise": 6,
        "question": "更大样本能否确认获益与风险？",
    },
    "bridge": {
        "name": "改良桥接研究",
        "weeks": 24,
        "cost": 250,
        "roles": ["clinical", "tox"],
        "limits": {"exposure": 62, "safety": 60},
        "noise": 7,
        "question": "改动后的暴露、安全与原有证据能否衔接？",
    },
    "confirm": {
        "name": "改良价值确认",
        "weeks": 28,
        "cost": 380,
        "roles": ["clinical", "proc"],
        "limits": {"effect": 63, "safety": 62},
        "noise": 6,
        "question": "给药或耐受性的改善是否确实成立？",
    },
    "review": {
        "name": "上市审评与质量核查",
        "weeks": 8,
        "cost": 60,
        "roles": ["proc", "clinical"],
        "limits": {"quality": 65},
        "noise": 4,
        "question": "临床证据与持续生产质量是否完整？",
    },
}
CLINICAL = {"I", "II", "III", "bridge", "confirm", "be"}
PLANS = {
    "standard": {"name": "标准方案", "time": 1, "cost": 1, "noise": 1, "text": "按标准规模执行，保留研究不确定性。"},
    "expanded": {
        "name": "扩大验证",
        "time": 1.25,
        "cost": 1.4,
        "noise": 0.68,
        "text": "提高判断精度，也更容易揭露真实短板；不能保证通过。",
    },
    "focused": {
        "name": "分层入组",
        "time": 1.12,
        "cost": 1.18,
        "noise": 0.9,
        "text": "需要分层证据与临床能力；只研究获益人群，市场缩小 35%。",
    },
}
EXPERIMENTS = {
    "validate": {
        "name": "专项复核",
        "cost": 65,
        "weeks": 6,
        "role": None,
        "text": "缩小一项判断的范围。好消息和坏消息都有价值，不提高药物本质。",
    },
    "translate": {
        "name": "转化验证",
        "cost": 100,
        "weeks": 8,
        "role": "bio",
        "text": "需要生物能力 55；更清楚地判断机制和获益能否支持后续临床。",
    },
    "refine": {
        "name": "定向优化",
        "cost": 110,
        "weeks": 8,
        "role": None,
        "text": "每候选最多两次；改善一项性质，同时付出另一项性质的代价。",
    },
    "marker": {
        "name": "人群分层研究",
        "cost": 130,
        "weeks": 8,
        "role": "bio",
        "text": "需要生物能力 55；验证是否有可重复的获益人群，结果可能不支持分层。",
    },
}
TERMS = {
    "cash": {"name": "现金优先", "upfront": 1, "royalty": 0.12, "cost_share": 0},
    "royalty": {"name": "长期分成", "upfront": 0.65, "royalty": 0.24, "cost_share": 0},
    "codevelop": {"name": "共同开发", "upfront": 0.4, "royalty": 0.42, "cost_share": 0.35},
}
PROMOTION = {
    2: {"xp": 28, "cases": 2, "knowledge": 8, "facility": 0, "cost": 90},
    3: {"xp": 85, "cases": 5, "knowledge": 35, "facility": 1, "cost": 450},
    4: {"xp": 170, "cases": 9, "knowledge": 75, "facility": 2, "cost": 1400},
}


def validate():
    assert len(ROSTER) == len(_ROSTER)
    for product in CATALOG.values():
        assert product["kind"] in PATHS and product["peak"] > 0
    for stages in PATHS.values():
        assert all(key in STAGES for key in stages)
    for stage in STAGES.values():
        assert stage["weeks"] > 0 and stage["cost"] > 0
        assert set(stage["roles"]) <= PROFESSIONS.keys()
        assert set(stage["limits"]) <= STATS.keys()
    for hero in ROSTER.values():
        assert hero["profession"] in PROFESSIONS and hero["tier"] in RANKS


validate()
