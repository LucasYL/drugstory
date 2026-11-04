"""Stable public domain events; scenes do not infer work by parsing journal prose."""

TEMPLATES = {
    "work_completed": "{name}完成一批{stage}工作：{detail}",
    "evidence_received": "{name}收到第 {batch} 批{stage}证据。",
    "phase_started": "{name}开始{stage}，预计 {weeks} 周。",
    "phase_finished": "{name}完成{stage}：{outcome}。",
    "character_promoted": "{name}晋升为{rank}。",
    "personal_completed": "{name}完成个人课题，招牌能力升级。",
    "equipment_upgraded": "{name}升级到 {level} 级，可以承担更复杂的开发工作。",
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
