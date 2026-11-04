"""bot：不用键盘的玩家。和界面一样，只通过 engine.actions 操作游戏（design/tech.md 第 9 节）。

三种策略：
- 新手：只靠笔记本学组合（没做过的就按顺序试），项目做完再开下一个，不接外包
- 稳健：懂科学（知道真实的组合档位），优先招毒理和工艺，留足现金，团队闲着就接外包，分数不够就终止
- 激进：懂科学，一个团队开一个项目，同时铺开，专挑大市场，从不终止
"""

from __future__ import annotations

from drugstory.content import ATTRS, Content
from drugstory.engine import actions as A
from drugstory.engine import decisions as D
from drugstory.engine.queries import (
    clinical_estimate,
    committed_costs,
    contract_terms,
    eligible_teams,
    modality_unlock_problems,
    next_facility,
    notebook_entry,
    rd_estimate,
    target_unlock_problems,
)
from drugstory.engine.rules.combo import compat, multiplier
from drugstory.engine.rules.scoring import expected_scores, passed
from drugstory.engine.state import RESEARCH, GameState, Project, Team
from drugstory.engine.systems.clinical import prior_approvals
from drugstory.engine.systems.research import best_team
from drugstory.engine.systems.teams import capacity, lead_salary, payroll, training_cost


