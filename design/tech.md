# 当前技术方案 · v0.12

## 单一规则引擎

入口为 career：CLI、网页、回放和模拟共用 engine.execute。旧 MVP engine/ui/sim/content 与对应 186 项测试从当前树移除，完整历史保存在已存在的 v0.3.0 tag；没有将删除的测试算成通过。规则重构在独立 checkout、端口、存档完成。

状态版本仍为 8，可读取 v0.8、v0.9 的复制存档；v7 及更早存档明确拒绝，不隐式迁移。v0.10 默认端口 8885、存档 `saves/scene-autosave.json`（与 v0.9 相同，同时运行时给旧版换端口）。execute 深复制、验证、变更；服务先原子存盘再替换内存，保存失败不生效。固定种子与操作记录可重放。快照与预览不改变原状态，不抽新随机数。

## v0.12 的变化

**存档 v10。** `model.MIGRATIONS` 依次把 v8、v9 迁到 v10，只在内存里补字段：`tips_seen`、`chronicle`、项目的 `autopilot` / `pace`、产品的 `history`。`model.resolve_save(path)` 决定读哪个文件、写哪个文件：按「`-v12` → `-v11` → 原文件」找第一个存在的存档，已是 v10 就写回自己，否则新进度写到 `-v12`。网页、CLI、线上多账号都走它，旧文件一个字节都不改。

**会让时间停下的项目。** 统一用 `model.blocking(p)`：待决定、没暂缓、也没交给团队自动推进。`advance`、`next_event`、快照的 `pending` 都用它。

**交给团队。** `start_project(..., autopilot)` 和 `set_autopilot`。`engine.autopilot_step` 在每周的项目循环之后运行，直接调用 `choose_candidate`、`continue_project`、`run_phase`、`launch`；这些函数都先检查后修改，失败时状态不变，只写 `waiting`。候选按 `assist.autopilot_candidate` 选，只看公开信念。方案（`pace`）开工时定下，接手不改变它。

**成长建议。** `guide.suggestions` 只读，进快照 `guide`（最多三条）。带命令的建议用 `guide.blocker` 按引擎的前提条件直接检查，不在副本上试执行（20 年存档复制一次要几毫秒）；`tests/test_guide.py` 用真实引擎核对。`guide.moments` 给引擎用：第一次出现的成长机会记进 `tips_seen` 并发 `growth_ready`，`next_event` 在那一周停下。

**快照新增。** `guide`、`chronicle_count`；项目的 `autopilot`、`pace`、`waiting`；证据的 `gate`、`gate_stage`、`verdict`；结果的 `words`；评级的 `early`、`gap`、`levers`；目录行的 `outlook`、`autopilot`、`share_loss`。`/api/content` 新增 `targets`（疾病卡与主流路线，只给药物类型，不给适配档位）。20 年存档快照约 9–13 毫秒。

**游玩记录。** `--playlog` / `--playlog-dir` 让服务每个操作追加一行 JSON（时间、周、命令、成败、耗时），不进存档；`scripts/playlog-report.py` 汇总。

**场景。** `#sheet` 是手机上的决定面板；成员用 `art.js` 的新画法；`panels.js` 的新项目页分为疾病卡、主流路线、自由组合三层。

## v0.13 的变化

**存档 v11。** `MIGRATIONS[10] = migrate_v10` 补 `year_goal`、`goal_history`、`goal_log`、`fellowships`、`wards`，并把已到原第 3 章及以后的章节下标后移一位（新插入的「新的实验室」算作跳过，不补奖励）。`resolve_save` 的查找顺序是「`-v13` → `-v12` → `-v11` → 原文件」，新进度写 `-v13`。旧文件只读不改。

**新模块。**
- `goals.py`：年度目标。`honors.annual` 在颁奖后调用 `close_year` 和 `offer(year + 1)`；`engine.execute` 每个操作后调用 `goals.update`。出题用 `rand(s, "goals", year)`，只看公开状态。
- `skills.py`：主动技能。九种原语，21 个技能的数据在 `abilities.json` 的 `active`；`use_skill` 先检查后修改，随机都带键。快照的人物 `active`、项目 `skills` 列出能用在哪。
- `gates.py` + `data/challenges.json`：难病搭档关（阿尔茨海默、KRAS G12C、乙肝、Lp(a)）。`science.plan_phase` 用 `gates.effects` 调门槛、噪声、工期；`economy.make_product` 乘 `gates.peak_factor`；立项筛选时 `gates.lock_design` 定下由分子设计决定的关。
- `incidents.py` + `data/incidents.json`：失败事件卡。`engine.finish_phase` 失败时 `incidents.draw` 用 `rand(s, "incident", 项目, 阶段, 补正次数)` 抽原因；`incidents.options` 只读，进快照项目的 `incident`；新命令 `rework_expert`。
- `investments.py`：花钱的出口。命令 `build_line`、`access_program`、`fund_fellowship`、`build_ward`；每周运营费在 `advance` 里记为 `operations`，患者援助在 `market_step` 里记为 `access`。

