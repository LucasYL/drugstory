"""跨系统验证：候选药、临床策略、授权现金流、竞争与开局目标。"""
from dataclasses import replace

import pytest

from drugstory.content import STATS
from drugstory.engine import actions as A
from drugstory.engine import decisions as D
from drugstory.engine.game import new_game
from drugstory.engine.loop import advance
from drugstory.engine.queries import committed_costs
from drugstory.engine.rules.scoring import project_scores
from drugstory.engine.save import from_json, replay, to_json
from drugstory.engine.state import LICENSED, PHASE_REVIEW, RD_REVIEW, Drug, Hazard, PhaseResult, Project, Rival
from drugstory.engine.systems import clinical, licensing, market, research, world
from drugstory.ui.web_server import GameSession
from drugstory.ui.web_view import forecasts, snapshot


def reviewed(s, stage=RD_REVIEW, phase="", value=450):
    p = Project(id=s.new_id(), target="egfr", modality="small_molecule", stage=stage,
                phase=phase, team_ids=[], rd_weeks=27, rd_done=27, milestones_done=4,
                stats={k: float(value) for k in STATS})
    if stage == PHASE_REVIEW:
        p.results = [PhaseResult(k, {stat: 8 for stat in ("efficacy", "safety")}, True, "通过")
                     for k in ("I", "II") if k <= phase]
    s.projects.append(p)
    d = D.add(s, D.RD_END if stage == RD_REVIEW else D.PHASE_RESULT, p.id,
              phase=phase, passed=True, next="II" if phase == "I" else "III")
    return p, d


def sign(s, c, kind="cash", phase=""):
    p, d = reviewed(s, PHASE_REVIEW if phase else RD_REVIEW, phase)
    A.license_project(s, c, decision_id=d.id, kind=kind)
    return p, s.deals[-1]


def test_profiles_create_different_strengths_and_limits(content, fresh):
    p = Project(1, "egfr", "small_molecule", "research", [], 27, stats={k: 0.0 for k in STATS})
    potent = replace(p, profile="potent")
    assert research.project_gain(potent, "efficacy", 100, content) > research.project_gain(p, "efficacy", 100, content)
    assert research.project_gain(potent, "safety", 100, content) < research.project_gain(p, "safety", 100, content)
    p.stats["efficacy"] = potent.stats["efficacy"] = 400
    assert (research.project_gain(potent, "efficacy", 10000, content)
            > research.project_gain(p, "efficacy", 10000, content))
    before = to_json(fresh)
    with pytest.raises(A.ActionError, match="候选药"):
        A.start_project(fresh, content, target="egfr", modality="small_molecule", team_ids=[1], profile="unknown")
    assert to_json(fresh) == before


def test_profile_is_frozen_in_save_and_affects_sales_and_margin(content, fresh):
    pid = A.start_project(fresh, content, target="egfr", modality="small_molecule", team_ids=[1], profile="convenient")
    p = from_json(to_json(fresh)).project(pid)
    assert p.profile == "convenient"
    p.composite = 80
    p.results = [PhaseResult("NDA", {"manufacturability": 6}, True, "通过")]
    assert market.peak_sales(fresh, p, content) == pytest.approx(
        1.18 * market.peak_sales(fresh, replace(p, profile="balanced"), content))
    stable = replace(p, profile="stable")
    assert market.margin(stable, content) == pytest.approx(market.margin(p, content) + .05)


@pytest.mark.parametrize("strategy", ["standard", "focused", "rigorous"])
def test_strategy_preview_matches_committed_cost_and_score_rules(content, fresh, strategy):
    p, d = reviewed(fresh, PHASE_REVIEW, "I", 330)
    option = next(x for x in snapshot(fresh, content)["pending"][0]["strategies"] if x["key"] == strategy)
    A.resolve_phase(fresh, content, decision_id=d.id, choice="continue", strategy=strategy)
    assert p.strategy_chosen and p.clinical_strategy == strategy
    assert p.phase_weeks == option["forecasts"][0]["weeks"]
    assert p.phase_weeks * p.phase_weekly_cost == pytest.approx(option["forecasts"][0]["cost"])
    assert committed_costs(fresh, content) == round(option["remaining_cost"])
    assert project_scores(p, "III", fresh.week, content) == option["forecasts"][1]["scores"]


