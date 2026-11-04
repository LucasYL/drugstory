"""决策队列：需要玩家决定的事都放在 state.pending 里，问完才能继续推进。种类见 design/tech.md 第 6 节。"""

from __future__ import annotations

from typing import Any

from drugstory.engine.state import Decision, GameState

MILESTONE = "milestone"  # 研发到了攻关节点：派哪个团队
RD_END = "rd_end"  # 研发期结束：多磨 4 周 / 进入临床 / 终止
PHASE_RESULT = "phase_result"  # 某一期出结果：过关就问继续还是终止，没过关只是告知
APPROVAL = "approval"  # 审评通过：给药起名
CANDIDATES = "candidates"  # 招聘出了候选人
CASH_NEGATIVE = "cash_negative"  # 现金第一次在月底变成负数
YEAR_END = "year_end"  # 年报
GAME_END = "game_end"  # 第 20 年结算

KINDS = (MILESTONE, RD_END, PHASE_RESULT, APPROVAL, CANDIDATES, CASH_NEGATIVE, YEAR_END, GAME_END)


def add(state: GameState, kind: str, project_id: int = 0, **data: Any) -> Decision:
    assert kind in KINDS, kind
    decision = Decision(id=state.new_id(), kind=kind, project_id=project_id, data=data)
    state.pending.append(decision)
    return decision


def remove(state: GameState, decision: Decision) -> None:
    state.pending.remove(decision)


def for_project(state: GameState, project_id: int) -> list[Decision]:
    return [d for d in state.pending if d.project_id == project_id]
