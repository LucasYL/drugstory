# 新药物语 · 开发与证据版 v0.7

从街角实验室起步的文字制药经营游戏。用鼠标安排研究与团队，靠仿制药、技术服务或授权维持现金流，培养普通伙伴，挑战创新药和终局科学荣誉。

[当前玩法](design/game-design.md) · [内容与角色](design/content.md) · [技术接口](design/tech.md) · [本版试玩记录](design/v07-playtest.md) · [偏写实 2.5D 原型](design/ui-v07/README.md) · [GitHub Releases](https://github.com/LucasYL/drugstory/releases)

## 开始游玩

需要 Python 3.12+ 与 uv：

```bash
git clone https://github.com/LucasYL/drugstory.git
cd drugstory
uv sync --dev
./scripts/run-career.sh
```

打开 **http://127.0.0.1:8883/**。时间由按钮推进，成功操作后自动保存，新公司会先备份原局。

```bash
uv run drugstory-web --port 8883 --seed 42 --save-path saves/development-autosave.json
uv run drugstory-web --difficulty competition --port 8890 --save-path saves/challenge-v7.json
uv run drugstory-web --load saves/my-v7.json --save-path saves/resumed-v7.json --port 8891
uv run drugstory --scenario foundation --seed 42
```

**v0.7 使用 v7 存档，不直接读取旧版存档。** 8880 的 v5、8881 的 v6 保持原目录和原进度；本版独立运行。服务只监听本机，不会抢占已使用的端口。

## 本版变化

- **开发与验证分开。** 分子优化、处方、质量工艺和改良设计由专业、阶位、成员和设备产生有限开发贡献，分三批呈现。临床只测量，不改善候选。
- **角色培养有可见结果。** 20 位角色、5 个专业、见习到传奇四阶；每人一个招牌能力，个人课题升级它，取代多层小百分比加成。普通角色可以一直成长。
- **恢复创新组合。** 24 个靶点 × 12 种分子类型，按靶点筛选、研究后记入手记。组合影响初始分布，靶点影响要求；仍有 6 个仿制与 3 个改良方案。288 个组合不等于 288 条独立剧情。
- **阶段中途有数据。** 验证阶段四批读数逐步更新证据；临床期中看到前两批后继续或止损。扩大样本、人群选择在开工前确定，不能看完数据再买一次重抽。创新标准路径由 172 周降为 132 周（另加筛选，未计团队提速与额外研究）。
- **给系统做减法。** 移除长期专长、维护档位和生产切换；产品统一委托生产。新增四个专业实验室的有限设备升级，每间最高三级。
- **为场景接口打底。** 结构化工作/证据/晋阶事件，静态内容与动态状态拆开，版本化 JSON Schema 和生成的 TypeScript 类型，动作请求防重复。

仍保留三种授权条款、产品差异、年度评奖、三条终局荣誉，以及开局可选的有限市场竞争模式。首局可从稳压片开始，保留工资和后续验证预算；失败时可以放弃候选，继续经营。

**画面仍是文字经营。** 新的办公室与实验室图是视觉原型，尚未接入角色移动、动画或真实场景点击。旧微缩风格样稿保留为历史设计，不再作为新方向。

## 验证与复现

```bash
uv run pytest -q
uv run ruff check .
node --check src/drugstory/career/web/app.js
node --check src/drugstory/career/web/projects.js
node --check src/drugstory/career/web/honors.js
uv run python scripts/generate-api-types.py
uv run python scripts/benchmark-v07.py --seeds 400
uv run python scripts/playtest-v07.py --seeds 6 --jobs 4
```

所有模拟从新局生成，结果写入忽略的 `.artifacts/`，不读取玩家存档。对照实验与完整经营模拟的口径不同，详见试玩记录。自动策略的结果不等于人类玩家胜率；晚期现金、纯仿制路线的重复内容仍需继续打磨。

旧引擎、旧测试和旧模拟脚本在对应不可移动 tag 中保留。需要旧版时创建独立目录并手动启动，例如：

```bash
git worktree add --detach ../drugstory-v03 v0.3.0
cd ../drugstory-v03
uv sync --dev
uv run drugstory-web --help
```

从对应版本的 README 选择独立端口与存档路径；不要让旧程序打开新版存档。本仓库不自动关闭其他版本服务。
