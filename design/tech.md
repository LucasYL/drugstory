# 技术方案 v1

配合 [game-design.md](game-design.md) 和 [content.md](content.md) 阅读。

## 1. 目标

- MVP 是一个能完整玩一局的文字版
- 核心逻辑和界面完全分开
- 以后加机制（成功率、竞争对手、融资……）不需要推倒重来
- 同一个种子加同样的操作，得到同样的结果：能测试、能复现 bug、能批量模拟

## 2. 技术选型

- **Python 3.12+**：用 uv 管理环境，pytest 测试，ruff 检查格式
- **内容数据用 TOML**：标准库 `tomllib` 就能读，还能写注释，方便你直接改靶点表
- **文字界面**：先用标准库；想好看一点再加 `rich`
- **不用游戏引擎**：MVP 的难点全在规则和数值上，不在画面

## 3. 目录结构

包名暂定 `drugstory`，游戏名定了再改。

```
src/drugstory/
  engine/                 纯逻辑：不读输入、不打印
    state.py              全部可存档的游戏状态（dataclass）
    clock.py              周 / 月 / 年
    rng.py                随机数：从主种子派生出每个系统自己的随机流
    actions.py            玩家能做的所有操作，先校验再修改状态
    events.py             事件队列：通知，以及需要玩家决定的事
    loop.py               step_week()：按固定顺序调用各个系统
    systems/
      teams.py            团队产出、经验、升级
      research.py         研发进度、点数、攻关、隐患
      clinical.py         临床各期与审评：打分、过关、爆雷
      market.py           在售药物的销售与退市
      finance.py          工资、月租、花费、收入、破产判定
      contracts.py        外包
      progression.py      解锁、熟练度、成就、年终、标准提高
    rules/
      combo.py            组合规则（由 design/tools/combo.py 正式化而来）
      scoring.py          打分公式
      naming.py           起名后缀
  content/                TOML 数据：targets、modalities、overrides、contracts、texts、names
  ui/cli/                 文字界面：只读状态，只通过 actions 修改状态
  sim/                    bot 和批量模拟
tests/
design/                   设计文档和设计工具
```

## 4. 主循环

```python
while not state.game_over:
    events = advance_until_blocking(state)   # 一周一周地推进，直到出现需要玩家决定的事件
    ui.show(state, events)
    action = ui.ask(events)
    apply_action(state, action)              # 经过 actions.py 校验
```

- `step_week(state)` 按固定顺序调用各个系统：团队产出 → 研发 → 临床 → 市场 → 外包 → 财务（月底）→ 成长（年底）。顺序固定，结果才是确定的。
- 界面、bot、测试都通过同一套 actions 操作游戏。bot 本质上就是一个不用键盘的玩家。

## 5. 可扩展的关键设计

| 设计 | 带来的好处 |
|---|---|
| 系统按周更新，彼此只通过状态和事件交流 | 新机制就是一个新系统，加进 `step_week` 的顺序表就行 |
| 研发管线是一张阶段列表（数据） | 拆分临床阶段、加成功率判定，只要改数据和判定函数 |
| 过关判定可插拔 | MVP 用"分数过线"，以后换成"分数 → 概率"，接口不变 |
| 统一的事件队列，事件可以带选项 | 事件卡只是一种带选项的事件，界面本来就会处理 |
| 内容全部放在 TOML 里 | 加靶点、分子类型、外包单都不用改代码 |
| 每个系统有自己的随机流 | 加一个新系统不会打乱其他系统的随机序列，旧测试和回放不受影响 |
| 状态里带版本号 | 以后改了存档格式，可以写迁移 |

## 6. 存档与回放

- 整个 `GameState` 序列化成 JSON，包含每个随机流的状态和版本号。
- 每年年底自动存一次，玩家也可以随时手动存。
- 回放：记录"种子 + 操作列表"，可以把一局完整重放出来，用来复现 bug。

## 7. 内容数据格式

```toml
[[targets]]
key = "egfr"
name = "EGFR"
disease = "非小细胞肺癌"
location = "surface"        # secreted / surface / intracellular / nucleic
pocket = "yes"              # yes / hard / no
actions = ["inhibit"]
tissue = "solid_tumor"
unlock_cost = 0
market = 4
trial_cost = 1.0
trial_time = 0.9
difficulty = 0.9
chronic = false
```

```toml
[[modalities]]
key = "small_molecule"
name = "小分子"
enters_cell = true
crosses_bbb = true
pocket = "functional"       # functional / binder / none
actions = ["inhibit", "activate"]
base_weeks = 30
weekly_cost = 5
trial_cost = 1.0
risk = "medium"
route = "oral"
```

加载时做校验：缺字段、取值不合法、引用了不存在的 key，一律直接报错，不让坏数据进游戏。

## 8. 模拟与平衡

先做三种 bot 策略：

- **新手**：总是选已知最好的组合，团队平均分配，不接外包
- **稳健**：优先招毒理和工艺负责人，常接外包，某一期分数偏低就终止
- **激进**：同时开很多项目，专挑大市场

每种策略用 200 个种子各跑满 20 年，看下面这些指标：

| 指标 | 目标 |
|---|---|
| 第一个批文出现在哪一年 | 新手策略的中位数在第 2–3 年 |
| 破产率 | 稳健策略低于 5%，新手策略低于 20% |
| 最强组合的优势 | 期望收益最高的组合，不超过第 5 名的 1.5 倍（没有"无脑最优"） |
| 后期现金 | 第 15 年以后现金不会无限膨胀（花钱的地方够多） |
| 后期分数 | 第 15 年以后不会轻松满分（标准增长够快） |
| 名人堂 | 稳健策略 20 年能进 2–5 个 |

结果输出成 CSV 加一页摘要。每调一轮数值重跑一遍，和上一轮对比。

## 9. 测试

- **规则的单元测试**：组合规则逐条对照 content.md 里的例子，再加打分公式、销售曲线、起名
- **不变量测试**：每推进一周检查一遍，比如现金的变化等于收入减支出，人数不超过场地容量
- **黄金测试**：固定种子跑完整一局，关键数字和保存的快照一致
- **存档测试**："存档 → 读档 → 继续跑"和"不存档直接跑"的结果完全一样

## 10. 里程碑

| 里程碑 | 内容 | 完成的标志 |
|---|---|---|
| M0 | 项目骨架、内容加载和校验、组合规则 | 组合测试全绿，能打印出 content.md 里的组合表 |
| M1 | 团队与研发 | 命令行里能跑完一个项目的研发期 |
| M2 | 临床、审评、上市、经济 | 一个药能从立项一路走到退市 |
| M3 | 文字界面、存档 | 能完整玩一局 20 年 |
| M4 | bot 与平衡模拟 | 跑出第 8 节的指标，并完成一轮调参 |
| M5 | 新手引导、成就、打磨 | 可以交给别人试玩 |