class Bot:
    name = "bot"
    uses_true_tiers = False
    min_tier = -2
    takes_contracts = False
    terminates = False
    teams_per_project = 0  # 0 表示把空闲团队都派上
    reserve_months = 3
    max_projects_in_research = 1
    channels = ("headhunter", "conference", "web")

    # ---------------------------------------------------------------- 每周的管理

    def manage(self, state: GameState, content: Content) -> None:
        self.unlock(state, content)
        self.build(state, content)
        self.hire(state, content)
        self.grow(state, content)
        self.train(state, content)
        self.reinforce(state, content)
        self.start_projects(state, content)
        if self.wants_contracts(state, content):
            self.take_contracts(state, content)

    def wants_contracts(self, state: GameState, content: Content) -> bool:
        return self.takes_contracts or state.cash < 1500

    def reinforce(self, state: GameState, content: Content) -> None:
        """在研项目缺某个专长、又有这个专长的团队闲着，就把它加进去。"""
        limit = content.balance.team.max_per_project
        for project in state.projects:
            if project.stage != RESEARCH or len(project.team_ids) >= limit:
                continue
            have = {state.team(i).lead.specialty for i in project.team_ids}
            for team in sorted(state.idle_teams, key=lambda t: t.id):
                if team.lead.specialty not in have and len(project.team_ids) < limit:
                    A.set_project_teams(state, content, project_id=project.id, team_ids=[*project.team_ids, team.id])
                    have.add(team.lead.specialty)

    def monthly_burn(self, state: GameState, content: Content) -> float:
        return payroll(state, content) + content.facility(state.facility).rent

    def reserve(self, state: GameState, content: Content) -> float:
        return self.reserve_months * self.monthly_burn(state, content)

    def spare_cash(self, state: GameState, content: Content) -> float:
        """手上的现金，减去安全垫，再减去在研项目接下来还要花的钱。"""
        return state.cash - self.reserve(state, content) - committed_costs(state, content)

    def tier(self, state: GameState, target: str, modality: str, content: Content) -> int | None:
        if self.uses_true_tiers:
            return compat(content.targets[target], content.modalities[modality], content)[0]
        entry = notebook_entry(state, target, modality)
        return None if entry is None else entry.tier

    def combo_value(self, state: GameState, target: str, modality: str, content: Content) -> float:
        tier = self.tier(state, target, modality, content)
        if tier is None:
            tier = 0  # 新手对没做过的组合一无所知，当作"一般"
        market = content.balance.market.base_by_tier[content.targets[target].market - 1]
        difficulty = content.targets[target].difficulty
        return market * multiplier(tier, content) ** 2 / difficulty**2

    def choose_combo(self, state: GameState, content: Content) -> tuple[str, str] | None:
        in_progress = {(p.target, p.modality) for p in state.active_projects}
        options = []
        for t in state.unlocked_targets:
            for m in state.unlocked_modalities:
                if (t, m) in in_progress:
                    continue
                tier = self.tier(state, t, m, content)
                if tier is not None and tier < self.min_tier:
                    continue
                options.append((self.combo_value(state, t, m, content), t, m))
        if not options:
            return None
        options.sort(key=lambda o: (-o[0], o[1], o[2]))
        return options[0][1], options[0][2]

    def can_fund(self, state: GameState, target: str, modality: str, content: Content) -> bool:
        _, rd_cost = rd_estimate(target, modality, content)
        _, trial_cost = clinical_estimate(target, modality, content)
        return self.spare_cash(state, content) >= rd_cost + trial_cost

    def start_projects(self, state: GameState, content: Content) -> None:
        researching = [p for p in state.projects if p.stage == RESEARCH]
        while len(researching) < self.max_projects_in_research and state.idle_teams:
            combo = self.choose_combo(state, content)
            if combo is None or not self.can_fund(state, *combo, content):
                return
            teams = self.pick_teams(state, content)
            A.start_project(state, content, target=combo[0], modality=combo[1], team_ids=[t.id for t in teams])
            researching = [p for p in state.projects if p.stage == RESEARCH]

    def pick_teams(self, state: GameState, content: Content) -> list[Team]:
        """先每个专长挑一个最强的，再用剩下的补满。"""
        limit = content.balance.team.max_per_project
        if self.teams_per_project:
            limit = min(limit, self.teams_per_project)
        idle = sorted(state.idle_teams, key=lambda t: (-t.lead.attr(t.lead.specialty), t.id))
        chosen: list[Team] = []
        for attr in ("bio", "tox", "chem", "proc"):
            team = next((t for t in idle if t.lead.specialty == attr and t not in chosen), None)
            if team is not None and len(chosen) < limit:
                chosen.append(team)
        for team in idle:
            if len(chosen) >= limit:
                break
            if team not in chosen:
                chosen.append(team)
        return chosen

    def wanted_specialty(self, state: GameState) -> str | None:
        have = {t.lead.specialty for t in state.teams}
        for attr in ("tox", "proc", "bio", "chem"):
            if attr not in have:
                return attr
        return None

    def hire(self, state: GameState, content: Content) -> None:
        if state.recruitment is not None or state.headcount + 1 > capacity(state, content):
            return
        specialty = self.wanted_specialty(state)
        if specialty is None:
            return
        spare = self.spare_cash(state, content)
        for channel in self.channels:
            ch = content.channel(channel)
            if spare >= ch.cost * 3:
                A.start_recruitment(state, content, channel=channel, specialty=specialty)
                return

    def grow(self, state: GameState, content: Content) -> None:
        fee = content.balance.team.member_hire_fee
        for team in sorted(state.teams, key=lambda t: t.id):
            room = capacity(state, content) - state.headcount
            want = team.lead.leadership - team.members
            if want <= 0 or room <= 0:
                continue
            count = min(want, room)
            if self.spare_cash(state, content) < count * fee + 12 * count * content.balance.team.member_salary:
                return
            A.add_members(state, content, team_id=team.id, count=count)

    def train(self, state: GameState, content: Content) -> None:
        for team in sorted(state.teams, key=lambda t: t.id):
            attr = team.lead.specialty
            if team.lead.attr(attr) >= content.balance.team.max_attr:
                continue
            cost, data = training_cost(team.lead, attr, content)
            if state.data >= data + 100 and self.spare_cash(state, content) >= cost * 4:
                A.train_lead(state, content, team_id=team.id, attr=attr)

    def unlock(self, state: GameState, content: Content) -> None:
        # 先解锁能马上用得上的分子类型，再解锁大市场的靶点
        for key in content.modalities:
            if not modality_unlock_problems(state, key, content):
                A.unlock_modality(state, content, key=key)
                return
        locked = [k for k in content.targets if k not in state.unlocked_targets]
        locked.sort(key=lambda k: (-content.targets[k].market, content.targets[k].unlock, k))
        for key in locked:
            if not target_unlock_problems(state, key, content):
                A.unlock_target(state, content, key=key)
                return

    def build(self, state: GameState, content: Content) -> None:
        nxt = next_facility(state, content)
        if nxt is None or state.headcount < capacity(state, content) - 2:
            return
        if self.spare_cash(state, content) >= nxt.cost * 1.5:
            A.build_facility(state, content)

    def take_contracts(self, state: GameState, content: Content) -> None:
        for offer in list(state.offers):
            contract = content.contracts[offer.kind]
            teams = eligible_teams(state, contract)
            if not teams:
                continue
            team = max(teams, key=lambda t: (contract_terms(t, contract, content)[1], -t.id))
            A.accept_contract(state, content, offer_id=offer.id, team_id=team.id)

    # ---------------------------------------------------------------- 需要决定的事

    def resolve(self, state: GameState, content: Content, decision) -> None:
        kind = decision.kind
        if kind == D.MILESTONE:
            project = state.project(decision.project_id)
            team = best_team(state, project, decision.data["stat"], content)
            A.choose_milestone_team(state, content, decision_id=decision.id, team_id=team.id)
        elif kind == D.RD_END:
            A.resolve_rd_end(state, content, decision_id=decision.id, choice=self.rd_choice(state, content, decision))
        elif kind == D.PHASE_RESULT:
            choice = self.phase_choice(state, content, decision) if decision.data["passed"] else "ack"
            A.resolve_phase(state, content, decision_id=decision.id, choice=choice)
        elif kind == D.APPROVAL:
            A.name_drug(state, content, decision_id=decision.id, name=decision.data["suggested"])
        elif kind == D.CANDIDATES:
            self.pick_candidate(state, content, decision)
        else:
            A.acknowledge(state, content, decision_id=decision.id)

    def expected_ok(self, state: GameState, project: Project, phase_key: str, content: Content) -> bool:
        target = content.targets[project.target]
        prior = prior_approvals(state, project.target)
        scores = expected_scores(project.stats, target, phase_key, state.week, content, prior)
        return passed(phase_key, scores, content)

    def rd_choice(self, state: GameState, content: Content, decision) -> str:
        if not self.terminates:
            return "proceed"
        project = state.project(decision.project_id)
        if all(self.expected_ok(state, project, k, content) for k in content.phase_keys):
            return "proceed"
        extensions = (project.rd_weeks - rd_estimate(project.target, project.modality, content)[0]) // (
            content.balance.research.extension_weeks
        )
        if project.team_ids and extensions < 3:
            return "extend"
        return "terminate"

    def phase_choice(self, state: GameState, content: Content, decision) -> str:
        if not self.terminates:
            return "continue"
        project = state.project(decision.project_id)
        return "continue" if self.expected_ok(state, project, decision.data["next"], content) else "terminate"

    def pick_candidate(self, state: GameState, content: Content, decision) -> None:
        recruitment = state.recruitment
        assert recruitment is not None
        fee_months = content.balance.recruiting.signing_months
        options = [
            (lead.attr(lead.specialty), -i, i)
            for i, lead in enumerate(recruitment.candidates)
            if state.cash >= fee_months * lead_salary(lead, content)
        ]
        if not options or state.headcount + 1 > capacity(state, content):
            A.hire_candidate(state, content, decision_id=decision.id, index=-1)
            return
        A.hire_candidate(state, content, decision_id=decision.id, index=max(options)[2])


