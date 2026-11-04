"""玩家能做的所有操作。每个操作先校验、再修改状态；不合法就抛 ActionError，信息是给玩家看的。

界面、bot、测试都只通过这里修改游戏状态。每个成功的操作都会记进 state.action_log，用于回放。
参数必须是 JSON 能表示的类型（int、str、list）。
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

from drugstory.content import ATTRS, STATS, Content
from drugstory.engine import decisions
from drugstory.engine.book import can_afford, earn, round_half_up, say, spend
from drugstory.engine.queries import modality_unlock_problems, next_facility, target_unlock_problems
from drugstory.engine.rules.combo import compat
from drugstory.engine.rules.texts import project_label, spaced
from drugstory.engine.state import (
    CANCELLED,
    IDLE,
    LICENSED,
    ON_CONTRACT,
    ON_PROJECT,
    PHASE_REVIEW,
    QUEUED,
    RD_REVIEW,
    RESEARCH,
    TERMINATED,
    ActiveContract,
    Decision,
    GameState,
    LicenseDeal,
    LoggedAction,
    Project,
    Recruitment,
    Team,
)
from drugstory.engine.systems import clinical, licensing, market, research
from drugstory.engine.systems.contracts import duration, reward
from drugstory.engine.systems.progression import add_proficiency, check_achievements
from drugstory.engine.systems.teams import capacity, lead_salary, training_cap, training_cost

MAX_NAME_LENGTH = 40


class ActionError(Exception):
    """操作不合法。"""


ACTIONS: dict[str, Callable[..., Any]] = {}


def action(fn: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(fn)
    def wrapper(state: GameState, content: Content, **kwargs: Any) -> Any:
        if state.game_over:
            raise ActionError("游戏已经结束了")
        result = fn(state, content, **kwargs)
        check_achievements(state, content)
        state.action_log.append(LoggedAction(week=state.week, name=fn.__name__, args=dict(kwargs)))
        return result

    ACTIONS[fn.__name__] = wrapper
    return wrapper


def apply(state: GameState, content: Content, name: str, args: dict[str, Any]) -> Any:
    """按名字执行一个操作（回放用）。"""
    if name not in ACTIONS:
        raise ActionError(f"没有这个操作：{name}")
    return ACTIONS[name](state, content, **args)


# ---------------------------------------------------------------- 小工具


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ActionError(message)


def _pay(state: GameState, amount: float, category: str, what: str) -> int:
    _require(can_afford(state, amount), f"现金不够：{what}要 ¥{round_half_up(amount):,} 万，你只有 ¥{state.cash:,} 万")
    return spend(state, amount, category)


def _team(state: GameState, team_id: int) -> Team:
    try:
        return state.team(team_id)
    except KeyError:
        raise ActionError(f"没有这个团队：{team_id}") from None


def _project(state: GameState, project_id: int) -> Project:
    try:
        return state.project(project_id)
    except KeyError:
        raise ActionError(f"没有这个项目：{project_id}") from None


def _decision(state: GameState, decision_id: int, *kinds: str) -> Decision:
    try:
        decision = state.decision(decision_id)
    except KeyError:
        raise ActionError(f"没有这件待决定的事：{decision_id}") from None
    _require(decision.kind in kinds, f"这件事不能这样处理（{decision.kind}）")
    return decision


def _check_team_ids(state: GameState, team_ids: list[int], allowed_project: int = 0) -> list[Team]:
    _require(len(set(team_ids)) == len(team_ids), "团队不能重复")
    teams = [_team(state, i) for i in team_ids]
    for t in teams:
        busy_elsewhere = not t.idle and not (t.task == ON_PROJECT and t.task_id == allowed_project)
        _require(not busy_elsewhere, f"{t.lead.name}的团队正忙")
    return teams


def _assign(teams: list[Team], project: Project) -> None:
    for t in teams:
        t.task, t.task_id = ON_PROJECT, project.id
    project.team_ids = [t.id for t in teams]


# ---------------------------------------------------------------- 项目


@action
def start_project(state: GameState, content: Content, target: str, modality: str, team_ids: list[int],
                  profile: str = "balanced") -> int:
    _require(profile in content.balance.profiles, "不认识的候选药方案")
    _require(target in state.unlocked_targets, "这个靶点还没解锁")
    _require(modality in state.unlocked_modalities, "这种分子类型还没解锁")
    _require(len(team_ids) > 0, "至少要配一个团队")
    limit = content.balance.team.max_per_project
    _require(len(team_ids) <= limit, f"一个项目最多配 {limit} 个团队")
    teams = _check_team_ids(state, team_ids)
    t, m = content.targets[target], content.modalities[modality]
    tier, reason = compat(t, m, content)
    _require(tier > -2, f"这条路线不可立项：{reason}。请换一个靶点或分子类型")
    project = Project(
        id=state.new_id(),
        target=target,
        modality=modality,
        stage=RESEARCH,
        team_ids=[],
        rd_weeks=research.rd_weeks(t, m),
        base_rd_weeks=research.rd_weeks(t, m),
        extension_count=0,
        profile=profile,
        stats={s: 0.0 for s in STATS},
        started_week=state.week,
    )
    state.projects.append(project)
    _assign(teams, project)
    say(state, f"立项：{project_label(project, content)}，研发期 {project.rd_weeks} 周")
    return project.id


@action
def set_project_teams(state: GameState, content: Content, project_id: int, team_ids: list[int]) -> None:
    project = _project(state, project_id)
    _require(project.stage == RESEARCH, "只有研发中的项目才能调整团队")
    _require(not decisions.for_project(state, project.id), "先处理完这个项目待决定的事")
    limit = content.balance.team.max_per_project
    _require(len(team_ids) <= limit, f"一个项目最多配 {limit} 个团队")
    teams = _check_team_ids(state, team_ids, allowed_project=project.id)
    for t in research.project_teams(state, project):
        t.task, t.task_id = IDLE, 0
    _assign(teams, project)
    say(state, f"{project_label(project, content)} 现在有 {len(teams)} 个团队")


@action
def cancel_project(state: GameState, content: Content, project_id: int) -> None:
    project = _project(state, project_id)
    _require(project.stage in (RESEARCH, QUEUED), "只能取消研发中或临床排队中的项目")
    for d in decisions.for_project(state, project.id):
        decisions.remove(state, d)
    research.release_teams(state, project)
    project.stage = CANCELLED
    project.ended_week = state.week
    say(state, f"{project_label(project, content)} 取消了")


@action
def choose_milestone_team(
    state: GameState, content: Content, decision_id: int, team_id: int, plan: str = "boost"
) -> float:
    decision = _decision(state, decision_id, decisions.MILESTONE)
    project = _project(state, decision.project_id)
    team = _team(state, team_id)
    _require(team.id in project.team_ids, "只能派这个项目上的团队攻关")
    _require(plan in ("boost", "validate", "fast"), "不认识的攻关方案")
    effect = research.milestone_plan(state, project, team, plan, content)
    _require(not effect["problem"], effect["problem"])
    if effect["cost"]:
        _pay(state, effect["cost"], "research", "攻关专项费用")
    project.spent += effect["cost"]
    bonus = research.apply_milestone(state, project, team, content, plan)
    decisions.remove(state, decision)
    return bonus


@action
def resolve_rd_end(state: GameState, content: Content, decision_id: int, choice: str) -> None:
    """研发结束：打磨、专项排险、自营排队、委托临床或终止。"""
    decision = _decision(state, decision_id, decisions.RD_END)
    project = _project(state, decision.project_id)
    _require(project.stage == RD_REVIEW, "这个项目不在研发结束的阶段")
    if choice == "extend":
        _require(bool(project.team_ids), "项目上没有团队，多磨也没用")
        _require(
            research.extensions_used(project, content) < content.balance.research.max_extensions,
            "已达到打磨上限，请根据临床预估进入临床或终止项目",
        )
        research.extend(state, project, content)
    elif choice == "validate":
        _require(project.validation_count < content.balance.research.max_validations, "已达到专项排险次数上限")
        _require(bool(project.team_ids) and bool(project.hazards), "需要有团队和待处理隐患")
        cost = len(project.hazards) * content.balance.research.final_validation_cost
        _pay(state, cost, "research", "专项排险")
        project.spent += cost
        if project.extension_count < 0:
            project.extension_count = research.extensions_used(project, content)
        project.hazards.clear()
        project.validation_count += 1
        project.validation_weeks_left = content.balance.research.validate_weeks
        project.rd_weeks += project.validation_weeks_left
        project.stage = RESEARCH
        say(state, f"{project_label(project, content)} 专项排险：{project.validation_weeks_left} 周，"
            "不加点、不产生新隐患")
    elif choice in ("proceed", "contract"):
        research.record_in_notebook(state, project, content)
        research.release_teams(state, project)
        clinical.assign_hazards(state, project, content)
        if choice == "contract":
            project.clinical_mode = "contract"
            clinical.start_phase(state, project, content.phase_keys[0], content)
        else:
            project.clinical_mode = "internal"
            project.stage = QUEUED
            project.queued_week = state.week
            clinical.promote_queue(state, content)
            if project.stage == QUEUED:
                say(state, f"{project_label(project, content)} 加入临床队列；研发团队已释放，等待不收临床费")
    elif choice == "terminate":
        research.record_in_notebook(state, project, content)
        research.release_teams(state, project)
        project.stage = TERMINATED
        project.ended_week = state.week
        add_proficiency(state, project, content)
        say(state, f"{project_label(project, content)} 研发结束后终止")
    else:
        raise ActionError(f"不认识的选择：{choice}")
    decisions.remove(state, decision)


@action
def outsource_clinical(state: GameState, content: Content, project_id: int) -> None:
    project = _project(state, project_id)
    _require(project.stage == QUEUED, "只有排队中的项目可以转为委托临床")
    project.clinical_mode = "contract"
    clinical.start_phase(state, project, content.phase_keys[0], content)


@action
def resolve_phase(state: GameState, content: Content, decision_id: int, choice: str,
                  strategy: str = "standard") -> None:
    """过关时 choice 是 continue 或 terminate；没过关时只能是 ack。"""
    decision = _decision(state, decision_id, decisions.PHASE_RESULT)
    project = _project(state, decision.project_id)
    if not decision.data["passed"]:
        _require(choice == "ack", "这一期没过关，只能确认")
    elif choice == "continue":
        _require(project.stage == PHASE_REVIEW, "这个项目不在等待决定的阶段")
        _require(strategy in content.balance.clinical_strategies, "不认识的临床策略")
        if project.phase == "I" and not project.strategy_chosen:
            project.clinical_strategy, project.strategy_chosen = strategy, True
            say(state, f"选择临床策略：{content.balance.clinical_strategies[strategy].name}，后续不再切换")
        else:
            _require(strategy in ("standard", project.clinical_strategy), "临床策略已经确定，不能中途切换")
        clinical.start_phase(state, project, decision.data["next"], content)
    elif choice == "terminate":
        _require(project.stage == PHASE_REVIEW, "这个项目不在等待决定的阶段")
        project.stage = TERMINATED
        project.ended_week = state.week
        add_proficiency(state, project, content)
        say(state, f"{project_label(project, content)} 在{spaced(content.phase(project.phase).name)}之后终止")
    else:
        raise ActionError(f"不认识的选择：{choice}")
    decisions.remove(state, decision)
    clinical.promote_queue(state, content)


@action
def license_project(state: GameState, content: Content, decision_id: int, kind: str) -> int:
    decision = _decision(state, decision_id, decisions.RD_END, decisions.PHASE_RESULT)
    p = _project(state, decision.project_id)
    _require(kind in content.balance.license_types, "不认识的授权条款")
    quoted = licensing.offer(state, p, content, kind)
    _require(not quoted["problem"], quoted["problem"])
    if p.stage == RD_REVIEW:
        research.record_in_notebook(state, p, content)
        research.release_teams(state, p)
        clinical.assign_hazards(state, p, content)
        p.clinical_strategy, p.strategy_chosen = "standard", True
        phase = content.phase_keys[0]
    else:
        phase = content.phase_keys[2]
    deal = LicenseDeal(id=state.new_id(), project_id=p.id, partner=quoted["partner"], kind=kind,
                       signed_week=state.week, upfront=quoted["upfront"], milestone=quoted["milestone"],
                       royalty_rate=quoted["royalty_rate"], phase=phase,
                       weeks_left=clinical.phase_plan(p, phase, content)[0])
    state.deals.append(deal)
    p.deal_id, p.stage, p.ended_week = deal.id, LICENSED, state.week
    earn(state, deal.upfront, "license_upfront")
    add_proficiency(state, p, content)
    decisions.remove(state, decision)
    clinical.promote_queue(state, content)
    say(state, f"{project_label(p, content)} 授权给{deal.partner}：首付款 ¥{deal.upfront:,} 万，"
        f"获批里程碑 ¥{deal.milestone:,} 万，销售分成 {deal.royalty_rate:.0%}；后续开发费用与风险由合作方承担")
    return deal.id


@action
def name_drug(state: GameState, content: Content, decision_id: int, name: str) -> int:
    decision = _decision(state, decision_id, decisions.APPROVAL)
    project = _project(state, decision.project_id)
    name = name.strip()
    _require(bool(name), "名字不能是空的")
    _require(len(name) <= MAX_NAME_LENGTH, f"名字最多 {MAX_NAME_LENGTH} 个字")
    _require(name not in {d.name for d in state.drugs}, "已经有药叫这个名字了")
    drug = market.launch(state, project, name, content)
    decisions.remove(state, decision)
    return drug.id


@action
def acknowledge(state: GameState, content: Content, decision_id: int) -> None:
    decision = _decision(state, decision_id, decisions.CASH_NEGATIVE, decisions.YEAR_END, decisions.GAME_END)
    decisions.remove(state, decision)


# ---------------------------------------------------------------- 人和团队


@action
def start_recruitment(state: GameState, content: Content, channel: str, specialty: str) -> None:
    _require(state.recruitment is None, "已经有一次招聘在进行了")
    _require(specialty in ATTRS, f"不认识的专长：{specialty}")
    try:
        ch = content.channel(channel)
    except KeyError:
        raise ActionError(f"没有这个招聘渠道：{channel}") from None
    _pay(state, ch.cost, "recruiting", f"在{ch.name}招聘")
    weeks = content.balance.recruiting.weeks
    state.recruitment = Recruitment(channel=channel, specialty=specialty, ready_week=state.week + weeks)
    say(state, f"在{ch.name}发布招聘，{weeks} 周后出结果")


@action
def hire_candidate(state: GameState, content: Content, decision_id: int, index: int, members: int = 0) -> int:
    """index 是第几位候选人（从 0 开始）；-1 表示都不要。返回新团队的编号（都不要时是 0）。"""
    decision = _decision(state, decision_id, decisions.CANDIDATES)
    recruitment = state.recruitment
    assert recruitment is not None
    if index == -1:
        state.recruitment = None
        decisions.remove(state, decision)
        say(state, "这次招聘一个都没签")
        return 0
    _require(0 <= index < len(recruitment.candidates), "没有这位候选人")
    _require(members >= 0, "成员人数不能为负")
    _require(state.headcount + 1 + members <= capacity(state, content), "场地坐不下了，先升级场地")
    lead = recruitment.candidates[index]
    fee = content.balance.recruiting.signing_months * lead_salary(lead, content)
    fee += members * content.balance.team.member_hire_fee
    _pay(state, fee, "hiring", f"签{lead.name}")
    team = Team(id=state.new_id(), lead=lead, members=members)
    state.teams.append(team)
    state.recruitment = None
    decisions.remove(state, decision)
    say(state, f"{lead.name}加入了公司，带领新的{content.texts.names.teams[lead.specialty]}")
    return team.id


@action
def add_members(state: GameState, content: Content, team_id: int, count: int) -> None:
    team = _team(state, team_id)
    _require(count >= 1, "至少加 1 个人")
    _require(state.headcount + count <= capacity(state, content), "场地坐不下了，先升级场地")
    _pay(state, count * content.balance.team.member_hire_fee, "hiring", f"招 {count} 个人")
    team.members += count
    say(state, f"{team.lead.name}的团队加了 {count} 个人，现在 {team.members} 人")


@action
def remove_members(state: GameState, content: Content, team_id: int, count: int) -> None:
    team = _team(state, team_id)
    _require(1 <= count <= team.members, "减的人数不对")
    spend(state, count * content.balance.team.member_severance, "severance")  # 遣散费不要求现金够
    team.members -= count
    say(state, f"{team.lead.name}的团队减了 {count} 个人，现在 {team.members} 人")


@action
def fire_lead(state: GameState, content: Content, team_id: int) -> None:
    team = _team(state, team_id)
    if team.task == ON_PROJECT:
        project = state.project(team.task_id)
        _require(not decisions.for_project(state, project.id), "先处理完这个项目待决定的事")
        project.team_ids = [i for i in project.team_ids if i != team.id]
    elif team.task == ON_CONTRACT:
        state.contracts = [c for c in state.contracts if c.team_id != team.id]
    severance = lead_salary(team.lead, content) + team.members * content.balance.team.member_severance
    spend(state, severance, "severance")
    state.teams.remove(team)
    say(state, f"{team.lead.name}离开了公司，团队解散")


@action
def train_lead(state: GameState, content: Content, team_id: int, attr: str) -> None:
    team = _team(state, team_id)
    _require(attr in ATTRS, f"不认识的属性：{attr}")
    lead = team.lead
    cap = training_cap(lead, attr, content)
    _require(lead.attr(attr) < cap, f"{content.texts.names.attrs[attr]}已达到专业培养上限 {cap}")
    cost, data = training_cost(lead, attr, content)
    _require(state.data >= data, f"研究数据不够：要 {data}，你只有 {state.data}")
    _pay(state, cost, "training", "培训")
    state.data -= data
    setattr(lead, attr, min(cap, lead.attr(attr) + content.balance.growth.training_gain))
    say(state, f"{lead.name}进修{content.texts.names.attrs[attr]}，现在是 {lead.attr(attr)}")


# ---------------------------------------------------------------- 外包、解锁、场地


@action
def accept_contract(state: GameState, content: Content, offer_id: int, team_id: int) -> None:
    offer = next((o for o in state.offers if o.id == offer_id), None)
    _require(offer is not None, "这个外包单已经没有了")
    assert offer is not None
    contract = content.contracts[offer.kind]
    team = _team(state, team_id)
    _require(team.idle, f"{team.lead.name}的团队正忙")
    attr_name = content.texts.names.attrs[contract.attr]
    _require(
        team.lead.attr(contract.attr) >= contract.requirement,
        f"这个外包要求{attr_name} ≥ {contract.requirement}",
    )
    weeks = duration(team, contract, content)
    state.contracts.append(
        ActiveContract(
            id=state.new_id(),
            kind=offer.kind,
            team_id=team.id,
            weeks_total=weeks,
            weeks_left=weeks,
            reward=reward(team, contract, content),
            data=contract.data,
        )
    )
    team.task, team.task_id = ON_CONTRACT, state.contracts[-1].id
    state.offers.remove(offer)
    say(state, f"{team.lead.name}的团队接了外包「{contract.name}」，{weeks} 周")


@action
def unlock_target(state: GameState, content: Content, key: str) -> None:
    _require(key in content.targets, f"没有这个靶点：{key}")
    problems = target_unlock_problems(state, key, content)
    _require(not problems, "；".join(problems))
    state.data -= content.targets[key].unlock
    state.unlocked_targets.append(key)
    say(state, f"解锁靶点 {content.targets[key].name}")


@action
def unlock_modality(state: GameState, content: Content, key: str) -> None:
    _require(key in content.modalities, f"没有这种分子类型：{key}")
    problems = modality_unlock_problems(state, key, content)
    _require(not problems, "；".join(problems))
    state.data -= content.modalities[key].unlock
    state.unlocked_modalities.append(key)
    say(state, f"解锁分子类型 {content.modalities[key].name}")


@action
def build_facility(state: GameState, content: Content) -> None:
    nxt = next_facility(state, content)
    _require(nxt is not None, "已经是最大的场地了")
    assert nxt is not None
    _pay(state, nxt.cost, "facility", f"建{nxt.name}")
    state.facility = nxt.key
    clinical.promote_queue(state, content)
    say(state, f"搬进了{nxt.name}，可以容纳 {nxt.capacity} 人")
