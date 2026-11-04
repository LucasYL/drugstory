# 新药物语 · 年度荣誉版 v0.5

从街角实验室开始的文字制药经营游戏。用鼠标安排研发、培养有专业分工的角色，经营仿制药现金流，挑战改良与创新，选择自主上市或授权合作，最终留下值得记住的科学成果。

[GitHub 仓库](https://github.com/LucasYL/drugstory) · [版本发布](https://github.com/LucasYL/drugstory/releases) · [本版模拟与试玩记录](design/v05-playtest.md)

## 开始游玩

需要 Python 3.12+ 和 [uv](https://docs.astral.sh/uv/)。

```bash
git clone https://github.com/LucasYL/drugstory.git
cd drugstory
uv sync --dev
./scripts/run-career.sh
```

打开 **http://127.0.0.1:8880/**。时间只在你点击推进时流动，成功操作后自动保存。

```bash
# 自定义端口、种子和独立存档
uv run drugstory-web --port 8880 --seed 42 --save-path saves/honors-autosave.json
# 恢复同版本的导出存档
uv run drugstory-web --load saves/my-v5.json --save-path saves/resumed-v5.json --port 8881
```

新开公司会先备份原局；页面顶部可导出 JSON。服务器只监听本机，占用中的端口会报错退出，不会替换已有服务。

**v0.5 使用 v5 存档，不直接读取 v4 或更早存档。** 请用对应版本继续旧局。现有本地 8877、8878、8879 的服务、代码与存档独立保留；本版位于新的目录，默认使用 `saves/honors-autosave.json`。

终端也使用同一套规则：`uv run drugstory --scenario foundation --seed 42`。输入 `help`、`view`、`next`；默认另存到 `saves/honors-cli.json`。

## 有什么可以玩

- **20 位角色、5 个专业、4 个阶位。** 烧杯仔、小药丸等普通伙伴能成长为精英、大师和传奇；高阶专家需要公开条件和联合课题。真实项目履历、专业知识、导师带教都影响成长。
- **角色有不同工作方式。** 9 种特质影响费用、观察误差、速度、优化或培养；精英以上可投入 90 万，永久选择深研或组织专长。能力帮助执行和判断，不能把不合格的候选直接变成好药。
- **三条研发路径。** 6 个普通仿制方案、3 个改良方案、6 个创新方向。仿制研究工艺、质量与等效性；改良研究桥接与价值；创新逐步取得临床前、I/II/III 期和审评证据。
- **取舍有后果。** 候选性质固定，研究可能揭示坏消息。定向优化最多两次且有代价；扩大研究改善精度，不保证过关。专业互补、成员效率、工资、临床槽位和生产线都需要安排。
- **经营有多个出口。** 有限技术服务订单、产品导入与换代、自营或委托生产，以及现金优先、长期分成、共同开发三种交易。合作方后续也可能失败，里程碑不是签约即收款。
- **每年有值得准备的大会。** 第 2 年起，每年报名一个方向：品质与供应、育才、转化合作、突破药物。年内第 46 周锁定，48 周年末评选。看真实年度成果，并显示对手分数；重复奖的奖金递减。
- **三条终局荣誉。** 冲击「星火生命科学大奖」，建设「普惠药业桂冠」，或培养「薪火研究院」。最高科学奖需要高难创新药的两轮独立验证，以及从见习培养的传奇、专业大师、带教和年度认可。
- **三家有风格的竞争者。** 规模制造、前沿创新、合作整合各有方向；研发会延迟、失败或调整。已上市产品影响同领域销售与报价，年度成绩影响评奖。相同种子可重现，刷新不能重抽。

首局建议选“起步药坊”，从稳压片入手。用仿制药支持现金流，再补齐专业、培养角色、投入创新。经营满 20 年后仍可继续挑战终局。

## 验证与开发

```bash
uv run pytest -q
uv run ruff check .
node --check src/drugstory/career/web/app.js
node --check src/drugstory/career/web/honors.js
uv run python scripts/playtest-v05.py --seeds 12  # 六种经营策略，各运行最多二十年
uv run python scripts/prepare-v05-playtests.py   # 正常操作生成鼠标试玩检查点
```

规则位于 `src/drugstory/career/`。`engine.py` 是网页、终端、模拟共用的事务式入口；`science.py` 管证据，`economy.py` 管经营与成长；`talents.py`、`competition.py`、`honors.py` 管特质、对手与荣誉。预览与读取界面不修改存档；非法操作、过期请求和写盘失败不会提交新状态。

多局模拟及 UI 检查点从新局开始，不注入资金、角色能力或候选质量。自动策略只能衡量可达性与节奏，不能证明真人一定觉得好玩。

- [研发与养成规格](design/growth-redesign.md)
- [v0.4 试玩记录](design/v04-playtest.md)
- [v0.5 设计判断、216 局模拟与鼠标试玩](design/v05-playtest.md)
- [版本历史](CHANGELOG.md)
- [发布与存档保护约定](AGENTS.md)

这是压缩时间尺度的经营游戏。概率、市场、角色和「星火生命科学大奖」均为游戏设定；最高奖是虚构的诺贝尔级挑战。竞争者采用不同风格的管线模拟，尚不是拥有完整财务和人才系统的公司 AI。复杂仿制药、生物类似药及完整监管细节尚未建模。