**专长看得见。** `talents.trigger` 发 `talent_triggered`，同一人、同一专长在同一项目的同一阶段只报一次（`p["talent_seen"]`），人物记 `talent_uses`。`science.skill_effects` 返回 `notes`，开工时发事件。

**快照新增。** `year_goal`；人物 `active`、`talent_uses`；项目 `talents_used`、`skills`、`incident`；目录与项目的 `gates` 带 `title`；产品 `invest`；顶层 `investments`；`facility.slots` 改为实际自营临床席位（含病房和欧阳岚）。

## 公共接口

- GET /api/content：版本化静态内容，客户端启动时读取一次：`rooms`（固定房间表，含每个房间承担的阶段）、`roster`（20 位角色的名字、外号、背景、外观）、`display_scale`（10）、项目、术语、方案和解锁条件文字；不含组合隐藏档位或理由。
- GET /api/state：动态公开状态，api_version=2，revision、token、saved_at。
- POST /api/action：name、args、revision、可选 request_id；必须携带同源与 X-Game-Token。相同 ID 的同一操作返回最新状态、不重复执行；同 ID 不同负载拒绝。缓存最近 256 请求、限当前服务进程，重启 token 改变，不承诺跨重启 exactly-once。
- POST /api/preview：只读预演费用、时间、阶段概率与团队开发贡献。
- GET /api/save：用户主动导出的完整存档，供本地回放/恢复；**含隐藏状态，不属于可向场景展示的公开 DTO**。

`design/api/state-v2.schema.json` 固定顶层、项目键和候选/工作/读数/事件结构，以及 v0.8 新增的 `Hero`（含 `look`、`room`、`activity`）、`Look`、`RoomId`、`Patent`；`scripts/generate-api-types.py` 生成 `web/api-types.d.ts`。历史经营面板字段仍用 JsonValue 兼容，后续逐步收紧，不能称全部嵌套数据已强类型化。Schema 用于回归验证，不在每次本地请求重复校验。

项目解锁判断仍由服务端执行；动态只发判定布尔值，客户端按静态条件文字展示，不复制规则。新局未压缩 JSON：完整快照约 270 KB，动态约 78 KB，另有一次静态内容请求。长期项目档案仍会增长，下一阶段应增加档案分页，不能宣称所有存档固定 78 KB。

## 事件到场景

事件包含 version、递增 id、week、type、actors、project、room、data。v0.8 的事件类型：

| 类型 | 何时 | 场景可以做什么 |
|---|---|---|
| work_completed | 开发批次完成 | 在 actors[0] 头上飘“+21 工艺稳定”（data.amounts 已是点数） |
| evidence_received | 验证批次读数 | 白板加一个点；data.values / limits / margins 为点数 |
| phase_started / phase_finished | 阶段开始与结束 | 人走到工位；data.executor 为 internal 或 cro，CRO 阶段 actors 为空 |
| product_launched / award_won / legacy_reached | 上市、年度奖、终局荣誉 | 全员庆祝 |
| patent_filed / patent_granted / patent_expired | 专利 | 横幅；到期提示销售下滑 |
| milestone_reached | 公司大事记 | 横幅（data.title） |
| facility_upgraded / equipment_upgraded | 搬迁、设备升级 | 新房间或新仪器出现 |
| service_completed / deal_signed / personal_completed / character_promoted | 交付、签约、课题、晋阶 | 小庆祝或收款 |
| cash_changed | 每个改变现金的命令 | data.income / data.expense 按类别给出明细，场景按类别过滤 |
| notice | 其他文字 | 只进日志 |

`room` 一律取自房间表：`room_bio`、`room_chem`、`room_proc`、`room_tox`、`room_clinical`、`room_academy`。阶段事件用阶段所在房间（`STAGES[key].room`），开发事件用负责人的专业房间，课题、带教、培训在共研教室。

动态快照里每位人物带 `room`（当前所在房间，空闲为 null）和 `activity`（make / test / service / study / idle），场景不必再从项目和工作里推算位置。

状态保留最近 96 条事件，公开快照返回最近 32 条，当前动作另返 transition_events。场景保存游标，丢失历史时直接按快照恢复，不从缺失事件猜状态。

## 分批证据

四批噪声 σ√4，取均值后噪声为 σ。阶段终点使用同一批数据，不再抽第二次。中途概率用已观察部分与剩余样本的条件分布估算；初步读数不是最终判定。临床不改变候选本身。授权后的合作方当前仍按阶段返回单次数据，未接入玩家的四批中期 UI。

中途只继续或停止；扩大样本和人群必须预先确定。真实适应性设计需要更完整的预设规则、偏差与错误率控制，本游戏不宣称统计模型足以用于真实临床设计。参考：[FDA Adaptive Designs guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/adaptive-design-clinical-trials-drugs-and-biologics-guidance-industry)。

## 实际场景接口

