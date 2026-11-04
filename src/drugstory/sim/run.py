"""批量模拟：每种策略用一批种子跑满 20 年，看平衡指标（design/tech.md 第 9 节）。"""

from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from drugstory.content import Content, default_content
from drugstory.engine.calendar import year_of
from drugstory.engine.game import new_game
from drugstory.engine.loop import advance
from drugstory.engine.state import APPROVED, ENDED_STAGES, GameState
from drugstory.engine.systems.progression import final_score, total_profit
from drugstory.sim.bots import STRATEGIES, Bot


def play(
    seed: int, bot: Bot, content: Content, years: int | None = None, on_week: Callable[[GameState], None] | None = None
) -> GameState:
    """让 bot 从开局玩到第 years 年结束（默认 20 年），或者破产为止。"""
    years = years or content.balance.time.career_years
    state = new_game(seed, content)
    end = years * content.balance.time.weeks_per_year
    while state.week < end and not state.game_over:
        bot.manage(state, content)
        advance(state, content, 1)
        while state.pending and not state.game_over:
            bot.resolve(state, content, state.pending[0])
        if on_week is not None:
            on_week(state)
    return state


@dataclass
class GameResult:
    strategy: str
    seed: int
    bankrupt: bool
    final_year: int
    first_approval_year: int | None
    approvals: int
    hall_of_fame: int
    achievements: int
    score: int
    profit: int
    cash_y15: int | None
    cash_end: int
    composite_early: float | None  # 第 1–5 年获批药的平均综合分
    composite_late: float | None  # 第 15–20 年获批药的平均综合分
    max_score_late: float  # 第 15 年以后临床分数里满分 10 分的比例
    combos: dict[str, list[float]] = field(default_factory=dict)  # 组合 → 每个项目的利润


def summarize(strategy: str, seed: int, state: GameState, cash_y15: int | None, content: Content) -> GameResult:
    drugs_by_project = {d.project_id: d for d in state.drugs}
    approved_years = [year_of(d.launched_week, content) for d in state.drugs]
    early = [d.composite for d in state.drugs if year_of(d.launched_week, content) <= 5]
    late = [d.composite for d in state.drugs if year_of(d.launched_week, content) >= 15]
    late_scores = [
        s
        for p in state.projects
        if p.ended_week >= 15 * content.balance.time.weeks_per_year or p.stage not in ENDED_STAGES
        for r in p.results
        for s in r.scores.values()
    ]
    combos: dict[str, list[float]] = defaultdict(list)
    for p in state.projects:
        if p.stage not in ENDED_STAGES or p.stage == "cancelled":
            continue
        drug = drugs_by_project.get(p.id)
        profit = (drug.revenue_total * drug.margin if drug else 0) - p.spent
        combos[f"{p.target}|{p.modality}"].append(profit)
    score = final_score(state, content)
    return GameResult(
        strategy=strategy,
        seed=seed,
        bankrupt=state.game_over,
        final_year=year_of(max(state.week - 1, 0), content),
        first_approval_year=min(approved_years) if approved_years else None,
        approvals=sum(p.stage == APPROVED for p in state.projects),
        hall_of_fame=sum(d.hall_of_fame for d in state.drugs),
        achievements=len(state.achievements),
        score=score["score"],
        profit=total_profit(state),
        cash_y15=cash_y15,
        cash_end=state.cash,
        composite_early=statistics.mean(early) if early else None,
        composite_late=statistics.mean(late) if late else None,
        max_score_late=(sum(s == 10 for s in late_scores) / len(late_scores)) if late_scores else 0.0,
        combos=dict(combos),
    )


def run_one(strategy: str, seed: int, content: Content, years: int | None = None) -> GameResult:
    bot = STRATEGIES[strategy]()
    marks: dict[str, int] = {}
    y15 = 15 * content.balance.time.weeks_per_year

    def on_week(state: GameState) -> None:
        if state.week == y15:
            marks["cash_y15"] = state.cash

    state = play(seed, bot, content, years, on_week)
    return summarize(strategy, seed, state, marks.get("cash_y15"), content)


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def report(results: list[GameResult]) -> str:
    lines = []
    by_strategy: dict[str, list[GameResult]] = defaultdict(list)
    for r in results:
        by_strategy[r.strategy].append(r)
    header = (
        f"{'策略':<6}{'局数':>5}{'破产率':>8}{'首批年份(中位)':>14}{'获批':>7}{'名人堂':>7}"
        f"{'第15年现金':>12}{'早期综合分':>10}{'后期综合分':>10}{'后期满分率':>10}{'总分':>8}"
    )
    lines.append(header)
    for strategy, rs in by_strategy.items():
        firsts = [r.first_approval_year for r in rs if r.first_approval_year is not None]
        early = [r.composite_early for r in rs if r.composite_early is not None]
        late = [r.composite_late for r in rs if r.composite_late is not None]
        cash15 = [r.cash_y15 for r in rs if r.cash_y15 is not None]
        lines.append(
            f"{STRATEGIES[strategy].name:<6}{len(rs):>5}"
            f"{sum(r.bankrupt for r in rs) / len(rs):>8.0%}"
            f"{_fmt(_median(firsts)):>14}"
            f"{statistics.mean(r.approvals for r in rs):>7.1f}"
            f"{statistics.mean(r.hall_of_fame for r in rs):>7.1f}"
            f"{_fmt(_median(cash15), 0):>12}"
            f"{_fmt(_median(early)):>10}{_fmt(_median(late)):>10}"
            f"{statistics.mean(r.max_score_late for r in rs):>10.0%}"
            f"{statistics.mean(r.score for r in rs):>8.0f}"
        )
        no_first = sum(r.first_approval_year is None for r in rs)
        if no_first:
            lines.append(f"      {no_first} 局一个药都没批下来")

    combos: dict[str, list[float]] = defaultdict(list)
    for r in results:
        for key, profits in r.combos.items():
            combos[key].extend(profits)
    ranked = sorted(((statistics.mean(v), len(v), k) for k, v in combos.items() if len(v) >= 5), reverse=True)
    if ranked:
        lines.append("")
        lines.append("每个项目平均利润最高的组合（至少做过 5 次）：")
        for mean, count, key in ranked[:8]:
            lines.append(f"  {key:<28}{mean:>10,.0f} 万  （{count} 次）")
        if len(ranked) >= 5 and ranked[4][0] > 0:
            lines.append(f"  第 1 名是第 5 名的 {ranked[0][0] / ranked[4][0]:.2f} 倍")
    return "\n".join(lines)


def _fmt(value: float | None, digits: int = 1) -> str:
    return "—" if value is None else f"{value:,.{digits}f}"


def write_csv(results: list[GameResult], path: Path) -> None:
    rows = [{k: v for k, v in asdict(r).items() if k != "combos"} for r in results]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(
    runs: int, strategies: list[str], content: Content | None = None, years: int | None = None, first_seed: int = 1
) -> list[GameResult]:
    content = content or default_content()
    return [run_one(s, seed, content, years) for s in strategies for seed in range(first_seed, first_seed + runs)]
