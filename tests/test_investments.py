"""v0.13 花钱的出口：自有产线、患者援助、青年学者计划、临床病房。"""

import json

import pytest

from drugstory.career import bot, economy, guide, investments, rating
from drugstory.career import engine as g
from drugstory.career.model import dumps, make_hero, new_game


@pytest.fixture(scope="module")
def played():
    return dumps(bot.play(2, weeks=400))


def fresh(played, cash=50_000, facility=2):
    s = json.loads(played)
    s["cash"] = cash  # 构造状态：只为覆盖每个出口
    s["facility"] = facility
    return s


def own(s):
    return next(d for d in s["products"] if d["active"] and not d["partner"] and d.get("production") != "self")


def test_line_raises_margin_and_needs_space(played):
    s = fresh(played)
    d = own(s)
    before = economy.base_sales(s, d)
    cost = investments.line_cost(s, d)
    s = g.execute(s, "build_line", {"product": d["id"]})
    d2 = next(x for x in s["products"] if x["id"] == d["id"])
    assert d2["production"] == "self"
    revenue, gross = economy.base_sales(s, d2)
    assert gross / revenue - before[1] / before[0] == pytest.approx(investments.LINE_MARGIN[d["kind"]], abs=0.011)
    assert s["expense"]["lines"] >= cost
    with pytest.raises(ValueError, match="已经是自有产线"):
        g.execute(s, "build_line", {"product": d["id"]})
    small = fresh(played, facility=0)
    with pytest.raises(ValueError, match="没有产线"):
        g.execute(small, "build_line", {"product": own(small)["id"]})


def test_architect_discount_and_extra_margin(played):
    s = fresh(played)
    d = own(s)
    plain_cost = investments.line_cost(s, d)
    s["heroes"].append({**make_hero("architect"), "joined": 0})
    assert investments.line_cost(s, d) == round(plain_cost * 0.7)
    assert investments.line_margin(s, d) == 0, "委托生产的产品不再吃高铁峰的毛利"
    d["production"] = "self"
    assert investments.line_margin(s, d) == pytest.approx(investments.LINE_MARGIN[d["kind"]] + 0.06)


def test_access_program_spends_and_reaches_more_patients(played):
    s = fresh(played)
    d = own(s)
    a = g.execute(json.loads(dumps(s)), "advance", {"weeks": 1})
    s = g.execute(s, "access_program", {"product": d["id"], "on": 1})
    b = g.execute(s, "advance", {"weeks": 1})
    pa = next(x for x in a["products"] if x["id"] == d["id"])
    pb = next(x for x in b["products"] if x["id"] == d["id"])
    gain_a = pa["patients"] - d.get("patients", 0)
    gain_b = pb["patients"] - d.get("patients", 0)
    assert gain_b == pytest.approx(gain_a * 1.6)
    assert b["expense"].get("access", 0) == pytest.approx(pb["last_revenue"] * 0.12)
    assert b["cash"] < a["cash"]
    c = g.execute(b, "access_program", {"product": d["id"], "on": 0})
    assert not next(x for x in c["products"] if x["id"] == d["id"])["access"]


def test_fellowship_adds_legacy_and_xp_from_the_third(played):
    s = fresh(played)
    base = rating.legacy_points(s)
    for _ in range(2):
        s = g.execute(s, "fund_fellowship", {})
    assert rating.legacy_points(s) == base + 16
    s["heroes"].append({**make_hero("sprout"), "joined": 0, "rank": 1})
    xp = {h["id"]: h["xp"] for h in s["heroes"]}
    s = g.execute(s, "fund_fellowship", {})
    junior = min((h for h in s["heroes"] if h["employed"] and h["rank"] == 1), key=lambda h: (xp[h["id"]], h["id"]))
    assert junior["xp"] == xp[junior["id"]] + 10
    for _ in range(2):
        s = g.execute(s, "fund_fellowship", {})
    with pytest.raises(ValueError, match="最多办 5 期"):
        g.execute(s, "fund_fellowship", {})
    with pytest.raises(ValueError, match="联合研发所"):
        g.execute(new_game(1), "fund_fellowship", {})


def test_ward_adds_a_clinical_seat_and_upkeep(played):
    s = fresh(played)
    slots = g.clinical_slots(s)
    s = g.execute(s, "build_ward", {})
    assert g.clinical_slots(s) == slots + 1
    assert investments.upkeep(s) >= investments.WARD_UPKEEP
    s = g.execute(s, "build_ward", {})
    with pytest.raises(ValueError, match="最多建 2 个"):
        g.execute(s, "build_ward", {})


def test_guide_suggests_one_investment_when_rich(played):
    s = fresh(played)
    items = [i for i in guide.suggestions(s, limit=10) if i["kind"] == "invest"]
    assert len(items) == 1 and items[0]["command"] == "build_line" and items[0]["ok"]
    g.execute(s, items[0]["command"], items[0]["args"])
    poor = fresh(played, cash=500)
    assert not [i for i in guide.suggestions(poor, limit=10) if i["kind"] == "invest"]


def test_bot_spends_surplus_but_keeps_reserve(played):
    s = fresh(played, cash=9000)
    s = bot.choose(s)
    assert s["expense"].get("lines", 0) > 0 or s.get("wards") or s.get("fellowships")
    assert s["cash"] >= bot.RESERVE