def test_strategy_tradeoffs_and_no_mid_trial_switch(content, fresh):
    p, d = reviewed(fresh, PHASE_REVIEW, "I", 330)
    A.resolve_phase(fresh, content, decision_id=d.id, choice="continue", strategy="focused")
    normal = replace(p, clinical_strategy="standard")
    assert project_scores(p, "III", 0, content)["efficacy"] == project_scores(normal, "III", 0, content)["efficacy"] + 1
    p.composite = normal.composite = 80
    assert market.peak_sales(fresh, p, content) == .75 * market.peak_sales(fresh, normal, content)
    assert clinical.phase_plan(p, "III", content)[1] > clinical.phase_plan(normal, "III", content)[1]
    p.stage = PHASE_REVIEW
    d = D.add(fresh, D.PHASE_RESULT, p.id, phase="II", passed=True, next="III")
    before = to_json(fresh)
    with pytest.raises(A.ActionError, match="不能中途切换"):
        A.resolve_phase(fresh, content, decision_id=d.id, choice="continue", strategy="rigorous")
    assert to_json(fresh) == before


def test_rigorous_removes_noise_but_does_not_erase_hazards(content, fresh):
    p, _ = reviewed(fresh, PHASE_REVIEW, "II", 330)
    p.clinical_strategy, p.strategy_chosen = "rigorous", True
    p.hazards = [Hazard(id=9, stat="safety", severity=2, text="毒性", phase="III")]
    expected = project_scores(p, "III", 0, content)
    results = [clinical.evaluate_phase(fresh, p, "III", content) for _ in range(10)]
    assert all(r.scores["efficacy"] == expected["efficacy"] for r in results)
    assert all(r.scores["safety"] == expected["safety"] - 2 for r in results)
    assert not forecasts(fresh, p, content)[0]["margin_ok"]


def test_bad_license_offer_is_atomic_and_cannot_sell_empty_work(content, fresh):
    p, d = reviewed(fresh, value=50)
    before = to_json(fresh)
    with pytest.raises(A.ActionError, match="报价要求"):
        A.license_project(fresh, content, decision_id=d.id, kind="cash")
    assert to_json(fresh) == before


def test_license_transfers_budget_and_team_and_only_pays_once(content, fresh):
    p, d = reviewed(fresh)
    p.team_ids = [1, 2]
    for t in fresh.teams:
        t.task, t.task_id = "project", p.id
    offer = licensing.offer(fresh, p, content, "cash")
    before = fresh.cash
    A.license_project(fresh, content, decision_id=d.id, kind="cash")
    assert fresh.cash == before + offer["upfront"]
    assert p.stage == LICENSED and not p.active and not fresh.pending
    assert all(t.idle for t in fresh.teams) and committed_costs(fresh, content) == 0
    after = to_json(fresh)
    with pytest.raises(A.ActionError):
        A.license_project(fresh, content, decision_id=d.id, kind="cash")
    assert to_json(fresh) == after


def test_phase_two_license_releases_clinical_slot_and_keeps_strategy(content, fresh):
    p, d = reviewed(fresh, PHASE_REVIEW, "II")
    p.clinical_strategy, p.strategy_chosen = "focused", True
    waiting, wd = reviewed(fresh)
    A.resolve_rd_end(fresh, content, decision_id=wd.id, choice="proceed")
    assert waiting.stage == "clinical_queue"
    A.license_project(fresh, content, decision_id=d.id, kind="royalty")
    assert waiting.stage == "clinical" and p.clinical_strategy == "focused"
    assert fresh.deals[0].phase == "III"
    assert clinical.operations(fresh, content)["used"] == 1


def test_partner_success_pays_milestone_once_then_royalties_without_player_cost(quiet, fresh):
    p, deal = sign(fresh, quiet)
    before = fresh.cash
    for _ in range(80):
        licensing.step(fresh, quiet)
        market.step(fresh, quiet)
        fresh.week += 1
    assert deal.status == "marketed" and deal.milestone_paid
    assert fresh.income["license_milestones"] == deal.milestone
    assert deal.royalty_total > 0 and fresh.cash == before + deal.milestone + deal.royalty_total
    assert not fresh.drugs and not fresh.pending and p.stage == LICENSED
    assert len(p.results) == 4 and from_json(to_json(fresh)) == fresh


def test_partner_failure_keeps_upfront_but_never_pays_future_amounts(quiet, fresh):
    p, deal = sign(fresh, quiet)
    p.stats["safety"] = 0
    before = fresh.cash
    for _ in range(80):
        licensing.step(fresh, quiet)
        market.step(fresh, quiet)
    assert deal.status == "failed" and fresh.cash == before
    assert deal.drug is None and not deal.milestone_paid and deal.royalty_total == 0


def test_license_terms_exchange_upfront_for_royalty(content, fresh):
    p, _ = reviewed(fresh)
    cash = licensing.offer(fresh, p, content, "cash")
    royalty = licensing.offer(fresh, p, content, "royalty")
    assert cash["upfront"] > royalty["upfront"] and cash["royalty_rate"] < royalty["royalty_rate"]
    assert cash["milestone"] == royalty["milestone"]


