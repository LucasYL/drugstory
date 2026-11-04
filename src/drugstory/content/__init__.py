"""内容与数值：从 TOML 加载，加载时校验。

游戏读取的所有内容（靶点、分子类型、组合特例、外包、文案）和所有可调数值（balance）都在这个目录的
TOML 文件里。加载时就把错误挡在门外：缺字段、取值不合法、引用了不存在的东西，一律报 ContentError。
"""

from __future__ import annotations

import copy
import tomllib
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

CONTENT_DIR = Path(__file__).parent

LOCATIONS = ("secreted", "surface", "intracellular", "nucleic")
POCKETS = ("yes", "hard", "no")
ACTIONS = ("inhibit", "activate", "deplete", "restore", "immunize")
TISSUES = ("systemic", "liver", "cns", "solid_tumor", "blood", "immune")
CATEGORIES = (
    "solid_tumor",
    "heme",
    "metabolic",
    "lipid",
    "neuro",
    "migraine",
    "rare",
    "autoimmune",
    "vaccine",
    "antiviral",
)
POCKET_NEEDS = ("functional", "binder", "none")
RISKS = ("low", "medium", "high")
ROUTES = ("oral", "injection", "infusion", "one_time")

# 负责人的四项属性和药的四项属性一一对应
ATTRS = ("bio", "chem", "tox", "proc")
STATS = ("efficacy", "druggability", "safety", "manufacturability")
ATTR_OF_STAT = dict(zip(STATS, ATTRS, strict=True))
STAT_OF_ATTR = dict(zip(ATTRS, STATS, strict=True))
HAZARD_STATS = ("safety", "druggability", "manufacturability")


class ContentError(ValueError):
    """内容数据有问题。"""


# ---------------------------------------------------------------- 数据类


@dataclass(frozen=True)
class Target:
    key: str
    name: str
    disease: str
    location: str
    pocket: str
    actions: frozenset[str]
    tissue: str
    unlock: int
    market: int
    trial_cost: float
    trial_time: float
    difficulty: float
    chronic: bool
    category: str
    sm_suffix: str
    examples: str


@dataclass(frozen=True)
class Condition:
    """组合规则里的条件：写了的项全部满足才算满足。"""

    location: tuple[str, ...] = ()
    pocket: str = ""
    action: str = ""
    tissue: tuple[str, ...] = ()
    reason: str = ""

    def matches(self, target: Target) -> bool:
        if self.location and target.location not in self.location:
            return False
        if self.pocket and target.pocket != self.pocket:
            return False
        if self.action and self.action not in target.actions:
            return False
        return not (self.tissue and target.tissue not in self.tissue)


@dataclass(frozen=True)
class Adjustment:
    delta: int
    reason: str


@dataclass(frozen=True)
class Modality:
    key: str
    name: str
    enters_cell: bool
    crosses_bbb: bool
    nucleic: bool
    requires_surface: bool
    pocket: str
    actions: frozenset[str]
    delivery: frozenset[str]
    prefers: frozenset[str]
    sweet_spot: Condition | None
    action_bonus_when: Condition | None
    blocked_locations: dict[str, str]
    location_penalties: dict[str, Adjustment]
    tissue_penalties: dict[str, Adjustment]
    base_weeks: int
    weekly_cost: float
    trial_cost: float
    risk: str
    route: str
    route_name: str
    suffix: str
    unlock: int
    requires_all: tuple[tuple[str, int], ...]
    requires_any: tuple[tuple[str, int], ...]
    requires_facility: str


@dataclass(frozen=True)
class Override:
    tier: int
    reason: str


@dataclass(frozen=True)
class Contract:
    key: str
    name: str
    attr: str
    requirement: int
    weeks: int
    reward: float
    data: int


class Section:
    """只读的 TOML 表，可以用属性访问。访问不存在的键时，错误信息里带着完整路径。"""

    __slots__ = ("_data", "_path")

    def __init__(self, data: dict[str, Any], path: str) -> None:
        object.__setattr__(self, "_data", {k: _wrap(v, f"{path}.{k}") for k, v in data.items()})
        object.__setattr__(self, "_path", path)

    def __getattr__(self, name: str) -> Any:
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(f"{self._path} 里没有 {name}") from None

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Section 是只读的")

    def __getitem__(self, key: str) -> Any:
        try:
            return self._data[key]
        except KeyError:
            raise KeyError(f"{self._path} 里没有 {key}") from None

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def __iter__(self):
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def keys(self):
        return self._data.keys()

    def items(self):
        return self._data.items()

    def values(self):
        return self._data.values()

    def __repr__(self) -> str:
        return f"Section({self._path})"


