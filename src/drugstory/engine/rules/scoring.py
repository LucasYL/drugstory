"""打分：标准、专家分、过关判定、综合分（design/game-design.md 8.2、8.5 节）。"""

from __future__ import annotations

from drugstory.content import Content, Target
from drugstory.engine.book import round_half_up
from drugstory.engine.calendar import year_of
from drugstory.engine.state import PhaseResult, Project


def year_factor(week: int, content: Content) -> float:
    return (1 + content.balance.scoring.yearly_growth) ** (year_of(week, content) - 1)


def standard(target: Target, phase_key: str, stat: str, week: int, content: Content, prior_approvals: int = 0) -> float:
    """标准 = 基础标准 × 难度 × 阶段系数。默认不随年份或历史获批数上涨。

    年份和标准疗法系数仍可由模拟实验覆盖；正常游戏中这两个增长参数均为零。
    """
    s = content.balance.scoring
    phase = content.phase(phase_key)
    value = s.base_standard * target.difficulty * phase.standard[stat] * year_factor(week, content)
    if stat == "efficacy" and phase.get("vs_standard_of_care", False):
        value *= 1 + s.standard_of_care_step * prior_approvals
    return value


def expert_score(value: float, standard_value: float, noise: int, content: Content) -> int:
    s = content.balance.scoring
    raw = round_half_up(s.score_scale * value / standard_value) + noise
    return max(s.min_score, min(s.max_score, raw))


def passed(phase_key: str, scores: dict[str, int], content: Content) -> bool:
    phase = content.phase(phase_key)
    single = all(scores[stat] >= line for stat, line in phase.pass_.items())
    return single and sum(scores.values()) >= phase.pass_total


def expected_scores(
    stats: dict[str, float], target: Target, phase_key: str, week: int, content: Content, prior_approvals: int = 0
) -> dict[str, int]:
    """不加随机波动、不算隐患的预估分，给界面和 bot 参考。"""
    return {
        stat: expert_score(stats[stat], standard(target, phase_key, stat, week, content, prior_approvals), 0, content)
        for stat in content.phase(phase_key).experts
    }


def composite(results: list[PhaseResult], content: Content) -> float:
    """综合分 = 各阶段专家平均分的加权平均 × 10，满分 100。"""
    total = weights = 0.0
    for r in results:
        w = content.phase(r.phase).weight
        total += w * sum(r.scores.values()) / len(r.scores)
        weights += w
    return round(total / weights * 10, 1) if weights else 0.0


def strategy_for(project: Project, phase_key: str, content: Content):
    key = project.clinical_strategy if project.strategy_chosen and phase_key != "I" else "standard"
    return content.balance.clinical_strategies[key]


def score_noise(project: Project, phase_key: str, content: Content) -> int:
    return min(content.balance.scoring.noise, strategy_for(project, phase_key, content).noise)


def project_scores(project: Project, phase_key: str, week: int, content: Content,
                   noises: dict[str, int] | None = None) -> dict[str, int]:
    strategy = strategy_for(project, phase_key, content)
    target = content.targets[project.target]
    return {
        stat: expert_score(project.stats[stat], standard(target, phase_key, stat, week, content),
                           (noises or {}).get(stat, 0) + (strategy.efficacy_bonus if stat == "efficacy" else 0),
                           content)
        for stat in content.phase(phase_key).experts
    }
