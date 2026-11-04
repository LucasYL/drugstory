"""Authored personal projects: work together, make a choice, keep a permanent legacy."""

# Every character has an authored professional question, not a random stat request.
import json

from .content import DATA, PROFESSIONS, ROSTER
from .model import ability, available_money, busy, check, free_team, gain_work, hero, log, spend

STORIES = json.loads((DATA / "stories.json").read_text())
CHOICES = {
    "practice": {
        "name": "完成专业课题",
        "weeks": 8,
        "cost": 100,
        "text": "与指定专业伙伴共同研究，升级本人的招牌能力，并抵一项晋阶履历。",
    }
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
    from .events import emit

    emit(s, "personal_completed", actors=job["heroes"], room="room_academy", data={"name": h["name"]})


def active(s, ids):
    roles = {h["profession"] for h in s["heroes"] if h["id"] in ids and h["employed"]}
    return [
        h
        for h in s["heroes"]
        if h["employed"] and h["id"] in ids and h.get("personal") and STORIES[h["id"]][2] in roles
    ]


assert set(STORIES) == set(ROSTER)
