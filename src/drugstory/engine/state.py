"""全部可存档的游戏状态。

这里只有数据，没有规则。所有字段都是 JSON 能直接表示的类型（int、float、str、bool、list、dict、
嵌套的 dataclass），存档就是把 GameState 整个序列化。唯一的例外是 runtime：运行时缓存（随机数对象），
不参与存档和比较。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from drugstory.content import ATTRS

SAVE_VERSION = 2

# 项目阶段
RESEARCH = "research"  # 研发中
RD_REVIEW = "rd_review"  # 研发结束，等玩家决定
CLINICAL = "clinical"  # 在某一期临床或审评中
QUEUED = "clinical_queue"
PHASE_REVIEW = "phase_review"  # 某一期过关，等玩家决定继续还是终止
NAMING = "naming"  # 审评通过，等玩家起名
APPROVED = "approved"
FAILED = "failed"
TERMINATED = "terminated"
CANCELLED = "cancelled"
ENDED_STAGES = (APPROVED, FAILED, TERMINATED, CANCELLED)
ACTIVE_STAGES = (RESEARCH, RD_REVIEW, QUEUED, CLINICAL, PHASE_REVIEW, NAMING)

# 团队在做什么
IDLE = ""
ON_PROJECT = "project"
ON_CONTRACT = "contract"


@dataclass
class Lead:
    name: str
    bio: int
    chem: int
    tox: int
    proc: int
    leadership: int
    level: int = 1
    exp: int = 0
    profession: str = ""
    secondary: str = ""
    trait: str = ""

    def __post_init__(self) -> None:
        ranked = sorted(ATTRS, key=lambda a: (-self.attr(a), ATTRS.index(a)))
        if not self.profession:
            self.profession = ranked[0]
        if not self.secondary:
            self.secondary = next(a for a in ranked if a != self.profession)
        if not self.trait:
            self.trait = {"bio": "rigorous", "chem": "iterative", "tox": "rigorous", "proc": "frugal"}[self.profession]

    def attr(self, key: str) -> int:
        return getattr(self, key)

    @property
    def specialty(self) -> str:
        """入职时确定的主专业，培养其他属性不会改变职业。"""
        return self.profession


@dataclass
class Team:
    id: int
    lead: Lead
    members: int = 0
    task: str = IDLE
    task_id: int = 0

    @property
    def idle(self) -> bool:
        return self.task == IDLE


@dataclass
class Hazard:
    id: int
    stat: str
    severity: int
    text: str
    phase: str = ""  # 进入临床时分配到哪一期


@dataclass
class PhaseResult:
    phase: str
    scores: dict[str, int]
    passed: bool
    text: str
    hazard_texts: list[str] = field(default_factory=list)


@dataclass
class Project:
    id: int
    target: str
    modality: str
    stage: str
    team_ids: list[int]
    rd_weeks: int
    rd_done: int = 0
    milestones_done: int = 0
    stats: dict[str, float] = field(default_factory=dict)
    hazards: list[Hazard] = field(default_factory=list)
    phase: str = ""
    phase_weeks: int = 0
    phase_weeks_left: int = 0
    phase_weekly_cost: float = 0.0
    results: list[PhaseResult] = field(default_factory=list)
    composite: float = 0.0
    started_week: int = 0
    ended_week: int = -1
    drug_id: int = 0
    spent: int = 0
    base_rd_weeks: int = 0
    extension_count: int = -1  # -1 表示从旧档研发时长推断
    validation_count: int = 0
    validation_weeks_left: int = 0
    clinical_mode: str = "internal"
    queued_week: int = -1

    @property
    def active(self) -> bool:
        return self.stage in ACTIVE_STAGES


@dataclass
class Drug:
    id: int
    project_id: int
    name: str
    target: str
    modality: str
    composite: float
    peak: float
    margin: float
    launched_week: int
    weeks_on_market: int = 0
    active: bool = True
    revenue_total: int = 0
    hall_of_fame: bool = False


@dataclass
class ContractOffer:
    id: int
    kind: str


@dataclass
class ActiveContract:
    id: int
    kind: str
    team_id: int
    weeks_total: int
    weeks_left: int
    reward: int
    data: int


@dataclass
class Recruitment:
    channel: str
    specialty: str
    ready_week: int
    candidates: list[Lead] = field(default_factory=list)


@dataclass
class Decision:
    """一件需要玩家决定的事。种类见 design/tech.md 第 6 节。"""

    id: int
    kind: str
    project_id: int = 0
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class NotebookEntry:
    tier: int
    reason: str
    times: int = 0
    best_composite: float = 0.0


@dataclass
class YearStats:
    year: int
    revenue: int = 0  # 药品销售额（毛收入）
    income: int = 0  # 进账：销售利润 + 外包
    expense: int = 0  # 全部支出
    approvals: int = 0
    failures: int = 0


@dataclass
class Message:
    week: int
    text: str


@dataclass
class LoggedAction:
    week: int
    name: str
    args: dict[str, Any]


@dataclass
class GameState:
    seed: int
    week: int
    cash: int
    data: int
    reputation: float
    facility: str
    teams: list[Team] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    drugs: list[Drug] = field(default_factory=list)
    offers: list[ContractOffer] = field(default_factory=list)
    contracts: list[ActiveContract] = field(default_factory=list)
    recruitment: Recruitment | None = None
    unlocked_targets: list[str] = field(default_factory=list)
    unlocked_modalities: list[str] = field(default_factory=list)
    modality_proficiency: dict[str, int] = field(default_factory=dict)
    target_proficiency: dict[str, int] = field(default_factory=dict)
    notebook: dict[str, NotebookEntry] = field(default_factory=dict)
    achievements: list[str] = field(default_factory=list)
    pending: list[Decision] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)
    years: list[YearStats] = field(default_factory=list)
    income: dict[str, int] = field(default_factory=dict)
    expense: dict[str, int] = field(default_factory=dict)
    negative_months: int = 0
    cash_warned: bool = False
    game_over: bool = False
    career_done: bool = False
    next_id: int = 1
    rng_states: dict[str, list[Any]] = field(default_factory=dict)
    action_log: list[LoggedAction] = field(default_factory=list)
    version: int = SAVE_VERSION
    runtime: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)

    # ---- 查找

    def new_id(self) -> int:
        self.next_id += 1
        return self.next_id - 1

    def team(self, team_id: int) -> Team:
        for t in self.teams:
            if t.id == team_id:
                return t
        raise KeyError(f"没有这个团队：{team_id}")

    def project(self, project_id: int) -> Project:
        for p in self.projects:
            if p.id == project_id:
                return p
        raise KeyError(f"没有这个项目：{project_id}")

    def drug(self, drug_id: int) -> Drug:
        for d in self.drugs:
            if d.id == drug_id:
                return d
        raise KeyError(f"没有这个药：{drug_id}")

    def decision(self, decision_id: int) -> Decision:
        for d in self.pending:
            if d.id == decision_id:
                return d
        raise KeyError(f"没有这件待决定的事：{decision_id}")

    @property
    def current_year(self) -> YearStats:
        return self.years[-1]

    @property
    def headcount(self) -> int:
        return sum(1 + t.members for t in self.teams)

    @property
    def active_projects(self) -> list[Project]:
        return [p for p in self.projects if p.active]

    @property
    def idle_teams(self) -> list[Team]:
        return [t for t in self.teams if t.idle]