class Newbie(Bot):
    name = "新手"
    reserve_months = 2
    channels = ("web",)

    def combo_value(self, state: GameState, target: str, modality: str, content: Content) -> float:
        # 没做过的组合：只用界面上看得到的信息猜——靶点要的干预方式，和分子类型擅长的对不对得上
        if notebook_entry(state, target, modality) is None:
            t, m = content.targets[target], content.modalities[modality]
            guess = 0.9 if t.actions & m.actions else 0.3
            market = content.balance.market.base_by_tier[t.market - 1]
            return market * guess / t.difficulty**2
        return super().combo_value(state, target, modality, content)

    def can_fund(self, state: GameState, target: str, modality: str, content: Content) -> bool:
        # 新手看界面上的"已承诺花费"，但不会替新项目提前算临床要花多少
        _, rd_cost = rd_estimate(target, modality, content)
        return self.spare_cash(state, content) >= rd_cost


class Steady(Bot):
    name = "稳健"
    uses_true_tiers = True
    min_tier = 1
    takes_contracts = True
    terminates = True
    reserve_months = 6
    max_projects_in_research = 2

    def wanted_specialty(self, state: GameState) -> str | None:
        counts = {a: sum(t.lead.specialty == a for t in state.teams) for a in ATTRS}
        for attr in ("tox", "proc", "bio", "chem"):
            if counts[attr] == 0:
                return attr
        # 每两个项目配一套人：缺得最多的先补
        if len(state.teams) >= 4 + 4 * (len(state.drugs) // 2):
            return None
        return min(("bio", "chem", "tox", "proc"), key=lambda a: (counts[a], ("bio", "chem", "tox", "proc").index(a)))


class Aggressive(Bot):
    name = "激进"
    uses_true_tiers = True
    min_tier = 0
    reserve_months = 1
    teams_per_project = 3
    max_projects_in_research = 99

    def wanted_specialty(self, state: GameState) -> str | None:
        if len(state.teams) >= 3 + 2 * len(state.drugs):
            return None
        counts = {a: sum(t.lead.specialty == a for t in state.teams) for a in ATTRS}
        return min(ATTRS, key=lambda a: (counts[a], ATTRS.index(a)))


STRATEGIES: dict[str, type[Bot]] = {"newbie": Newbie, "steady": Steady, "aggressive": Aggressive}
