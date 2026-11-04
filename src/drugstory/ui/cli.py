"""文字界面（design/game-design.md 第 14 节）。

界面只读游戏状态，所有修改都通过 engine.actions。输入输出可以替换，测试时用脚本喂输入。
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from collections.abc import Callable
from pathlib import Path

from drugstory.content import ACTIONS, ATTRS, STATS, Content, default_content
from drugstory.engine import actions as A
from drugstory.engine import decisions as D
from drugstory.engine.calendar import label
from drugstory.engine.game import new_game
from drugstory.engine.loop import advance
from drugstory.engine.queries import (
    clinical_estimate,
    committed_costs,
    contract_terms,
    eligible_teams,
    known_tier_text,
    modality_unlock_problems,
    next_facility,
    rd_estimate,
    target_unlock_problems,
)
from drugstory.engine.rules.combo import tier_name
from drugstory.engine.rules.scoring import expected_scores
from drugstory.engine.rules.texts import project_label, spaced
from drugstory.engine.save import SaveError, load, save
from drugstory.engine.state import (
    CLINICAL,
    ON_CONTRACT,
    ON_PROJECT,
    PHASE_REVIEW,
    QUEUED,
    RD_REVIEW,
    RESEARCH,
    Decision,
    GameState,
    Project,
    Team,
)
from drugstory.engine.systems.clinical import phase_plan, prior_approvals
from drugstory.engine.systems.market import curve, sharing
from drugstory.engine.systems.progression import final_score
from drugstory.engine.systems.research import extensions_used, milestone_plan, project_teams
from drugstory.engine.systems.teams import capacity, exp_to_next, lead_salary, team_salary, training_cost

LINE = "─" * 64
AUTOSAVE = Path("autosave.json")


class Quit(Exception):
    """玩家要退出，或者输入结束了。"""


def money(x: float) -> str:
    return f"¥{round(x):,} 万"


class CLI:
    def __init__(
        self,
        state: GameState,
        content: Content,
        input_fn: Callable[[str], str] | None = None,
        print_fn: Callable[..., None] | None = None,
        delay: float = 0.4,
        autosave: Path | None = AUTOSAVE,
    ) -> None:
        self.state = state
        self.content = content
        # 默认在调用时才去拿内置的 input/print，测试里可以替换
        self._input = input_fn or (lambda prompt: input(prompt))
        self._print = print_fn or (lambda *args: print(*args))
        self.delay = delay
        self.autosave = autosave
        self.shown_week = state.week
        self.names = content.texts.names

    # ---------------------------------------------------------------- 输入输出

    def say(self, text: str = "") -> None:
        self._print(text)

    def pause(self, scale: float = 1.0) -> None:
        if self.delay:
            time.sleep(self.delay * scale)

    def ask(self, prompt: str) -> str:
        try:
            return self._input(prompt).strip()
        except EOFError:
            raise Quit from None

    def choose(self, prompt: str, count: int, default: int | None = None, allow_back: bool = True) -> int | None:
        """让玩家选 1..count 中的一个，返回从 0 开始的下标；直接回车返回 default，输入 0 返回 None（返回上一层）。"""
        while True:
            hint = f"（回车 = {default + 1}）" if default is not None else ""
            back = "，0 返回" if allow_back else ""
            text = self.ask(f"{prompt}{hint}[1-{count}{back}] > ")
            if not text and default is not None:
                return default
            if text == "0" and allow_back:
                return None
            if text.isdigit() and 1 <= int(text) <= count:
                return int(text) - 1
            self.say("❌ 请输入列表里的编号")

    def ask_count(self, prompt: str, maximum: int) -> int | None:
        while True:
            text = self.ask(f"{prompt}[1-{maximum}，0 返回] > ")
            if text in ("", "0"):
                return None
            if text.isdigit() and 1 <= int(text) <= maximum:
                return int(text)
            self.say("❌ 请输入一个合理的数字")

    def confirm(self, prompt: str) -> bool:
        return self.ask(f"{prompt}[y/N] > ").lower() in ("y", "yes", "是")

    def act(self, name: str, **kwargs) -> object:
        """执行一个操作；不合法就告诉玩家原因，返回 None。"""
        try:
            return A.ACTIONS[name](self.state, self.content, **kwargs)
        except A.ActionError as e:
            self.say(f"❌ {e}")
            return None

    # ---------------------------------------------------------------- 主循环

    def run(self) -> None:
        self.say("新药物语 · 开罗式制药经营游戏（输入 ? 看命令说明）")
        try:
            while True:
                self.resolve_pending()
                if self.state.game_over:
                    self.show_dashboard()
                    self.game_over()
                    return
                self.show_dashboard()
                self.command(self.ask("> ").lower())
        except Quit:
            self.say("再见！")

    def command(self, cmd: str) -> None:
        handlers: dict[str, Callable[[], None]] = {
            "": lambda: self.advance(4),
            "f": lambda: self.advance(self.content.balance.time.weeks_per_year),
            "n": self.menu_new_project,
            "p": self.menu_projects,
            "t": self.menu_teams,
            "h": self.menu_recruit,
            "c": self.menu_contracts,
            "u": self.menu_unlock,
            "b": self.menu_facility,
            "k": self.menu_notebook,
            "d": self.menu_drugs,
            "s": self.menu_save,
            "?": self.help,
            "q": self.quit,
        }
        handler = handlers.get(cmd)
        if handler is None:
            self.say("❌ 不认识这个命令，输入 ? 看说明")
        else:
            handler()

    def advance(self, weeks: int) -> None:
        advance(self.state, self.content, weeks)

    def help(self) -> None:
        self.say(
            "回车 继续（最多 4 周）  f 快进到下一件要决定的事  n 立项  p 项目  t 团队  h 招聘负责人\n"
            "c 外包  u 解锁靶点和分子类型  b 场地  k 笔记本  d 药物和成就  s 存档  q 退出\n"
            "研发要团队，临床不要：药进了临床，团队就可以去开下一个项目。"
        )

    def quit(self) -> None:
        if self.confirm("要先存档吗？"):
            self.menu_save()
        raise Quit

    # ---------------------------------------------------------------- 主界面

    def show_dashboard(self) -> None:
        s, c = self.state, self.content
        committed = committed_costs(s, c)
        promise = f"（已承诺 {money(committed)}）" if committed else ""
        self.say()
        self.say("═" * 64)
        self.say(
            f"{label(s.week, c)}   现金 {money(s.cash)}{promise}   研究数据 {s.data}   "
            f"口碑 {s.reputation:.0f}   场地 {s.headcount}/{capacity(s, c)} 人"
        )
        self.say(f"─ 项目 {LINE[5:]}")
        active = s.active_projects
        if not active:
            self.say("（还没有项目，输入 n 立项）")
        for i, p in enumerate(active, 1):
            self.say(f"[{i}] {self.project_line(p)}")
        self.say(f"─ 团队 {LINE[5:]}")
        for i, t in enumerate(s.teams, 1):
            self.say(f"[{i}] {self.team_line(t)}")
        on_sale = [d for d in s.drugs if d.active]
        if on_sale:
            self.say(f"─ 在售 {LINE[5:]}")
            shares = sharing(s)
            for d in on_sale:
                weekly = d.peak * curve(d.weeks_on_market, c) / shares[d.target]
                star = " ★" if d.hall_of_fame else ""
                combo = f"{c.targets[d.target].name} × {c.modalities[d.modality].name}"
                self.say(f"{d.name}{star}（{combo}）  {money(weekly)}/周  上市第 {d.weeks_on_market} 周")
        recent = [m for m in s.messages if m.week >= self.shown_week][-12:]
        if recent:
            self.say(f"─ 最近 {LINE[5:]}")
            for m in recent:
                self.say(m.text)
        self.shown_week = s.week
        self.say(LINE)
        self.say(
            "[回车] 继续  [f] 快进  [n] 立项  [p] 项目  [t] 团队  [h] 招聘  [c] 外包  [u] 解锁  "
            "[b] 场地  [k] 笔记本  [d] 药物  [s] 存档  [?] 帮助  [q] 退出"
        )

    def project_line(self, p: Project) -> str:
        c = self.content
        name = project_label(p, c)
        if p.stage in (RESEARCH, RD_REVIEW):
            stats = " ".join(f"{self.names.stats[k]} {p.stats[k]:.0f}" for k in STATS)
            teams = f"{len(p.team_ids)} 个团队" if p.team_ids else "没有团队，暂停中"
            return f"{name}  研发 {p.rd_done}/{p.rd_weeks} 周  {stats}  隐患 {len(p.hazards)}  {teams}"
        if p.stage == CLINICAL:
            done = p.phase_weeks - p.phase_weeks_left
            return f"{name}  {c.phase(p.phase).name} {done}/{p.phase_weeks} 周"
        if p.stage == QUEUED:
            return f"{name}  等待临床席位，不占研发团队、不收临床费"
        if p.stage == PHASE_REVIEW:
            return f"{name}  {c.phase(p.phase).name}已过关，等你决定"
        return f"{name}  等待起名"

    def team_line(self, t: Team) -> str:
        lead = t.lead
        spec = lead.specialty
        task = "空闲"
        if t.task == ON_PROJECT:
            task = f"→ {project_label(self.state.project(t.task_id), self.content)}"
        elif t.task == ON_CONTRACT:
            contract = next(x for x in self.state.contracts if x.id == t.task_id)
            task = f"→ 外包：{self.content.contracts[contract.kind].name}（还剩 {contract.weeks_left} 周）"
        return (
            f"{self.names.teams[spec]}  {lead.name}  {self.names.attrs[spec]} {lead.attr(spec)}  Lv{lead.level}  "
            f"+{t.members} 人  {task}"
        )

    # ---------------------------------------------------------------- 需要决定的事

    def resolve_pending(self) -> None:
        handlers = {
            D.MILESTONE: self.on_milestone,
            D.RD_END: self.on_rd_end,
            D.PHASE_RESULT: self.on_phase_result,
            D.APPROVAL: self.on_approval,
            D.CANDIDATES: self.on_candidates,
            D.CASH_NEGATIVE: self.on_cash_negative,
            D.YEAR_END: self.on_year_end,
            D.GAME_END: self.on_game_end,
        }
        while self.state.pending and not self.state.game_over:
            decision = self.state.pending[0]
            self.say()
            handlers[decision.kind](decision)

    def on_milestone(self, d: Decision) -> None:
        s, c = self.state, self.content
        p = s.project(d.project_id)
        stat = d.data["stat"]
        self.say(f"⚑ {project_label(p, c)} 到了「{self.names.milestones[stat]}」节点（{self.names.stats[stat]}）")
        teams = project_teams(s, p)
        self.say("  [1] 深挖性能：追加费用和工期，提升属性")
        self.say("  [2] 专项验证：消除已知隐患，放弃属性加成")
        self.say("  [3] 尽快定型：缩短工期，放弃属性加成")
        plan_index = self.choose("选择攻关方案", 3, default=0, allow_back=False)
        plan = ("boost", "validate", "fast")[plan_index or 0]
        options = [milestone_plan(s, p, t, plan, c) for t in teams]
        for i, (t, effect) in enumerate(zip(teams, options, strict=True), 1):
            self.say(f"  [{i}] {t.lead.name} · {c.balance.traits[t.lead.trait].name}："
                     f"加点 {effect['bonus']:.1f}，{effect['weeks']:+} 周，费用 {money(effect['cost'])}，"
                     f"排险 {len(effect['hazard_ids'])} 项 {effect['problem']}")
        index = self.choose("派哪个团队攻关？", len(teams), default=0, allow_back=False)
        assert index is not None
        self.act("choose_milestone_team", decision_id=d.id, team_id=teams[index].id, plan=plan)

    def expectation_lines(self, p: Project, phases: list[str]) -> list[str]:
        """按现在的属性，各期预计能拿几分（不算随机和隐患）。"""
        s, c = self.state, self.content
        target = c.targets[p.target]
        prior = prior_approvals(s, p.target)
        lines = []
        for key in phases:
            phase = c.phase(key)
            scores = expected_scores(p.stats, target, key, s.week, c, prior)
            parts = "  ".join(f"{self.names.stats[k]} {v}" for k, v in scores.items())
            lines.append(f"  预计{spaced(phase.name)}：{parts}{self.pass_hint(key, scores)}")
        return lines

    def pass_hint(self, key: str, scores: dict[str, int]) -> str:
        phase = self.content.phase(key)
        problems = [f"{self.names.stats[k]}要 {line} 分" for k, line in phase.pass_.items() if scores[k] < line]
        if phase.pass_total and sum(scores.values()) < phase.pass_total:
            problems.append(f"总分要 {phase.pass_total}")
        return f"  ⚠️ 可能过不了（{'，'.join(problems)}）" if problems else ""

    def on_rd_end(self, d: Decision) -> None:
        s, c = self.state, self.content
        p = s.project(d.project_id)
        self.say(f"⚑ {project_label(p, c)} 研发期结束")
        self.say("  " + "  ".join(f"{self.names.stats[k]} {p.stats[k]:.0f}" for k in STATS))
        if p.hazards:
            hazards = "、".join(f"{h.text}（{self.names.stats[h.stat]}，严重度 {h.severity}）" for h in p.hazards)
            self.say(f"  还有 {len(p.hazards)} 个隐患没清掉：{hazards}")
        for line in self.expectation_lines(p, c.phase_keys):
            self.say(line)
        weeks, cost = clinical_estimate(p.target, p.modality, c)
        extra = c.balance.research.extension_weeks
        extend_cost = extra * c.modalities[p.modality].weekly_cost
        used = extensions_used(p, c)
        limit = c.balance.research.max_extensions
        self.say(f"  [1] 进入临床：一共约 {weeks} 周、{money(cost)}，团队空出来")
        self.say(f"  [2] 多磨 {extra} 周：研发费 {money(extend_cost)}，另付工资租金；已用 {used}/{limit} 次")
        self.say("  [3] 终止：钱不再花，熟练度照涨")
        self.say("  [4] 专项排险：2 周，按隐患数量付费，不加点、不产生新隐患")
        self.say(f"  [5] 委托临床：不占自营席位，全程约 {money(cost * 1.3)}")
        index = self.choose("怎么办？", 5, allow_back=False)
        choice = ("proceed", "extend", "terminate", "validate", "contract")[index or 0]
        self.act("resolve_rd_end", decision_id=d.id, choice=choice)

    def show_result(self, p: Project, phase_key: str) -> None:
        c = self.content
        result = next(r for r in reversed(p.results) if r.phase == phase_key)
        self.say(f"━━ {project_label(p, c)} · {c.phase(phase_key).name}结果 ━━")
        self.pause()
        for stat, score in result.scores.items():
            self.say(f"  {self.names.stats[stat]}专家：{'●' * score}{'○' * (10 - score)} {score} 分")
            self.pause()
        for line in result.hazard_texts:
            self.say(f"  💥 {line}")
            self.pause()
        self.say(f"  {result.text}")
        self.pause()

    def on_phase_result(self, d: Decision) -> None:
        s, c = self.state, self.content
        p = s.project(d.project_id)
        self.show_result(p, d.data["phase"])
        if not d.data["passed"]:
            self.say("  ✗ 没过关，项目结束。研究数据和熟练度照样涨了。")
            self.ask("（回车继续）")
            self.act("resolve_phase", decision_id=d.id, choice="ack")
            return
        nxt = d.data["next"]
        weeks, cost = phase_plan(p, nxt, c)
        self.say(f"  ✓ 过关！下一步是{c.phase(nxt).name}：{weeks} 周、{money(cost)}")
        for line in self.expectation_lines(p, [nxt]):
            self.say(line)
        self.say("  [1] 继续  [2] 终止")
        index = self.choose("怎么办？", 2, default=0, allow_back=False)
        self.act("resolve_phase", decision_id=d.id, choice="continue" if index == 0 else "terminate")

    def on_approval(self, d: Decision) -> None:
        s, c = self.state, self.content
        p = s.project(d.project_id)
        self.show_result(p, c.phase_keys[-1])
        hall = p.composite >= c.balance.scoring.hall_of_fame
        self.say(f"  🎉 获批上市！综合分 {p.composite:.1f}{'，进入名人堂 ★' if hall else ''}")
        while True:
            name = self.ask(f"给药起个名字（回车用推荐的 {d.data['suggested']}）> ") or d.data["suggested"]
            if self.act("name_drug", decision_id=d.id, name=name) is not None:
                return

    def on_candidates(self, d: Decision) -> None:
        s, c = self.state, self.content
        recruitment = s.recruitment
        assert recruitment is not None
        self.say(f"⚑ {c.channel(recruitment.channel).name}的候选人：")
        months = c.balance.recruiting.signing_months
        for i, lead in enumerate(recruitment.candidates, 1):
            attrs = "  ".join(f"{self.names.attrs[a]} {lead.attr(a)}" for a in ATTRS)
            salary = lead_salary(lead, c)
            self.say(
                f"  [{i}] {lead.name}（{self.names.teams[lead.specialty]}）  {attrs}  带队 {lead.leadership}  "
                f"月薪 {money(salary)}  签约费 {money(months * salary)}"
            )
        while True:
            index = self.choose("签哪一位？", len(recruitment.candidates))
            if index is None:
                self.act("hire_candidate", decision_id=d.id, index=-1)
                return
            team_id = self.act("hire_candidate", decision_id=d.id, index=index)
            if team_id is not None:
                self.offer_to_join(self.state.team(team_id))
                return

    def offer_to_join(self, team: Team) -> None:
        """新团队要不要直接加进一个缺这个专长的在研项目。"""
        s, c = self.state, self.content
        limit = c.balance.team.max_per_project
        spec = team.lead.specialty
        for p in s.projects:
            if p.stage != RESEARCH or len(p.team_ids) >= limit:
                continue
            if spec in {s.team(i).lead.specialty for i in p.team_ids}:
                continue
            question = f"{project_label(p, c)} 还没有{self.names.teams[spec]}，要把{team.lead.name}的团队加进去吗？"
            if self.confirm(question):
                self.act("set_project_teams", project_id=p.id, team_ids=[*p.team_ids, team.id])
            return

    def on_cash_negative(self, d: Decision) -> None:
        self.say(f"⚠️ 现金变成负数了（{money(d.data['cash'])}）。连续 {d.data['limit']} 个月月底为负，公司就会破产。")
        self.say("   办法：接外包（c）、减人（t）、终止没希望的项目（p），或者等药上市回款。")
        self.ask("（回车继续）")
        self.act("acknowledge", decision_id=d.id)

    def on_year_end(self, d: Decision) -> None:
        data = d.data
        self.say(f"━━ 第 {data['year']} 年年报 ━━")
        self.say(
            f"  药品销售额 {money(data['revenue'])}   进账 {money(data['income'])}   支出 {money(data['expense'])}"
        )
        self.say(
            f"  获批 {data['approvals']} 个   失败 {data['failures']} 个   年底现金 {money(data['cash'])}   "
            f"口碑 {data['reputation']:.0f}"
        )
        if self.autosave is not None:
            save(self.state, self.autosave)
            self.say(f"  （已自动存档到 {self.autosave}）")
        self.ask("（回车继续）")
        self.act("acknowledge", decision_id=d.id)

    def on_game_end(self, d: Decision) -> None:
        data = d.data
        years = self.content.balance.time.career_years
        self.say(f"━━ {years} 年结算 ━━")
        self.say(
            f"  累计利润 {money(data['profit'])}   获批 {data['approvals']} 个   "
            f"名人堂 {data['hall_of_fame']} 个   成就 {data['achievements']} 个"
        )
        self.say(f"  总分：{data['score']}")
        self.say("  可以继续玩下去，之后不再计分。")
        self.ask("（回车继续）")
        self.act("acknowledge", decision_id=d.id)

    def game_over(self) -> None:
        score = final_score(self.state, self.content)
        self.say("━━ 游戏结束：公司破产了 ━━")
        self.say(f"  一共获批 {score['approvals']} 个药，总分 {score['score']}")

    # ---------------------------------------------------------------- 菜单

    def menu_new_project(self) -> None:
        s, c = self.state, self.content
        if not s.idle_teams:
            self.say("❌ 没有空闲的团队。研发要团队，等项目进了临床团队就会空出来。")
            return
        if not s.projects:
            self.say("提示：开局可以试试 EGFR × 小分子，这是个很稳的组合。")
        if all(t.lead.specialty != "tox" for t in s.teams):
            self.say("提示：还没有毒理组，安全性很可能拖后腿。可以先用 h 招一个毒理负责人。")
        targets = [c.targets[k] for k in s.unlocked_targets]
        self.say("选靶点：")
        for i, t in enumerate(targets, 1):
            approved = prior_approvals(s, t.key)
            mine = f"，你已经有 {approved} 个药" if approved else ""
            self.say(f"  [{i}] {t.name}（{t.disease}）  市场 {'★' * t.market}  难度 {t.difficulty}{mine}")
        ti = self.choose("哪个靶点？", len(targets))
        if ti is None:
            return
        target = targets[ti]
        modalities = [c.modalities[k] for k in s.unlocked_modalities]
        self.say(f"选分子类型（{target.name}：{self.target_tags(target.key)}）：")
        for i, m in enumerate(modalities, 1):
            rd_weeks, rd_cost = rd_estimate(target.key, m.key, c)
            _, trial_cost = clinical_estimate(target.key, m.key, c)
            note = known_tier_text(s, target.key, m.key, c)
            costs = f"研发 {rd_weeks} 周 {money(rd_cost)}，临床约 {money(trial_cost)}"
            self.say(f"  [{i}] {m.name}  {costs}  笔记本：{note}")
        mi = self.choose("哪种分子类型？", len(modalities))
        if mi is None:
            return
        team_ids = self.pick_teams(s.idle_teams, c.balance.team.max_per_project)
        if team_ids is None:
            return
        self.act("start_project", target=target.key, modality=modalities[mi].key, team_ids=team_ids)

    def target_tags(self, key: str) -> str:
        t = self.content.targets[key]
        location = {"secreted": "胞外分泌", "surface": "细胞表面", "intracellular": "细胞内", "nucleic": "基因层面"}
        pocket = {"yes": "有口袋", "hard": "口袋很难做", "no": "没有口袋"}
        actions = "、".join(self.names.actions[a] for a in ACTIONS if a in t.actions)
        return f"{location[t.location]}，{pocket[t.pocket]}，要{actions}，在{self.names.tissues[t.tissue]}"

    def pick_teams(self, teams: list[Team], limit: int, current: list[int] | None = None) -> list[int] | None:
        self.say(f"配哪些团队？（最多 {limit} 个，用空格隔开编号）")
        for i, t in enumerate(teams, 1):
            mark = " ✓" if current and t.id in current else ""
            attrs = "  ".join(f"{self.names.attrs[a]} {t.lead.attr(a)}" for a in ATTRS)
            self.say(f"  [{i}] {self.names.teams[t.lead.specialty]} {t.lead.name}  {attrs}  +{t.members} 人{mark}")
        default = [t.id for t in teams][:limit]
        while True:
            text = self.ask(f"团队编号（回车 = {' '.join(str(i) for i in range(1, len(default) + 1))}，0 返回）> ")
            if text == "0":
                return None
            if not text:
                return default
            parts = text.replace(",", " ").split()
            if all(p.isdigit() and 1 <= int(p) <= len(teams) for p in parts) and len(set(parts)) == len(parts):
                return [teams[int(p) - 1].id for p in parts]
            self.say("❌ 请输入列表里的编号，用空格隔开")

    def menu_projects(self) -> None:
        s, c = self.state, self.content
        active = s.active_projects
        if not active:
            self.say("还没有在研的项目。")
            return
        for i, p in enumerate(active, 1):
            self.say(f"  [{i}] {self.project_line(p)}")
        index = self.choose("看哪个项目？", len(active))
        if index is None:
            return
        p = active[index]
        for r in p.results:
            scores = "  ".join(f"{self.names.stats[k]} {v}" for k, v in r.scores.items())
            self.say(f"  {c.phase(r.phase).name}：{scores}  {r.text}")
        if p.stage != RESEARCH:
            self.say("  （临床阶段自动进行，不需要团队）")
            return
        self.say(f"  组合：{known_tier_text(s, p.target, p.modality, c)}")
        self.say(f"  按现在的属性（研发 {p.rd_done}/{p.rd_weeks} 周，后面还会继续涨）：")
        for line in self.expectation_lines(p, c.phase_keys):
            self.say(line)
        self.say("  [1] 调整团队  [2] 取消项目")
        option = self.choose("做什么？", 2)
        if option == 0:
            candidates = [t for t in s.teams if t.idle or t.id in p.team_ids]
            team_ids = self.pick_teams(candidates, c.balance.team.max_per_project, current=p.team_ids)
            if team_ids is not None:
                self.act("set_project_teams", project_id=p.id, team_ids=team_ids)
        elif option == 1 and self.confirm(f"确定取消 {project_label(p, c)}？已经花的钱拿不回来"):
            self.act("cancel_project", project_id=p.id)

    def menu_teams(self) -> None:
        s, c = self.state, self.content
        for i, t in enumerate(s.teams, 1):
            lead = t.lead
            attrs = "  ".join(f"{self.names.attrs[a]} {lead.attr(a)}" for a in ATTRS)
            self.say(
                f"  [{i}] {lead.name}  {attrs}  带队 {lead.leadership}  Lv{lead.level}"
                f"（经验 {lead.exp}/{exp_to_next(lead, c)}）  +{t.members} 人  "
                f"月薪合计 {money(team_salary(t, c))}"
            )
        index = self.choose("管理哪个团队？", len(s.teams))
        if index is None:
            return
        team = s.teams[index]
        t = c.balance.team
        self.say(f"  [1] 加人（每人招聘费 {money(t.member_hire_fee)}，月薪 {money(t.member_salary)}）")
        self.say(f"  [2] 减人（每人遣散费 {money(t.member_severance)}）")
        self.say("  [3] 培训负责人")
        self.say("  [4] 解雇负责人（整个团队解散）")
        option = self.choose("做什么？", 4)
        if option == 0:
            room = capacity(s, c) - s.headcount
            if room <= 0:
                self.say("❌ 场地坐满了，先用 b 升级场地")
                return
            count = self.ask_count("加几个人？", room)
            if count:
                self.act("add_members", team_id=team.id, count=count)
        elif option == 1:
            if team.members == 0:
                self.say("❌ 这个团队没有成员")
                return
            count = self.ask_count("减几个人？", team.members)
            if count:
                self.act("remove_members", team_id=team.id, count=count)
        elif option == 2:
            for i, a in enumerate(ATTRS, 1):
                cost, data = training_cost(team.lead, a, c)
                now = team.lead.attr(a)
                self.say(f"  [{i}] 进修{self.names.attrs[a]}（现在 {now}）：{money(cost)} + {data} 研究数据")
            attr = self.choose("练哪一项？", len(ATTRS))
            if attr is not None:
                self.act("train_lead", team_id=team.id, attr=ATTRS[attr])
        elif option == 3 and self.confirm(f"确定解雇{team.lead.name}？团队会解散"):
            self.act("fire_lead", team_id=team.id)

    def menu_recruit(self) -> None:
        s, c = self.state, self.content
        if s.recruitment is not None:
            weeks = max(0, s.recruitment.ready_week - s.week)
            self.say(f"招聘进行中，还要 {weeks} 周出结果。")
            return
        channels = list(c.balance.recruiting.channels)
        for i, ch in enumerate(channels, 1):
            low, high = ch.specialty
            self.say(
                f"  [{i}] {ch.name}：{money(ch.cost)}，候选人专长 {low}–{high}，带队能力 {ch.leadership[0]}–"
                f"{ch.leadership[1]}"
            )
        index = self.choose("在哪里招？", len(channels))
        if index is None:
            return
        for i, a in enumerate(ATTRS, 1):
            have = sum(t.lead.specialty == a for t in s.teams)
            self.say(f"  [{i}] {self.names.teams[a]}负责人（现有 {have} 个）")
        spec = self.choose("招什么专长？", len(ATTRS))
        if spec is not None:
            self.act("start_recruitment", channel=channels[index].key, specialty=ATTRS[spec])

    def menu_contracts(self) -> None:
        s, c = self.state, self.content
        if not s.offers:
            self.say("这个月的外包单已经接完了，下个月初会刷新。")
            return
        for i, offer in enumerate(s.offers, 1):
            k = c.contracts[offer.kind]
            self.say(
                f"  [{i}] {k.name}：要求{self.names.attrs[k.attr]} ≥ {k.requirement}，基础 {k.weeks} 周，"
                f"{money(k.reward)} + {k.data} 研究数据"
            )
        index = self.choose("接哪一单？", len(s.offers))
        if index is None:
            return
        offer = s.offers[index]
        contract = c.contracts[offer.kind]
        teams = eligible_teams(s, contract)
        if not teams:
            self.say("❌ 没有符合要求的空闲团队")
            return
        for i, t in enumerate(teams, 1):
            weeks, reward = contract_terms(t, contract, c)
            self.say(f"  [{i}] {t.lead.name}的团队：{weeks} 周，{money(reward)}")
        ti = self.choose("派谁去？", len(teams))
        if ti is not None:
            self.act("accept_contract", offer_id=offer.id, team_id=teams[ti].id)

    def menu_unlock(self) -> None:
        s, c = self.state, self.content
        options: list[tuple[str, str]] = []
        self.say(f"研究数据：{s.data}")
        for key, m in c.modalities.items():
            if key in s.unlocked_modalities:
                continue
            problems = modality_unlock_problems(s, key, c)
            status = "可以解锁" if not problems else "；".join(problems)
            options.append(("modality", key))
            self.say(f"  [{len(options)}] 分子类型 {m.name}（{m.unlock} 研究数据）：{status}")
        for key, t in c.targets.items():
            if key in s.unlocked_targets:
                continue
            problems = target_unlock_problems(s, key, c)
            status = "可以解锁" if not problems else "；".join(problems)
            options.append(("target", key))
            self.say(
                f"  [{len(options)}] 靶点 {t.name}（{t.disease}，市场 {'★' * t.market}，{t.unlock} 研究数据）：{status}"
            )
        if not options:
            self.say("全部解锁了！")
            return
        index = self.choose("解锁哪个？", len(options))
        if index is not None:
            kind, key = options[index]
            self.act("unlock_modality" if kind == "modality" else "unlock_target", key=key)

    def menu_facility(self) -> None:
        s, c = self.state, self.content
        current = c.facility(s.facility)
        self.say(
            f"现在：{current.name}，容纳 {current.capacity} 人，月租 {money(current.rent)}，已经坐了 {s.headcount} 人"
        )
        nxt = next_facility(s, c)
        if nxt is None:
            self.say("已经是最大的场地了。")
            return
        self.say(f"下一级：{nxt.name}，容纳 {nxt.capacity} 人，建造费 {money(nxt.cost)}，月租 {money(nxt.rent)}")
        if self.confirm("要建吗？"):
            self.act("build_facility")

    def menu_notebook(self) -> None:
        s, c = self.state, self.content
        if not s.notebook:
            self.say("笔记本还是空的：研发做完一个组合，就会记下它的档位和原因。")
            return
        for key, entry in sorted(s.notebook.items(), key=lambda kv: (-kv[1].tier, kv[0])):
            t, m = key.split("|")
            best = f"，最好的药综合分 {entry.best_composite:.1f}" if entry.best_composite else ""
            self.say(
                f"  {c.targets[t].name} × {c.modalities[m].name}：{tier_name(entry.tier, c)}（{entry.reason}）"
                f"，做过 {entry.times} 次{best}"
            )

    def menu_drugs(self) -> None:
        s, c = self.state, self.content
        if not s.drugs:
            self.say("还没有药上市。")
        for d in s.drugs:
            star = " ★ 名人堂" if d.hall_of_fame else ""
            status = "在售" if d.active else "已退市"
            combo = f"{c.targets[d.target].name} × {c.modalities[d.modality].name}"
            sales = f"综合分 {d.composite:.1f}  累计销售 {money(d.revenue_total)}"
            self.say(f"  {d.name}（{combo}）  {sales}  {status}{star}")
        names = c.texts.achievements
        got = [names[k].name for k in s.achievements]
        self.say(f"成就（{len(got)}/{len(names)}）：{'、'.join(got) if got else '还没有'}")

    def menu_save(self) -> None:
        text = self.ask("存到哪个文件？（回车 = save.json）> ") or "save.json"
        try:
            save(self.state, text)
            self.say(f"已存档到 {text}")
        except OSError as e:
            self.say(f"❌ 存档失败：{e}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="新药物语：开罗式的制药经营游戏")
    parser.add_argument("--seed", type=int, help="随机种子（默认随机）")
    parser.add_argument("--load", type=Path, help="读取存档")
    parser.add_argument("--fast", action="store_true", help="揭晓结果时不停顿")
    args = parser.parse_args(argv)
    content = default_content()
    if args.load:
        try:
            state = load(args.load)
        except SaveError as e:
            print(f"❌ {e}")
            sys.exit(1)
    else:
        state = new_game(args.seed if args.seed is not None else random.randrange(1, 1_000_000), content)
    CLI(state, content, delay=0 if args.fast else 0.4).run()