def _wrap(value: Any, path: str) -> Any:
    if isinstance(value, dict):
        return Section(value, path)
    if isinstance(value, list):
        return [_wrap(v, f"{path}[{i}]") for i, v in enumerate(value)]
    return value


@dataclass(frozen=True)
class Content:
    targets: dict[str, Target]
    modalities: dict[str, Modality]
    overrides: dict[tuple[str, str], Override]
    contracts: dict[str, Contract]
    balance: Section
    texts: Section

    def facility(self, key: str) -> Section:
        for f in self.balance.facilities:
            if f.key == key:
                return f
        raise KeyError(f"没有这个场地：{key}")

    def facility_index(self, key: str) -> int:
        return [f.key for f in self.balance.facilities].index(key)

    def phase(self, key: str) -> Section:
        for p in self.balance.phases:
            if p.key == key:
                return p
        raise KeyError(f"没有这个阶段：{key}")

    @property
    def phase_keys(self) -> list[str]:
        return [p.key for p in self.balance.phases]

    def channel(self, key: str) -> Section:
        for c in self.balance.recruiting.channels:
            if c.key == key:
                return c
        raise KeyError(f"没有这个招聘渠道：{key}")


# ---------------------------------------------------------------- 读取与校验


def _read(directory: Path, name: str) -> dict[str, Any]:
    path = directory / name
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        raise ContentError(f"找不到内容文件：{path}") from None
    except tomllib.TOMLDecodeError as e:
        raise ContentError(f"{name} 格式错误：{e}") from None


def _field(d: dict[str, Any], key: str, kind: type | tuple[type, ...], where: str, default: Any = ...) -> Any:
    if key not in d:
        if default is ...:
            raise ContentError(f"{where} 缺少字段 {key}")
        return default
    value = d[key]
    # TOML 里的整数也可以当作小数用
    if kind is float and isinstance(value, int) and not isinstance(value, bool):
        return float(value)
    if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
        raise ContentError(f"{where} 的 {key} 类型不对：{value!r}")
    return value


def _choice(value: str, options: tuple[str, ...], where: str) -> str:
    if value not in options:
        raise ContentError(f"{where} 的取值 {value!r} 不在 {options} 里")
    return value


def _choices(values: list[str], options: tuple[str, ...], where: str) -> frozenset[str]:
    return frozenset(_choice(v, options, where) for v in values)


def _parse_target(d: dict[str, Any]) -> Target:
    where = f"targets.toml 的 {d.get('key', '?')}"
    return Target(
        key=_field(d, "key", str, where),
        name=_field(d, "name", str, where),
        disease=_field(d, "disease", str, where),
        location=_choice(_field(d, "location", str, where), LOCATIONS, where),
        pocket=_choice(_field(d, "pocket", str, where), POCKETS, where),
        actions=_choices(_field(d, "actions", list, where), ACTIONS, where),
        tissue=_choice(_field(d, "tissue", str, where), TISSUES, where),
        unlock=_field(d, "unlock", int, where),
        market=_field(d, "market", int, where),
        trial_cost=_field(d, "trial_cost", float, where),
        trial_time=_field(d, "trial_time", float, where),
        difficulty=_field(d, "difficulty", float, where),
        chronic=_field(d, "chronic", bool, where),
        category=_choice(_field(d, "category", str, where), CATEGORIES, where),
        sm_suffix=_field(d, "sm_suffix", str, where),
        examples=_field(d, "examples", str, where, ""),
    )


def _parse_condition(d: dict[str, Any] | None, where: str) -> Condition | None:
    if d is None:
        return None
    unknown = set(d) - {"location", "pocket", "action", "tissue", "reason"}
    if unknown:
        raise ContentError(f"{where} 有不认识的条件：{sorted(unknown)}")

    def as_tuple(key: str, options: tuple[str, ...]) -> tuple[str, ...]:
        value = d.get(key, ())
        values = [value] if isinstance(value, str) else list(value)
        return tuple(_choice(v, options, where) for v in values)

    return Condition(
        location=as_tuple("location", LOCATIONS),
        pocket=_choice(d["pocket"], POCKETS, where) if "pocket" in d else "",
        action=_choice(d["action"], ACTIONS, where) if "action" in d else "",
        tissue=as_tuple("tissue", TISSUES),
        reason=_field(d, "reason", str, where),
    )


def _parse_adjustments(d: dict[str, Any], options: tuple[str, ...], where: str) -> dict[str, Adjustment]:
    return {
        _choice(k, options, where): Adjustment(_field(v, "delta", int, where), _field(v, "reason", str, where))
        for k, v in d.items()
    }


