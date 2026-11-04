# 新药物语 · 协作课题版 v0.6

从街角实验室开始的文字制药经营游戏。用鼠标安排研发、培养有专业分工的角色，经营仿制药现金流，挑战改良与创新，选择自主上市或授权合作，最终留下值得记住的科学成果。

[GitHub 仓库](https://github.com/LucasYL/drugstory) · [版本发布](https://github.com/LucasYL/drugstory/releases) · [本版模拟与试玩记录](design/v06-playtest.md) · [2.5D 视觉与交互设计](design/ui-v06/README.md)

## 开始游玩

需要 Python 3.12+ 和 [uv](https://docs.astral.sh/uv/)。

```bash
git clone https://github.com/LucasYL/drugstory.git
cd drugstory
uv sync --dev
./scripts/run-career.sh
```

打开 **http://127.0.0.1:8881/**。时间只在你点击推进时流动，成功操作后自动保存。

```bash
# 自定义端口、种子和独立存档
uv run drugstory-web --port 8881 --seed 42 --save-path saves/projects-autosave.json
# 恢复同版本的导出存档
uv run drugstory-web --load saves/my-v6.json --save-path saves/resumed-v6.json --port 8890
```

新开公司会先备份原局；页面顶部可导出 JSON。服务器只监听本机，占用中的端口会报错退出，不会替换已有服务。

**v0.6 使用 v6 存档，不直接读取 v5 或更早存档。** 请用对应版本继续旧局。现有本地 8877、8878、8879、8880 的服务、代码与存档独立保留；本版位于新的目录，默认使用 `saves/projects-autosave.json`。

终端也使用同一套规则：`uv run drugstory --scenario foundation --seed 42`。输入 `help`、`view`、`next`；默认另存到 `saves/projects-cli.json`。

## 本版新内容与 2.5D 设计

- **20 个个人课题。** 每位伙伴有专业故事与指定搭档专业；选交叉复现或联合交接，完成后永久获得相应协作方法，并抵一项晋阶履历要求。
- **临床中途选择。** I/II/III 期、改良桥接与价值确认各有一个执行检查点。可以维持方案，也可改变随访、中心网络、时间和观察精度；不能靠付钱改变药物自身性质。
- **减少重复点击。** 阶段结果可直接安排下一阶段；一次可核对并安排 1–3 个技术服务订单。
- **可选产业竞逐。** 新公司可选，模式开局后固定。更强对手、有限领域容量和固定平台维护费；可选择节约、常规或精密维护，审批要求不因年份或财富上涨。默认仍是舒展经营。
- **9 个产品特性。** 仿制与改良分别关注供货、均匀性、溶出、储存稳定、小片易服、杂质、长效依从性、耐受与给药便利；强化验证增加投入，取得支持后才带来相应商业效果。

**2.5D 先做设计。** 柔和微缩研究所概念图与可点选的交互样稿在 `design/ui-v06/`。它演示房间导航、人物课题和关键选择，使用示例数据，尚未接入真实存档或人物动画。真实玩法仍在当前文字界面。

```bash
# 独立视觉样稿，建议与游戏同时保留
python -m http.server 8882 --bind 127.0.0.1 --directory design/ui-v06
# 可选挑战开局：使用另一份新存档
uv run drugstory-web --difficulty competition --port 8890 --save-path saves/challenge-v6.json
```

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
node --check src/drugstory/career/web/projects.js
node --check design/ui-v06/concept.js
uv run python scripts/playtest-v06.py --seeds 6 --output .artifacts/v06-first
# 六策略 × 两模式 × 六种子，各运行最多二十年
uv run python scripts/prepare-v06-playtests.py   # 从上述正常操作生成鼠标试玩检查点
```

规则位于 `src/drugstory/career/`。`engine.py` 是网页、终端、模拟共用的事务式入口；`science.py` 管证据，`economy.py` 管经营与成长；`talents.py`、`competition.py`、`honors.py` 管特质、对手与荣誉。预览与读取界面不修改存档；非法操作、过期请求和写盘失败不会提交新状态。

多局模拟及 UI 检查点从新局开始，不注入资金、角色能力或候选质量。自动策略只能衡量可达性与节奏，不能证明真人一定觉得好玩。

- [研发与养成规格](design/growth-redesign.md)
- [v0.4 试玩记录](design/v04-playtest.md)
- [v0.5 设计判断、216 局模拟与鼠标试玩](design/v05-playtest.md)
- [v0.6 多路线模拟、协作与临床决策](design/v06-playtest.md)
- [微缩研究所设计、素材与分步实现方案](design/ui-v06/README.md)
- [版本历史](CHANGELOG.md)
- [发布与存档保护约定](AGENTS.md)

这是压缩时间尺度的经营游戏。概率、市场、角色和「星火生命科学大奖」均为游戏设定；最高奖是虚构的诺贝尔级挑战。竞争者采用不同风格的管线模拟，尚不是拥有完整财务和人才系统的公司 AI。复杂仿制药、生物类似药及完整监管细节尚未建模。
