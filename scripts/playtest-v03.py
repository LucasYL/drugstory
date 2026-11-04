"""三种开局 × 五种候选药 × 三种临床策略，无资源注入的长局检查。"""
import json
from pathlib import Path

from drugstory.content import default_content
from drugstory.engine.save import save
from drugstory.engine.systems.world import objective
from drugstory.sim.bots import LicensingStudio, PlatformCompany, RoadmapCompany
from drugstory.sim.run import play

root = Path('.artifacts/v03-sim')
root.mkdir(parents=True, exist_ok=True)
c = default_content()
rows = []
for cls in (RoadmapCompany, LicensingStudio, PlatformCompany):
    for profile in c.balance.profiles:
        for strategy, seed in zip(c.balance.clinical_strategies, (1, 7, 42), strict=True):
            bot = cls()
            bot.profile, bot.strategy = profile, strategy
            s = play(seed, bot, c, years=20)
            opening = c.balance.scenarios[s.scenario].cash
            assert s.cash == opening + sum(s.income.values()) - sum(s.expense.values())
            row = dict(scenario=s.scenario, profile=profile, strategy=strategy, seed=seed, week=s.week,
                       bankrupt=s.game_over, approvals=len(s.drugs), licenses=len(s.deals), cash=s.cash,
                       objective=s.objective_completed, goal_progress=objective(s,c)['metrics'],
                       partner_approvals=sum(d.milestone_paid for d in s.deals),
                       royalties=s.income.get('royalties',0),
                       first_approval=min((d.launched_week for d in s.drugs),default=None))
            rows.append(row)
            save(s, root/f'{s.scenario}-{profile}-{strategy}.json')
    recent = [r for r in rows if r['scenario'] == cls.scenario]
    print(json.dumps({'scenario':cls.scenario,'runs':len(recent),'bankrupt':sum(r['bankrupt'] for r in recent),
                      'objectives':sum(r['objective'] for r in recent),'min_cash':min(r['cash'] for r in recent),
                      'min_approvals':min(r['approvals'] for r in recent),
                      'min_licenses':min(r['licenses'] for r in recent)},ensure_ascii=False),flush=True)
(root/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