def _parse_requirements(raw: list[Any], where: str) -> tuple[tuple[str, int], ...]:
    out = []
    for item in raw:
        if not (isinstance(item, list) and len(item) == 2 and isinstance(item[0], str) and isinstance(item[1], int)):
            raise ContentError(f"{where} 的解锁条件要写成 [分子类型, 熟练度]：{item!r}")
        out.append((item[0], item[1]))
    return tuple(out)


def _parse_modality(d: dict[str, Any]) -> Modality:
    where = f"modalities.toml 的 {d.get('key', '?')}"
    blocked = _field(d, "blocked_locations", dict, where, {})
    return Modality(
        key=_field(d, "key", str, where),
        name=_field(d, "name", str, where),
        enters_cell=_field(d, "enters_cell", bool, where),
        crosses_bbb=_field(d, "crosses_bbb", bool, where),
        nucleic=_field(d, "nucleic", bool, where),
        requires_surface=_field(d, "requires_surface", bool, where),
        pocket=_choice(_field(d, "pocket", str, where), POCKET_NEEDS, where),
        actions=_choices(_field(d, "actions", list, where), ACTIONS, where),
        delivery=_choices(_field(d, "delivery", list, where), TISSUES, where),
        prefers=_choices(_field(d, "prefers", list, where), TISSUES, where),
        sweet_spot=_parse_condition(_field(d, "sweet_spot", dict, where, None), f"{where} 的 sweet_spot"),
        action_bonus_when=_parse_condition(
            _field(d, "action_bonus_when", dict, where, None), f"{where} 的 action_bonus_when"
        ),
        blocked_locations={_choice(k, LOCATIONS, where): str(v) for k, v in blocked.items()},
        location_penalties=_parse_adjustments(_field(d, "location_penalties", dict, where, {}), LOCATIONS, where),
        tissue_penalties=_parse_adjustments(_field(d, "tissue_penalties", dict, where, {}), TISSUES, where),
        base_weeks=_field(d, "base_weeks", int, where),
        weekly_cost=_field(d, "weekly_cost", float, where),
        trial_cost=_field(d, "trial_cost", float, where),
        risk=_choice(_field(d, "risk", str, where), RISKS, where),
        route=_choice(_field(d, "route", str, where), ROUTES, where),
        route_name=_field(d, "route_name", str, where),
        suffix=_field(d, "suffix", str, where),
        unlock=_field(d, "unlock", int, where),
        requires_all=_parse_requirements(_field(d, "requires_all", list, where, []), where),
        requires_any=_parse_requirements(_field(d, "requires_any", list, where, []), where),
        requires_facility=_field(d, "requires_facility", str, where, ""),
    )


def _apply_overrides(raw: dict[str, Any], overrides: dict[str, Any]) -> None:
    """按点分路径改数值，比如 {"scoring.yearly_growth": 0.05}。模拟调参时用。"""
    for dotted, value in overrides.items():
        node = raw
        parts = dotted.split(".")
        for part in parts[:-1]:
            if not isinstance(node, dict) or part not in node:
                raise ContentError(f"balance 里没有 {dotted}")
            node = node[part]
        if not isinstance(node, dict) or parts[-1] not in node:
            raise ContentError(f"balance 里没有 {dotted}")
        node[parts[-1]] = value