v0.9 在 DTO v2 中追加 `Project.scene`：`room`、`activity`、`total`、`elapsed`、`executor`、`limits`。当前阶段的真实工期和公开门槛在服务端计算；不读取或暴露候选真值。筛选、专项实验、补正各有自己的时长，不能硬套基础阶段周数；临床外包标记仅针对当前执行阶段。`Hero.signature_value` 的开发贡献使用点数，排程的周数及带教倍率保留原单位。

v0.10 追加三组只读字段，都由服务端从公开状态计算：

- `Project.quick`：等待决定（含已暂缓）的项目的一键方案，`command` / `args` 可直接提交；`roles` 是本阶段需要的专业，`weeks` / `cost` / `chance` 来自在状态副本上用 `engine.execute` 试执行的结果，失败时 `ok=false` 并带引擎的原因。实现在 `career/assist.py`。
- `assist`：`services`（每张未接订单的推荐人选：能力最低的合格空闲伙伴，附原因）、`screen`（三条路线的默认筛选团队）、`idle`（空闲伙伴）。
- `negative_months`：连续几个月月底现金为负；`roster[].weekly_salary`：招募后的每周工资。

`next_event` 新增参数 `batches`：默认 1 保持 v0.7 起逐批停下的节奏，旧操作记录照原样重放；0 跳过开发和读数批次，并在有人空闲时的新订单处、现金转负时停下。网页两个入口与 CLI 的 `next` 使用 0。

快照里的阶段方案估计 `plans` 只给等待开工的项目算，`future_base_cost`、`outlook` 只给未结束的项目算；20 年存档的快照从约 39 毫秒降到约 9 毫秒。

- `/scene`：实际入口。`renderer.js` 只做画面、点击、几何寻路和装饰动画；随机走动不参与引擎种子。只保留明快画风。
- `figures.js`：人物画法，按外观数据画全身、背面、走路、工作和头像；场景、底栏、人物卡、图鉴共用，可在 Node 里加载做绘制检查。
- `panels.js`：右侧面板（决定卡、候选对比、进行中、新项目、技术服务、伙伴、研究所、房间），只读快照、发送已有命令。
- `world.js`：从公开快照投影房间与分工，读数只取当前候选和当前阶段。没有门槛的指标不伪造零线。
- `ui.js`：时钟、提示条、面板路由、人物/项目快捷栏、提示气泡、图鉴、事件游标和房间标签；「调整方案」等表单复用 `app.js`、`projects.js`、`honors.js`。玩家悬停或输入时面板不重画，离开后补上。
- `api-driver.js`：文字和场景共享传输层。串行操作；丢失网络响应最多以同一个 request_id 重试一次；409 载入权威快照且不自动重放旧选择，403 或结果不明时要求重连。存盘失败保留已确认画面，用户可明确重试。
- 首次连接或事件游标回退，按快照恢复且跳过历史动画。动作响应的 transition_events 与最近事件按 id 去重；事件不是游戏状态的唯一来源。

场景将药化/制剂画在同一实验室；第 0 级场地的生物工作借用该室，培训借用临床办公室。场地第 1、2、3 级依次开放专用生物室、共研教室、大会与荣誉室。荣誉室是现有大会/奖杯入口的视觉空间，不是新增收费机制。每种设备各自控制仪器显示，不用合并房间的最高等级替代专业等级。每位负责人最多画两位成员代表，界面明确标注真实人数。

静态资源使用明确白名单，场景不加载示例 sim.js，不加载远端字体或脚本。CSP 限制脚本同源，允许动态布局所需的 style 属性；不允许内联脚本。

## 时间、存盘与原型的关系

默认暂停；连续时钟每次只提交一周，收到并保存结果才排下一次，不补算后台积压时间。玩家选的速度一直保留：未暂缓的待决定项目、弹窗（含年度大会）、隐藏标签页或结果不明的连接期间时钟停住，条件解除后自动继续；游戏结束、操作出错或现金转负时速度归零，需要玩家重新开始。点选面板、重要庆祝不再暂停。手动推进、下一件事与文字入口继续使用同一命令。

保留每个成功动作落盘。原建议的按月存盘并非必要前置项：当前延迟足够支持秒级时钟，逐操作原子保存提供更明确的恢复语义，避免关闭标签页丢失一个月。请求去重仍限当前服务进程；没有承诺跨进程重启恰好一次。

`design/ui-claude` 是保留的离线设计原型，`sim.js` 的同步演示接口不能原封不动换成异步驱动。正式场景复用了几何绘制思路，重写了异步 UI、多人多项目映射、状态恢复及完整操作入口。旧原型的 `cast.js` 仍可由 `design/tools/cast_js.py` 生成；真实场景直接读 `/api/content`，避免维护第二份角色数据。

暂未做全量档案分页、自由房间布局、精灵动画素材、离线推进和网络多人游戏。场景不会把合作方阶段读数编造成四批，也不把授权当成已获批。
