# 新药物语（暂定名）

开罗《游戏发展国》式的制药经营游戏。你从一家小 biotech 起步：招募科学家、组建团队，选"靶点 × 分子类型"开发新药，闯过三期临床和上市审评，把公司做成大药厂。

状态：MVP（文字版）可以玩了。

## 怎么玩

需要 [uv](https://docs.astral.sh/uv/)。

```bash
uv sync
uv run drugstory                    # 开始新游戏
uv run drugstory --seed 42          # 指定随机种子（同一个种子，开局一样）
uv run drugstory --load save.json   # 读档；每年年底会自动存到 autosave.json
uv run drugstory --fast             # 揭晓临床结果时不停顿
```

上手提示：

- 第一个项目可以试试 **EGFR × 小分子**，这是个很稳的组合
- 开局只有生物组和化学组，尽快招一个**毒理负责人**（`h`），否则安全性会拖后腿
- **研发要团队，临床不要**：药进了临床，团队就空出来了，可以去开下一个项目
- 现金旁边的"已承诺"是在研项目接下来还要花的钱。别同时压太多临床
- 没钱了就接外包（`c`）；连续 3 个月月底现金为负，公司就破产了
- 游戏里输入 `?` 看全部命令

## 开发

```bash
uv run pytest                                # 全部测试
uv run ruff check .                          # 代码检查
uv run python -m drugstory.sim --runs 50     # 平衡模拟：三种 bot 各跑 50 局
uv run python design/tools/combo.py --write  # 改了靶点或分子类型以后，重新生成 content.md 的组合表
```

## 文档

- [游戏设计](design/game-design.md)：核心循环、各个系统、数值、MVP 范围
- [内容表](design/content.md)：靶点、分子类型、组合规则、文案
- [技术方案](design/tech.md)：架构、约定、存档、模拟结果、里程碑

## 代码结构

```
src/drugstory/
  content/   内容和数值（TOML）：靶点、分子类型、组合特例、外包、文案、balance
  engine/    纯逻辑：状态、各个系统、玩家操作、存档
  ui/        文字界面
  sim/       bot 和批量模拟
tests/
design/      设计文档
```

引擎不读输入、不打印；界面、bot 和测试都通过同一套操作来玩游戏。改数值只需要改 `src/drugstory/content/balance.toml`。
