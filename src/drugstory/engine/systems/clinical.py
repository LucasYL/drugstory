"""临床各期与上市审评：按周付费、打分、过关判定、隐患爆雷（design/game-design.md 第 8 节）。"""

from __future__ import annotations

from drugstory.content import Content
from drugstory.engine import decisions, rng
from drugstory.engine.book import round_half_up, say, spend
from drugstory.engine.rules.naming import suggest_name
from drugstory.engine.rules.scoring import composite, passed, project_scores, score_noise, strategy_for
from drugstory.engine.rules.texts import hazard_text, phase_text, project_label, spaced
from drugstory.engine.state import CLINICAL, FAILED, NAMING, PHASE_REVIEW, QUEUED, GameState, PhaseResult, Project
from drugstory.engine.systems.progression import add_proficiency


def prior_approvals(state: GameState, target: str) -> int:
    """这个靶点上已经批下来的药有几个（包括已经退市的）。"""
    return sum(d.target == target for d in state.drugs)


def unresolved_hazards(project: Project):
    """已揭晓的隐患仍留在历史结果中，不再当作未来风险（兼容旧存档）。"""
    completed = {r.phase for r in project.results}
    return [h for h in project.hazards if h.phase not in completed]


def operations(state: GameState, content: Content) -> dict:
    capacity = content.facility(state.facility).clinical_slots
    used = sum(p.clinical_mode == "internal" and p.stage in (CLINICAL, PHASE_REVIEW) for p in state.projects)
    queue = sorted((p for p in state.projects if p.stage == QUEUED), key=lambda p: (p.queued_week, p.id))
    return {"capacity": capacity, "used": used, "available": max(0, capacity - used),
            "queue": [p.id for p in queue],
            "contract_multiplier": content.balance.clinical_operations.contract_multiplier}


def promote_queue(state: GameState, content: Content) -> None:
    op = operations(state, content)
    for pid in op["queue"][:op["available"]]:
        start_phase(state, state.project(pid), content.phase_keys[0], content)


def phase_plan(project: Project, phase_key: str, content: Content) -> tuple[int, float]:
    """这一期要多少周、一共花多少钱。"""
    phase = content.phase(phase_key)
    target = content.targets[project.target]
    modality = content.modalities[project.modality]
    strategy = strategy_for(project, phase_key, content)
    weeks = max(2, round_half_up(phase.weeks * target.trial_time * strategy.weeks))
    mult = content.balance.clinical_operations.contract_multiplier if project.clinical_mode == "contract" else 1
    return weeks, phase.cost * target.trial_cost * modality.trial_cost * mult * strategy.cost


def assign_hazards(state: GameState, project: Project, content: Content) -> None:
    """进入临床时，把剩下的隐患分配到各期（8.3 节）。"""
    random_ = rng.stream(state, "clinical")
    for hazard in project.hazards:
        weights = content.balance.hazard_phases[hazard.stat]
        keys = list(weights.keys())
        hazard.phase = random_.choices(keys, weights=[weights[k] for k in keys])[0]


def start_phase(state: GameState, project: Project, phase_key: str, content: Content) -> None:
    weeks, cost = phase_plan(project, phase_key, content)
    project.stage = CLINICAL
    project.phase = phase_key
    project.phase_weeks = weeks
    project.phase_weeks_left = weeks
    project.phase_weekly_cost = cost / weeks
    phase_name = spaced(content.phase(phase_key).name)
    say(state, f"{project_label(project, content)} 进入{phase_name}：{weeks} 周，共 ¥{cost:,.0f} 万")


def step(state: GameState, content: Content) -> None:
    promote_queue(state, content)
    for project in [p for p in state.projects if p.stage == CLINICAL]:
        project.spent += spend(state, project.phase_weekly_cost, "clinical")
        project.phase_weeks_left -= 1
        if project.phase_weeks_left <= 0:
            _finish_phase(state, project, content)
    promote_queue(state, content)


def evaluate_phase(state: GameState, project: Project, phase_key: str, content: Content,
                   stream: str = "clinical") -> PhaseResult:
    phase = content.phase(phase_key)
    random_ = rng.stream(state, stream)
    noise = score_noise(project, phase_key, content)
    scores = project_scores(project, phase_key, state.week, content,
                            {stat: random_.randint(-noise, noise) for stat in phase.experts})
    hazard_lines = []
    for hazard in project.hazards:
        if hazard.phase == phase_key:
            scores[hazard.stat] = max(content.balance.scoring.min_score, scores[hazard.stat] - hazard.severity)
            hazard_lines.append(hazard_text(content, phase.name, hazard.text, hazard.stat, hazard.severity))
    ok = passed(phase_key, scores, content)
    text = phase_text(content, content.targets[project.target], content.modalities[project.modality],
                      phase_key, scores, ok)
    return PhaseResult(phase=phase_key, scores=scores, passed=ok, text=text, hazard_texts=hazard_lines)


def _finish_phase(state: GameState, project: Project, content: Content) -> None:
    phase = content.phase(project.phase)
    target, modality = content.targets[project.target], content.modalities[project.modality]
    result = evaluate_phase(state, project, phase.key, content)
    state.data += phase.data
    project.results.append(result)
    ok = result.passed
    say(state, f"{project_label(project, content)} {phase.name}{'过关' if ok else '失败'}：{result.text}")

    keys = content.phase_keys
    if not ok:
        project.stage = FAILED
        project.ended_week = state.week
        r = content.balance.reputation
        state.reputation = max(0.0, state.reputation - r.failure_penalty)
        state.current_year.failures += 1
        add_proficiency(state, project, content)
        decisions.add(state, decisions.PHASE_RESULT, project.id, phase=phase.key, passed=False)
    elif phase.key == keys[-1]:
        project.composite = composite(project.results, content)
        project.stage = NAMING
        taken = {d.name for d in state.drugs}
        name = suggest_name(rng.stream(state, "naming"), target, modality, content, taken)
        decisions.add(state, decisions.APPROVAL, project.id, suggested=name, composite=project.composite)
    else:
        project.stage = PHASE_REVIEW
        next_phase = keys[keys.index(phase.key) + 1]
        decisions.add(state, decisions.PHASE_RESULT, project.id, phase=phase.key, passed=True, next=next_phase)