def _unique(items: list[Any], what: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for item in items:
        if item.key in out:
            raise ContentError(f"{what} 里有重复的 key：{item.key}")
        out[item.key] = item
    return out


def _validate(content: Content) -> None:
    b, t = content.balance, content.texts
    targets, modalities = content.targets, content.modalities
    facility_keys = [f.key for f in b.facilities]

    for m in modalities.values():
        for key, _level in (*m.requires_all, *m.requires_any):
            if key not in modalities:
                raise ContentError(f"{m.key} 的解锁条件引用了不存在的分子类型 {key}")
        if m.requires_facility and m.requires_facility not in facility_keys:
            raise ContentError(f"{m.key} 的解锁条件引用了不存在的场地 {m.requires_facility}")
        if m.risk not in b.research.hazard_rate:
            raise ContentError(f"balance.research.hazard_rate 缺少 {m.risk}")
    for (tk, mk), o in content.overrides.items():
        if tk not in targets or mk not in modalities:
            raise ContentError(f"组合特例引用了不存在的靶点或分子类型：{tk} × {mk}")
        if not -2 <= o.tier <= 2:
            raise ContentError(f"组合特例 {tk} × {mk} 的档位必须在 -2 到 2 之间")
    for c in content.contracts.values():
        _choice(c.attr, ATTRS, f"contracts.toml 的 {c.key}")

    for key in b.start.targets:
        if key not in targets:
            raise ContentError(f"balance.start.targets 里的 {key} 不存在")
    for key in b.start.modalities:
        if key not in modalities:
            raise ContentError(f"balance.start.modalities 里的 {key} 不存在")
    if b.start.facility not in facility_keys:
        raise ContentError(f"balance.start.facility 里的 {b.start.facility} 不存在")
    if len(b.combo.tier_multipliers) != 5:
        raise ContentError("balance.combo.tier_multipliers 必须正好 5 个（很差到绝配）")
    if len(b.market.base_by_tier) != 5:
        raise ContentError("balance.market.base_by_tier 必须正好 5 个（1 到 5 档）")
    phase_keys = [p.key for p in b.phases]
    if len(set(phase_keys)) != len(phase_keys) or not phase_keys:
        raise ContentError("balance.phases 的 key 不能重复，也不能为空")
    for p in b.phases:
        for s in p.experts:
            _choice(s, STATS, f"balance.phases 的 {p.key}")
            if s not in p.standard:
                raise ContentError(f"balance.phases 的 {p.key} 缺少 {s} 的阶段系数")
        for s in p.pass_:
            _choice(s, STATS, f"balance.phases 的 {p.key} 的 pass")
    for stat in HAZARD_STATS:
        weights = b.hazard_phases.get(stat)
        if weights is None:
            raise ContentError(f"balance.hazard_phases 缺少 {stat}")
        for phase_key in weights:
            if phase_key not in phase_keys:
                raise ContentError(f"balance.hazard_phases.{stat} 引用了不存在的阶段 {phase_key}")
            if stat not in content.phase(phase_key).experts:
                raise ContentError(f"{stat} 的隐患不能分到没有 {stat} 专家的阶段 {phase_key}")

    for category in {tg.category for tg in targets.values()}:
        if category not in t.results:
            raise ContentError(f"texts.toml 缺少 {category} 的结果文案")
    for stat in HAZARD_STATS:
        if not t.hazards.general.get(stat):
            raise ContentError(f"texts.toml 缺少 {stat} 的通用隐患")
    for route in ROUTES:
        if route not in t.phase_one.druggability:
            raise ContentError(f"texts.toml 缺少 {route} 的 I 期文案")


def load_content(directory: Path | None = None, balance_overrides: dict[str, Any] | None = None) -> Content:
    directory = directory or CONTENT_DIR
    raw_balance = _read(directory, "balance.toml")
    if balance_overrides:
        raw_balance = copy.deepcopy(raw_balance)
        _apply_overrides(raw_balance, balance_overrides)
    # "pass" 是 Python 关键字，不能当属性名，读进来以后改叫 pass_
    for phase in raw_balance.get("phases", []):
        phase["pass_"] = phase.pop("pass", {})
        phase.setdefault("pass_total", 0)

    targets = _unique([_parse_target(d) for d in _read(directory, "targets.toml").get("targets", [])], "targets")
    modalities = _unique(
        [_parse_modality(d) for d in _read(directory, "modalities.toml").get("modalities", [])], "modalities"
    )
    overrides: dict[tuple[str, str], Override] = {}
    for d in _read(directory, "overrides.toml").get("overrides", []):
        where = f"overrides.toml 的 {d.get('target')} × {d.get('modality')}"
        pair = (_field(d, "target", str, where), _field(d, "modality", str, where))
        if pair in overrides:
            raise ContentError(f"{where} 重复了")
        overrides[pair] = Override(_field(d, "tier", int, where), _field(d, "reason", str, where))
    contracts = _unique(
        [
            Contract(
                key=_field(d, "key", str, "contracts.toml"),
                name=_field(d, "name", str, "contracts.toml"),
                attr=_field(d, "attr", str, "contracts.toml"),
                requirement=_field(d, "requirement", int, "contracts.toml"),
                weeks=_field(d, "weeks", int, "contracts.toml"),
                reward=_field(d, "reward", float, "contracts.toml"),
                data=_field(d, "data", int, "contracts.toml"),
            )
            for d in _read(directory, "contracts.toml").get("contracts", [])
        ],
        "contracts",
    )
    try:
        content = Content(
            targets=targets,
            modalities=modalities,
            overrides=overrides,
            contracts=contracts,
            balance=Section(raw_balance, "balance"),
            texts=Section(_read(directory, "texts.toml"), "texts"),
        )
        _validate(content)
    except (AttributeError, KeyError) as e:
        raise ContentError(f"内容数据缺东西：{e}") from None
    return content


@cache
def default_content() -> Content:
    """游戏默认使用的内容（只加载一次）。"""
    return load_content()
