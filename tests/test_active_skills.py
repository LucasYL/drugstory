"""v0.13 主动技能：九种原语、解锁、冷却、只读的可用列表、重放一致。"""

import json

import pytest

from drugstory.career import engine as g
from drugstory.career import science as sc
from drugstory.career.model import dumps, make_hero, new_game
from drugstory.career.view import snapshot


def add(s, key, **extra):
    h = {**make_hero(key), "joined": 0, **extra}
    s["heroes"].append(h)
    return h


def hero(s, key):
    return next(h for h in s["heroes"] if h["id"] == key)


def selecting(seed=1):
    s = new_game(seed)
    s = g.execute(s, "start_project", {"catalog": "g_pressure", "heroes": ["beaker", "pill"]})
    s = g.execute(s, "next_event", {"batches": 0})
    assert s["projects"][0]["status"] == "selecting"
    return s


def ready(seed=1):
    s = selecting(seed)
    return g.execute(s, "choose_candidate", {"project": s["projects"][0]["id"], "candidate": 0})


def use(s, character, **args):
    return g.execute(s, "use_skill", {"character": character, **args})


def test_juniors_unlock_at_elite_and_cooldown_applies():
    s = ready()
    pid = s["projects"][0]["id"]
    s = g.execute(s, "run_phase", {"project": pid, "heroes": ["beaker", "pill"]})
    with pytest.raises(ValueError, match="晋升精英后解锁"):
        use(s, "beaker", project=pid)
    s = json.loads(dumps(s))
    hero(s, "beaker")["rank"] = 2
    left = s["projects"][0]["left"]
    s = use(s, "beaker", project=pid)
    assert s["projects"][0]["left"] == left - 3
    assert hero(s, "beaker")["skill_ready"] == s["week"] + 96
    with pytest.raises(ValueError, match="还要等"):
        use(s, "beaker", project=pid)


def test_service_is_delivered_now():
    s = new_game(1)
    hero(s, "pill")["rank"] = 2
    s = g.execute(s, "take_service", {"order": "0-0", "character": "pill"})
    cash = s["cash"]
    s = use(s, "pill")
    assert not s["jobs"] and s["cash"] > cash and s["services_done"] == 1


def test_extra_candidate_is_deterministic():
    s = selecting()
    add(s, "sprout", rank=2)
    a = use(s, "sprout", project=s["projects"][0]["id"])
    b = use(s, "sprout", project=s["projects"][0]["id"])
    assert len(a["projects"][0]["candidates"]) == 4
    assert a["projects"][0]["candidates"][3] == b["projects"][0]["candidates"][3]


def test_reveal_narrows_the_range():
    s = ready()
    add(s, "bubble", rank=2)
    p = s["projects"][0]
    before = p["candidates"][0]["belief"]["safety"]["variance"]
    s = use(s, "bubble", project=p["id"])
    assert s["projects"][0]["candidates"][0]["belief"]["safety"]["variance"] < before


def test_improve_once_per_project_before_clinic():
    s = ready()
    add(s, "catalyst")
    pid = s["projects"][0]["id"]
    q = s["projects"][0]["candidates"][0]["truth"]["quality"]
    s = use(s, "catalyst", project=pid)
    assert s["projects"][0]["candidates"][0]["truth"]["quality"] == pytest.approx(min(98, q + 4))
    hero(s, "catalyst")["skill_ready"] = 0
    with pytest.raises(ValueError, match="用过一次"):
        use(s, "catalyst", project=pid)


def test_limit_applies_to_the_next_stage_once():
    s = ready()
    add(s, "shield")
    p = s["projects"][0]
    p["index"] = 1  # 质量与稳定性阶段：考安全
    s = use(s, "shield", project=p["id"])
    p = s["projects"][0]
    assert sc.plan_phase(s, p, ["pill"], key="quality")["adjust"]["safety"] == -3
    s = g.execute(s, "run_phase", {"project": p["id"], "heroes": ["pill", "beaker"]})
    p = s["projects"][0]
    assert sc.limits(p, "quality")["safety"] == pytest.approx(58 - 3)
    assert "quality" not in p.get("adjust_next", {}), "用过一次就清掉"


def test_rescue_only_close_recent_clinical_failures():
    s = ready()
    add(s, "curve")
    p = s["projects"][0]
    p.update(status="failed", index=2, ended=s["week"])
    p["results"].append(
        {
            "key": "be",
            "week": s["week"],
            "passed": False,
            "values": {"exposure": 60},
            "limits": {"exposure": 64},
            "failures": ["exposure"],
        }
    )
    s = use(s, "curve", project=p["id"])
    p = s["projects"][0]
    assert p["status"] == "problem" and p["ended"] is None and p["reanalyzed"]
    s2 = json.loads(dumps(s))
    s2["projects"][0].update(status="failed", reanalyzed=False)
    s2["projects"][0]["results"][-1]["values"]["exposure"] = 50
    hero(s2, "curve")["skill_ready"] = 0
    with pytest.raises(ValueError, match="差得太多"):
        use(s2, "curve", project=p["id"])


def test_marker_and_product_and_notebook_and_xp():
    s = new_game(1)
    s = g.execute(s, "start_project", {"catalog": "n_lung", "heroes": ["beaker"]})
    s = g.execute(s, "next_event", {"batches": 0})
    s = g.execute(s, "choose_candidate", {"project": s["projects"][0]["id"], "candidate": 0})
    add(s, "bridge")
    s = use(s, "bridge", project=s["projects"][0]["id"])
    assert s["projects"][0]["candidates"][0]["marker"]["observations"] == 1

    add(s, "scout")
    s = use(s, "scout", target="pd1")
    assert sum(1 for k in s["notebook"] if k.startswith("n_pd1")) >= 11

    star = add(s, "star")
    pupil = add(s, "sprout")
    xp = pupil["xp"]
    s = use(s, "star")
    assert hero(s, "sprout")["xp"] == xp + 20 and star["profession"] == "bio"

    add(s, "forge")
    s["products"].append(
        {
            "id": "drug-x",
            "name": "测试药",
            "catalog": "g_pressure",
            "kind": "generic",
            "market": "pressure",
            "launched": s["week"],
            "partner": False,
            "active": True,
            "peak": 100.0,
            "margin": 0.5,
            "patients": 0,
        }
    )
    s = use(s, "forge", product="drug-x")
    assert s["products"][-1]["peak"] == pytest.approx(110)
    hero(s, "forge")["skill_ready"] = 0
    with pytest.raises(ValueError, match="改过一次"):
        use(s, "forge", product="drug-x")


def test_usable_list_is_read_only_and_replay_matches():
    s = ready()
    hero(s, "beaker")["rank"] = 2
    add(s, "catalyst")
    before = dumps(s)
    v = snapshot(s)
    assert dumps(s) == before
    names = {x["name"] for x in v["projects"][0]["skills"]}
    assert "放大一次" in names
    assert v["heroes"][-1]["active"]["choices"]


def test_skills_are_deterministic():
    """同一状态、同一技能，结果完全一样（技能只用带键随机）。"""
    s = selecting()
    add(s, "sprout", rank=2)
    add(s, "wizard")
    pid = s["projects"][0]["id"]
    a = use(json.loads(dumps(s)), "sprout", project=pid)
    b = use(json.loads(dumps(s)), "sprout", project=pid)
    assert dumps(a) == dumps(b)
