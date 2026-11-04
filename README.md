# 新药物语（暂定名）

开罗《游戏发展国》式的制药经营游戏。你从一家小 biotech 起步：招募科学家、组建团队，选"靶点 × 分子类型"开发新药，闯过三期临床和上市审评，把公司做成大药厂。

状态：MVP（文字版）。

## 怎么玩

需要 [uv](https://docs.astral.sh/uv/)。

```bash
uv sync
uv run drugstory                    # 开始新游戏
uv run drugstory --seed 42          # 指定随机种子
uv run drugstory --load save.json   # 读档
```

## 开发

```bash
uv run pytest                                # 全部测试
uv run ruff check .                          # 代码检查
uv run python -m drugstory.sim --runs 100    # 平衡模拟：三种 bot 各跑 100 局
uv run python design/tools/combo.py          # 重新生成 content.md 里的组合表
```

## 文档

- [游戏设计](design/game-design.md)：核心循环、各个系统、数值初稿、MVP 范围
- [内容表](design/content.md)：靶点、分子类型、组合规则、文案
- [技术方案](design/tech.md)：架构、约定、存档、模拟、里程碑

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

引擎不读输入、不打印；界面、bot 和测试都通过同一套操作来玩游戏。
