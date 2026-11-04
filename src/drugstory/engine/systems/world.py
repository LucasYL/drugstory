"""可预见的竞争管线与公司的长期目标；不改变审批门槛。"""
from __future__ import annotations

from drugstory.content import Content
from drugstory.engine import rng
from drugstory.engine.book import say
from drugstory.engine.state import GameState, Rival


def ensure(state: GameState, content: Content) -> None:
    if state.world_initialized:
        return
    b = content.balance.competition
    random_ = rng.stream(state, "competition")
    pool = [t.key for t in content.targets.values() if t.market >= 3]
    for i, name in enumerate(b.companies):
        launch = state.week + b.first_launch + i * 32 + random_.randint(0, 16)
        target_pool = list(content.balance.start.targets) if i == 0 else pool
        state.rivals.append(Rival(key=f"rival-{i}", name=name, target=random_.choice(target_pool),
                                  launch_week=launch, retire_week=launch + b.product_life,
                                  strength=random_.choice([0.6, 0.8, 1.0])))
    state.world_initialized = True


def pressure(state: GameState, target: str, content: Content) -> float:
    return min(content.balance.competition.max_pressure,
               sum(r.strength for r in state.rivals if r.target == target and r.launched
                   and r.launch_week <= state.week < r.retire_week))


def step(state: GameState, content: Content) -> None:
    ensure(state, content)
    b = content.balance.competition
    random_ = rng.stream(state, "competition")
    pool = [t.key for t in content.targets.values() if t.market >= 3]
    for r in state.rivals:
        if state.week >= r.retire_week:
            old = content.targets[r.target].name
            r.target = random_.choice(pool)
            r.launch_week = state.week + b.next_pipeline
            r.retire_week = r.launch_week + b.product_life
            r.launched = False
            r.cycle += 1
            say(state, f"{r.name}的 {old} 产品退出市场；公开新管线 {content.targets[r.target].name}，"
                f"预计 {b.next_pipeline} 周后上市")
        elif state.week >= r.launch_week and not r.launched:
            r.launched = True
            say(state, f"竞争动态：{r.name}的 {content.targets[r.target].name} 产品上市，开始分流同靶点市场")


def objective(state: GameState, content: Content) -> dict:
    scenario = content.balance.scenarios[state.scenario]
    if state.scenario == "licensing":
        metrics = [("已签授权", len(state.deals), 3), ("累计首付款（万）", sum(d.upfront for d in state.deals), 1800)]
    elif state.scenario == "platform":
        metrics = [("已完成外包", state.contracts_completed, 6), ("已掌握分子类型", len(state.unlocked_modalities), 4),
                   ("上市或授权", len(state.drugs) + len(state.deals), 1)]
    else:
        metrics = [("自主上市药品", len(state.drugs), 3), ("覆盖靶点", len({d.target for d in state.drugs}), 2)]
    ready = all(value >= goal for _, value, goal in metrics) and state.cash > 0
    return {"scenario": state.scenario, "name": scenario.name, "description": scenario.objective,
            "metrics": [{"name": name, "value": value, "goal": goal} for name, value, goal in metrics],
            "cash_ok": state.cash > 0, "ready": ready, "completed": state.objective_completed}


def check_objective(state: GameState, content: Content) -> None:
    if not state.objective_completed and objective(state, content)["ready"]:
        state.objective_completed = True
        say(state, f"🏁 公司目标达成：{content.balance.scenarios[state.scenario].name}！可以继续经营挑战二十年总分")