def test_competition_changes_market_income_but_not_gate_scores(content, fresh):
    p, _ = reviewed(fresh)
    d = Drug(10, p.id, "测试药", "egfr", "small_molecule", 80, 100, .6, 0, weeks_on_market=30)
    fresh.drugs.append(d)
    before = project_scores(p, "III", 0, content)
    base = market.sharing(fresh, content)["egfr"]
    fresh.rivals = [Rival("r", "竞争公司", "egfr", 0, 288, .8, launched=True)]
    assert market.sharing(fresh, content)["egfr"] > base
    assert project_scores(p, "III", 200, content) == before
    cash = fresh.cash
    market.step(fresh, content)
    assert fresh.cash - cash == round(100 * .6 / 1.8)


def test_rivals_have_advance_notice_and_retire_without_endless_pressure(content, fresh):
    assert all(r.launch_week >= content.balance.competition.first_launch for r in fresh.rivals)
    r = fresh.rivals[0]
    assert r.target in content.balance.start.targets
    fresh.week = r.launch_week
    world.step(fresh, content)
    assert r.launched
    fresh.week = r.retire_week
    world.step(fresh, content)
    assert not r.launched and r.cycle == 1 and r.launch_week > fresh.week
    assert max(world.pressure(fresh, t, content) for t in content.targets) <= content.balance.competition.max_pressure


@pytest.mark.parametrize("scenario", ["independent", "licensing", "platform"])
def test_openings_cash_technology_and_replay_are_deterministic(content, scenario):
    s = new_game(42, content, scenario)
    assert s.cash == content.balance.scenarios[scenario].cash
    assert s.data == content.balance.scenarios[scenario].data
    assert ("peptide" in s.unlocked_modalities) == (scenario == "platform")
    A.start_project(s, content, target="egfr", modality="small_molecule", team_ids=[1, 2], profile="selective")
    advance(s, content, 4)
    reconstructed = replay(s.seed, s.action_log, content, scenario=scenario)
    advance(reconstructed, content, s.week - reconstructed.week)
    assert to_json(reconstructed) == to_json(s)


def test_objective_is_awarded_once_and_does_not_end_game(content, fresh):
    fresh.scenario = "licensing"
    for _ in range(3):
        sign(fresh, content, phase="II")
    assert fresh.objective_completed and not fresh.game_over
    messages = len([m for m in fresh.messages if "公司目标达成" in m.text])
    world.check_objective(fresh, content)
    assert len([m for m in fresh.messages if "公司目标达成" in m.text]) == messages == 1


def test_old_save_load_does_not_create_retroactive_competition(content):
    import json
    raw = json.loads(to_json(new_game(1, content)))
    raw.update(version=2, week=800)
    for k in ("rivals", "world_initialized", "deals", "scenario"):
        raw.pop(k)
    loaded = from_json(json.dumps(raw))
    world.ensure(loaded, content)
    assert loaded.week == 800 and loaded.cash == 4000
    assert all(r.launch_week >= 800 + content.balance.competition.first_launch for r in loaded.rivals)


def test_web_new_scenario_backs_up_old_company_and_rejects_bad_scenario(tmp_path):
    session = GameSession(tmp_path / "save.json")
    original = to_json(session.state)
    with pytest.raises(ValueError):
        session.execute({"revision":0, "name":"new_game", "args":{"seed":42,"scenario":[]}})
    assert to_json(session.state) == original and session.revision == 0
    v = session.execute({"revision":0, "name":"new_game", "args":{"seed":42,"scenario":"platform"}})
    assert v["scenario"] == "platform" and v["cash"] == 3400
    backups = list(tmp_path.glob("save-before-new-*.json"))
    assert len(backups) == 1 and backups[0].read_text() == original


def test_license_quote_accounts_for_visible_competition(content, fresh):
    p, _ = reviewed(fresh)
    original = licensing.offer(fresh, p, content, "cash")
    fresh.rivals = [Rival("r", "竞争公司", "egfr", 0, 288, 1.0, launched=True)]
    competed = licensing.offer(fresh, p, content, "cash")
    assert competed["upfront"] < original["upfront"]
    assert competed["market_share"] == .5
    assert competed["royalty_rate"] == original["royalty_rate"]


def test_rigorous_forecast_can_be_safe_at_the_actual_threshold(content, fresh):
    p, _ = reviewed(fresh, PHASE_REVIEW, "II", 330)
    standard = forecasts(fresh, p, content)[0]
    p.clinical_strategy, p.strategy_chosen = "rigorous", True
    rigorous = forecasts(fresh, p, content)[0]
    assert standard["scores"]["efficacy"] == rigorous["scores"]["efficacy"] == 6
    assert not standard["margin_ok"] and rigorous["margin_ok"]


def test_invalid_profile_ceiling_is_rejected_before_play():
    from drugstory.content import ContentError, load_content
    with pytest.raises(ContentError, match="候选药"):
        load_content(balance_overrides={"profiles.potent.ceilings.efficacy": .1})
