"""v0.12：证据和结果先说一个词，数字放进悬停提示；评级前两年先不给字母，并告诉玩家怎么涨分。"""

import pytest

from drugstory.career import bot, rating
from drugstory.career.model import dumps, new_game
from drugstory.career.view import gates_for, result_word, snapshot, verdict


@pytest.mark.parametrize(
    "low,high,mean,gate,word",
    [
        (700, 900, 800, 620, "很可能过"),
        (650, 900, 780, 620, "大概率过"),
        (600, 700, 650, 620, "可能过"),
        (560, 680, 610, 620, "悬"),
        (400, 600, 500, 620, "很难过"),
        (400, 600, 500, None, "后面不考"),
    ],
)
def test_verdict_words(low, high, mean, gate, word):
    assert verdict(low, high, mean, gate) == word


@pytest.mark.parametrize(
    "value,limit,word",
    [
        (900, 650, "远超门槛"),
        (720, 650, "稳稳过线"),
        (660, 650, "刚好过线"),
        (610, 650, "差一点"),
        (500, 650, "差得远"),
    ],
)
def test_result_words(value, limit, word):
    assert result_word(value, limit) == word


def test_gate_is_current_stage_or_the_highest_later_one():
    s = bot.play(3, weeks=310)
    p = next(
        p for p in s["projects"] if p["status"] not in ("approved", "failed", "terminated") and p["chosen"] is not None
    )
    gates = gates_for(p)
    assert gates, "在研项目至少有一项指标有门槛"
    for gate, stage in gates.values():
        assert gate > 0 and stage


def test_snapshot_evidence_has_words():
    s = bot.play(3, weeks=310)
    v = snapshot(s)
    rows = [e for p in v["projects"] for c in p["candidates"] for e in c["evidence"]]
    assert rows and all(e["verdict"] for e in rows)
    results = [r for p in v["projects"] for r in p["results"]]
    assert results and all(set(r["words"]) == set(r["values"]) for r in results)


def test_rating_is_early_for_two_years_and_levers_are_read_only():
    s = new_game(1)
    assert rating.view(s)["early"]
    s = bot.play(3, weeks=310)
    before = dumps(s)
    v = rating.view(s)
    assert not v["early"] and v["levers"] and all(x["text"] for x in v["levers"])
    assert v["gap"] is None or v["gap"]["points"] > 0
    assert dumps(s) == before
