# 新药物语 · 研究所版 v0.8

从街角实验室起步的文字制药经营游戏。用鼠标安排研究与团队，靠仿制药、技术服务或授权维持现金流，培养普通伙伴，挑战创新药和终局科学荣誉。

[当前玩法](design/game-design.md) · [内容与角色](design/content.md) · [技术接口](design/tech.md) · [本版试玩记录](design/v08-playtest.md) · [2.5D 场景原型「一屏研究所」](design/ui-claude/README.md) · [偏写实 2.5D 样图](design/ui-v07/README.md) · [GitHub Releases](https://github.com/LucasYL/drugstory/releases)

## 开始游玩

需要 Python 3.12+ 与 uv：

```bash
git clone https://github.com/LucasYL/drugstory.git
cd drugstory
uv sync --dev
./scripts/run-career.sh
```

打开 **http://127.0.0.1:8884/**。时间由按钮推进，成功操作后自动保存，新公司会先备份原局。

```bash
uv run drugstory-web --port 8884 --seed 42 --save-path saves/institute-autosave.json
uv run drugstory-web --difficulty competition --port 8892 --save-path saves/challenge-v8.json
uv run drugstory-web --load saves/my-v8.json --save-path saves/resumed-v8.json --port 8893
uv run drugstory --scenario foundation --seed 42
```

**v0.8 使用 v8 存档，不直接读取旧版存档。** 8883 的 v7、8881 的 v6 保持原目录和原进度；本版独立运行。服务只监听本机，不会抢占已使用的端口。

## 本版变化

- **钱不再无限膨胀。** 自主产品要付市场与医学事务费用（创新 18%、改良 10%）。创新药通过临床前、改良药通过改良设计时申请核心专利，一年后授权；专利到期后仿制药进场，销售半年内降到三到四成。场地租金上调，设备每级每周有运营费。二十年后创新路线的现金比 v0.7 少四到八成，84 局模拟零破产。
- **后期也会失败。** 同一个候选越开发越难改：每项性质前 60 点开发不打折，超出部分递减。见习团队不受影响；传奇团队做成熟组合的获批率从 84% 降到 75.5%，做高难组合约 42%。
- **中间有更多大事。** 专利申请、授权、到期；21 条公司大事记（第一项专利、六人小队、搬进新场地、累计销售一亿……）；上市、搬迁、授权签约、年度奖都有明确的事件。多数路线最长一段“什么大事都没有”的时间约 1–2 年。
- **数字更有手感。** 证据、门槛、读数、开发量都乘以 10 显示，一批开发是“+21”而不是“+2.1”。规则内部不变。
- **20 位角色重做。** 陈一鸣「夜猫子」、苏小禾「烘焙师」、米可「曲线猫」……每人有外号、背景、招牌能力、个人课题和一份外观数据，给以后的 2.5D 场景直接使用。
- **场景接口 v2。** 固定房间表、人物当前所在房间与活动、外包执行标记、资金变化明细、角色外观；见 [技术接口](design/tech.md)。

仍保留三种授权条款、产品差异、年度评奖、三条终局荣誉，以及开局可选的有限市场竞争模式。首局可从稳压片开始，保留工资和后续验证预算；失败时可以放弃候选，继续经营。

**画面仍是文字经营。** [design/ui-claude](design/ui-claude/README.md) 是可以直接玩的 2.5D 场景原型（示例数据、规则与 v0.8 同构）：代码绘制的一屏研究所、新手引导、伙伴图鉴，下一步接入真实引擎。[design/ui-v07](design/ui-v07/README.md) 的偏写实样图保留作对照。

## 验证与复现

```bash
uv run pytest -q
uv run ruff check .
node --check src/drugstory/career/web/app.js
node --check src/drugstory/career/web/projects.js
node --check src/drugstory/career/web/honors.js
uv run python scripts/generate-api-types.py
uv run python scripts/benchmark-v08.py --seeds 400
uv run python scripts/playtest-v08.py --seeds 6 --jobs 4
uv run python design/tools/cast_js.py   # 改了角色数据后，重新生成原型用的 cast.js
```

所有模拟从新局生成，结果写入忽略的 `.artifacts/`，不读取玩家存档。对照实验与完整经营模拟的口径不同，详见试玩记录。自动策略的结果不等于人类玩家胜率；后期仍缺真正的花钱目标，纯仿制路线的重复内容仍需继续打磨。

想继续玩 v0.7 的局，在独立目录检出 `v0.7.0` tag，用 8883 端口启动（见下方做法）。

旧引擎、旧测试和旧模拟脚本在对应不可移动 tag 中保留。需要旧版时创建独立目录并手动启动，例如：

```bash
git worktree add --detach ../drugstory-v03 v0.3.0
cd ../drugstory-v03
uv sync --dev
uv run drugstory-web --help
```

从对应版本的 README 选择独立端口与存档路径；不要让旧程序打开新版存档。本仓库不自动关闭其他版本服务。
