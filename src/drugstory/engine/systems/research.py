"""研发：每周点数、攻关节点、隐患（design/game-design.md 第 7 节）。"""

from __future__ import annotations

import math
import random

from drugstory.content import ATTR_OF_STAT, HAZARD_STATS, STATS, Content, Modality, Target
from drugstory.engine import decisions, rng
from drugstory.engine.book import round_half_up, say, spend
from drugstory.engine.rules.combo import compat, multiplier
from drugstory.engine.rules.texts import project_label, spaced
from drugstory.engine.state import IDLE, RD_REVIEW, RESEARCH, GameState, Hazard, NotebookEntry, Project, Team
from drugstory.engine.systems.teams import gain_exp, weekly_output


def rd_weeks(target: Target, modality: Modality) -> int:
    return max(1, round_half_up(modality.base_weeks * target.difficulty))


def extensions_used(project: Project, content: Content) -> int:
    base = rd_weeks(content.targets[project.target], content.modalities[project.modality])
    return max(0, (project.rd_weeks - base) // content.balance.research.extension_weeks)


def quality_gain(current: float, effort: float, target: Target, content: Content) -> float:
    """基础研发按原速度积累，优秀后逐渐放缓；投入顺序不影响结果，旧属性不下调。"""
    base = content.balance.scoring.base_standard * target.difficulty
    knee = base * content.balance.research.quality_knee
    ceiling = base * content.balance.research.quality_ceiling
    linear = min(max(0.0, effort), max(0.0, knee - current))
    remaining = max(0.0, effort - linear)
    room = max(0.0, ceiling - current - linear)
    return linear + room * -math.expm1(-remaining / (ceiling - knee))


def proficiency_multiplier(state: GameState, project: Project, content: Content) -> float:
    levels = state.modality_proficiency.get(project.modality, 0) + state.target_proficiency.get(project.target, 0)
    return 1 + content.balance.research.proficiency_bonus * levels


def point_multiplier(state: GameState, project: Project, content: Content) -> float:
    """组合系数 × 熟练度。"""
    tier, _ = compat(content.targets[project.target], content.modalities[project.modality], content)
    return multiplier(tier, content) * proficiency_multiplier(state, project, content)


def project_teams(state: GameState, project: Project) -> list[Team]:
    return [state.team(i) for i in project.team_ids]


def milestone_week(project: Project, index: int, content: Content) -> int:
    return math.ceil(content.balance.research.milestones[index] * project.rd_weeks)


def best_team(state: GameState, project: Project, stat: str, content: Content) -> Team | None:
    """项目上这一项产出最高的团队；一样高时取编号小的。"""
    teams = project_teams(state, project)
    if not teams:
        return None
    return max(teams, key=lambda t: (weekly_output(t, stat, content), -t.id))


def milestone_bonus(state: GameState, project: Project, team: Team, stat: str, content: Content) -> float:
    r = content.balance.research
    effort = weekly_output(team, stat, content) * point_multiplier(state, project, content) * r.milestone_multiplier
    return quality_gain(project.stats[stat], effort, content.targets[project.target], content)


def step(state: GameState, content: Content) -> None:
    r = content.balance.research
    random_ = rng.stream(state, "research")
    for project in state.projects:
        if project.stage != RESEARCH or decisions.for_project(state, project.id):
            continue
        teams = project_teams(state, project)
        if not teams:
            continue  # 没有团队：研发暂停，也不花钱
        target = content.targets[project.target]
        modality = content.modalities[project.modality]
        mult = point_multiplier(state, project, content)
        for team in teams:
            for stat in STATS:
                noise = random_.uniform(1 - r.noise, 1 + r.noise)
                effort = weekly_output(team, stat, content) * mult * noise
                project.stats[stat] += quality_gain(project.stats[stat], effort, target, content)
            state.data += r.data_per_team_week
            gain_exp(state, team, content)
        project.spent += spend(state, modality.weekly_cost, "research")
        project.rd_done += 1
        _spawn_hazard(state, project, target, modality, random_, content)
        _clear_hazards(state, project, teams, random_, content)

        if project.milestones_done < len(r.milestones):
            if project.rd_done >= milestone_week(project, project.milestones_done, content):
                stat = STATS[project.milestones_done]
                decisions.add(state, decisions.MILESTONE, project.id, index=project.milestones_done, stat=stat)
        elif project.rd_done >= project.rd_weeks:
            project.stage = RD_REVIEW
            decisions.add(state, decisions.RD_END, project.id)
            say(state, f"{project_label(project, content)} 研发期结束")


def _spawn_hazard(
    state: GameState, project: Project, target: Target, modality: Modality, random_: random.Random, content: Content
) -> None:
    r = content.balance.research
    if random_.random() >= r.hazard_rate[modality.risk] * target.difficulty:
        return
    stats = list(r.hazard_stat_weights.keys())
    stat = random_.choices(stats, weights=[r.hazard_stat_weights[s] for s in stats])[0]
    severity = 2 if random_.random() < r.hazard_severity2_chance else 1
    hazards = content.texts.hazards
    special = hazards.modality.get(modality.key)
    pool = list(hazards.general[stat]) + (list(special.get(stat, [])) if special else [])
    text = random_.choice(pool)
    project.hazards.append(Hazard(id=state.new_id(), stat=stat, severity=severity, text=text))
    name = content.texts.names.stats[stat]
    say(state, f"{project_label(project, content)} 冒出隐患「{text}」（{name}，严重度 {severity}）")


def _clear_hazards(
    state: GameState, project: Project, teams: list[Team], random_: random.Random, content: Content
) -> None:
    divisor = content.balance.research.hazard_clear_divisor
    for stat in HAZARD_STATS:
        open_hazards = [h for h in project.hazards if h.stat == stat]
        if not open_hazards:
            continue
        attr = ATTR_OF_STAT[stat]
        best = max(teams, key=lambda t: (t.lead.attr(attr), -t.id))
        if random_.random() < best.lead.attr(attr) / divisor:
            hazard = open_hazards[0]
            project.hazards.remove(hazard)
            say(state, f"{best.lead.name}的团队清掉了{spaced(project_label(project, content))}的隐患「{hazard.text}」")


def apply_milestone(state: GameState, project: Project, team: Team, content: Content) -> float:
    stat = STATS[project.milestones_done]
    bonus = milestone_bonus(state, project, team, stat, content)
    project.stats[stat] += bonus
    project.milestones_done += 1
    names = content.texts.names
    say(state, f"{team.lead.name}带队完成{names.milestones[stat]}：{names.stats[stat]} +{bonus:.0f}")
    return bonus


def extend(state: GameState, project: Project, content: Content) -> None:
    weeks = content.balance.research.extension_weeks
    project.rd_weeks += weeks
    project.stage = RESEARCH
    say(state, f"{project_label(project, content)} 多磨 {weeks} 周")


def release_teams(state: GameState, project: Project) -> None:
    for team in project_teams(state, project):
        team.task, team.task_id = IDLE, 0
    project.team_ids = []


def record_in_notebook(state: GameState, project: Project, content: Content) -> NotebookEntry:
    tier, reason = compat(content.targets[project.target], content.modalities[project.modality], content)
    key = f"{project.target}|{project.modality}"
    entry = state.notebook.get(key)
    if entry is None:
        entry = NotebookEntry(tier=tier, reason=reason)
        state.notebook[key] = entry
        tier_name = content.texts.names.tiers[str(tier)]
        say(
            state,
            f"笔记本记下：{content.targets[project.target].name} × {content.modalities[project.modality].name}"
            f"——{tier_name}（{reason}）",
        )
    entry.times += 1
    return entry
