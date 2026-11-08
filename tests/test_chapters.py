"""v0.11 章节、疾病地图与患者组织委托。"""

from drugstory.career import chapters
from drugstory.career import engine as g
from drugstory.career.content import CATALOG
from drugstory.career.model import dumps, new_game
from drugstory.career.view import snapshot
from tests.test_career import complete_phase, ready


def launched_generic():
    s = ready("generic", strong=True)
    for index in range(4):
        s = complete_phase(s)
        if index < 3:
            s = g.execute(s, "continue_project", {"project": "1"})
    return s


def test_first_chapter_completes_when_the_first_generic_launches():
    s = launched_generic()
    view = snapshot(s)["chapters"]
    assert view["current"]["index"] == 1 and view["current"]["goal"].startswith("第一款药上市")
    cash = s["cash"]
    s = g.execute(s, "launch", {"project": "1"})
    assert s["chapter"] == 1 and s["chapter_log"][0]["stars"] >= 1
    assert s["income"]["chapters"] == 300 and s["cash"] > cash - 200
    assert any(e["type"] == "chapter_completed" for e in s["events"])
    assert snapshot(s)["chapters"]["current"]["name"] == "第一位专家"
    before = dumps(s)
    chapters.update(s)
    assert dumps(s) == before, "同一章只结算一次"


def test_disease_map_lights_up_with_a_patient_story():
    s = g.execute(launched_generic(), "launch", {"project": "1"})
    rows = snapshot(s)["chapters"]["map"]
    cured = [r for r in rows if r["cured"]]
    assert len(cured) == 1 and cured[0]["story"]
    assert any(r["tier"] == "final" for r in rows) and any(r["tier"] == "hard" for r in rows)


def test_bounties_arrive_every_two_years_and_pay_when_the_disease_gets_a_drug():
    s = new_game(3)
    s["cash"] = 1e6
    while s["week"] < 96:
        s = g.execute(s, "advance", {"weeks": 48})
    assert len(s["bounties"]) == 1
    b = s["bounties"][0]
    assert b["status"] == "open" and b["deadline"] > s["week"] and b["reward"] > 0
    assert snapshot(s)["chapters"]["bounties"][0]["disease"] == b["disease"]
    # 边界单测：直接放一款对应疾病的产品，验证结算
    key = next(k for k, c in CATALOG.items() if c.get("indication") == b["disease"])
    s["products"].append({"catalog": key, "kind": CATALOG[key]["kind"], "partner": False, "name": "x", "patients": 0})
    chapters.settle_bounties(s)
    assert s["bounties"][0]["status"] == "done" and s["income"]["bounties"] == b["reward"]
    assert s["bounties_done"] == [b["id"]]
