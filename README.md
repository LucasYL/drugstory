# 新药物语 · 一屏研究所 v0.9

从街角实验室起步的制药经营游戏。点选房间和伙伴，安排仿制、改良或创新研发；用服务与授权维持现金流，培养普通角色，挑战年度奖项和终局科学荣誉。

**2.5D 场景现在连接真实 Python 引擎。** 文字手记继续可用，两种界面共用当前服务的进度；候选、临床、收入和成长均由引擎计算。

[当前玩法](design/game-design.md) · [内容与角色](design/content.md) · [技术接口](design/tech.md) · [本版试玩与独立复核](design/v09-playtest.md) · [v0.8 平衡记录](design/v08-playtest.md) · [历史场景原型](design/ui-claude/README.md) · [GitHub Releases](https://github.com/LucasYL/drugstory/releases)

## 开始游玩

需要 Python 3.12+ 与 uv：

```bash
git clone https://github.com/LucasYL/drugstory.git
cd drugstory
uv sync --dev
./scripts/run-career.sh
```

打开 **http://127.0.0.1:8885/scene**。文字界面在 **http://127.0.0.1:8885/**。

1. 点「新建研究计划」，首局可从稳压片开始；确认团队、筛选候选。
2. 点房间、人物或项目卡查看详情，右侧做决定；开发前可预览工期、费用和贡献。
3. 时间默认暂停。1× / 2× / 4× 连续推进；待决策、年度大会、弹窗、后台切换和连接错误会暂停。也可以逐周或到下一件事。
4. 橙色飘字是开发贡献，蓝色读数是取得证据。画面不决定成功率。
5. 底部菜单包含全部经营功能。「怎么开始」、动态目标条和伙伴图鉴可随时查看。工资、后续验证和上市都要预留预算。

每次成功操作都自动存盘；刷新恢复后保持暂停。点击「导出存档」备份。重新开公司会先备份当前局。两位小助手是团队成员代表，真实人数以人物卡为准。

```bash
uv run drugstory-web --port 8885 --seed 42 --save-path saves/scene-autosave.json
uv run drugstory-web --difficulty competition --port 8897 --save-path saves/challenge-v9.json
uv run drugstory-web --load saves/my-v8-copy.json --save-path saves/resumed-v9.json --port 8898
uv run drugstory --scenario foundation --seed 42
```

**v0.9 沿用 v8 存档格式，兼容 v0.8。** 如要续玩，先手动复制存档，再用独立路径加载；不要让两个服务同时写同一文件。不会自动迁移、覆盖或推进旧版玩家存档。v7 及更早版本的存档仍需对应版本运行。服务只监听本机。

## 本版变化

- **从演示走向真实经营：** 接入全部研发、授权、角色课题、晋阶、技术服务、产业竞争、年度大会和终局荣誉操作；保留现有文字面板，避免在场景中重新实现规则。
- **持续时间和可靠存档：** 逐周串行请求，保存成功才更新。断线重试使用相同操作编号；结果不明时暂停并提示重新连接。刷新和服务重启按完整快照恢复，不重播旧奖励。
- **看得见的成长：** 角色从公开外观数据绘制，招募与离开即时反映；晋阶加标记、课题与培训有工作状态。扩建逐步开放生物室、共研教室、大会与荣誉室，最多六个房间；四类设备三级升级各有仪器变化。
- **修正显示：** 开发型招牌能力也统一成点数；专项验证显示为「测」；阶段贡献正确标为剩余量。当前阶段的工期、门槛和外包状态来自公开接口。

沿用 v0.8 的开发递减、核心专利、销售费用、设备运营费、20 位角色和公司大事记，**本版没有再次调整经济或成功率**。场景是几何办公室/实验室的可玩版本，尚未制作写实人物素材、复杂动画、自由装修和音效。后期花钱目标、角色课题的分支深度及组合流程差异仍需后续设计。

## 验证与复现

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
node --test tests/test_scene_transport.cjs
uv run python scripts/generate-api-types.py
uv run python scripts/benchmark-v08.py --seeds 400
uv run python scripts/playtest-v08.py --seeds 6 --jobs 4
uv run python scripts/scene-fixtures.py
```

106 项 Python 测试、8 项 Node 测试；另检查全部 JS 语法、Schema/类型同步与关键鼠标路径。独立复核 v0.8 的 84 局二十年经营和 4,000 条受控团队路径；同样 84 局在 v0.9 再跑，指标文件逐字一致，证明本次接入未改变这组策略结果。配对复测不是新增独立样本，自动策略结果不是人类胜率。

所有模拟和 UI 检查只用独立新局，输出在忽略的 `.artifacts/`。记录区分获批、失败、授权、主动终止和仍在研；正常经营与构造边界单测分开，详见 [试玩记录](design/v09-playtest.md)。

## 历史版本

每版保留不可移动 tag 和 Release。需要旧版时另建目录，按对应 README 指定独立端口和存档，不会自动关闭现有服务：

```bash
git worktree add --detach ../drugstory-v08 v0.8.0
cd ../drugstory-v08
uv sync --dev
uv run drugstory-web --port 8884 --save-path saves/v08-autosave.json
```

v0.7 使用 8883，v0.6 使用 8881，v0.5 使用 8880。旧 MVP 引擎与测试可在 v0.3.0 查阅。
