"""Stable public domain events; scenes do not infer work by parsing journal prose."""

TEMPLATES = {
    "work_completed": "{name}完成一批{stage}：{detail}",
    "evidence_received": "{name}收到第 {batch} 批{stage}数据：{detail}",
    "phase_started": "{name}开始{stage}，预计 {weeks} 周{note}。",
    "phase_finished": "{name}完成{stage}：{outcome}。",
    "character_promoted": "{name}晋升为{rank}。",
    "personal_completed": "{name}完成个人课题，招牌能力升级。",
    "equipment_upgraded": "{name}升级到 {level} 级，可以承担更复杂的开发工作。",
    "facility_upgraded": "搬入{name}：更多团队、自营临床席位和生产线，房租也涨到每周 ¥{rent} 万。",
    "product_launched": "{name}获批上市！{text}",
    "service_completed": "{name}交付{service}，收到 ¥{reward} 万。",
    "deal_signed": "{name}签下{terms}：首付款 ¥{upfront} 万已到账，后续款项按实际里程碑。",
    "patent_filed": "{name}提交核心专利，独占期预计到第 {expires_year} 年。",
    "patent_granted": "{name}的核心专利获得授权，口碑 +{reputation}。",
    "patent_expired": "{name}专利到期，仿制药进场，销售会在半年内明显下滑。",
    "milestone_reached": "公司大事记：{title}。",
    "award_won": "年度颁奖：研究社获得{name}！奖金 ¥{prize} 万，作品和培养记录已刻入奖杯室。",
    "legacy_reached": "终局荣誉达成：{name}！研究社的成果与培养传承被正式认可。",
    "cash_changed": "本次安排资金变化 ¥{amount:,.1f} 万。",
    "notice": "{text}",
}


def emit(s, kind, *, actors=None, project=None, room=None, data=None, journal=True):
    if kind not in TEMPLATES:
        raise ValueError("Unknown public event type")
    payload = data or {}
    s["event_seq"] = s.get("event_seq", 0) + 1
    item = {
        "version": 1,
        "id": s["event_seq"],
        "week": s["week"],
        "type": kind,
        "actors": list(actors or []),
        "project": project,
        "room": room,
        "data": payload,
    }
    s.setdefault("events", []).append(item)
    s["events"] = s["events"][-96:]
    s.setdefault("transition_events", []).append(item)
    if journal:
        s["journal"].append({"week": s["week"], "text": TEMPLATES[kind].format(**payload)})
        s["journal"] = s["journal"][-600:]
    return item
