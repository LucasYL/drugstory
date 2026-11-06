# 当前技术方案 · v0.10

## 单一规则引擎

入口为 career：CLI、网页、回放和模拟共用 engine.execute。旧 MVP engine/ui/sim/content 与对应 186 项测试从当前树移除，完整历史保存在已存在的 v0.3.0 tag；没有将删除的测试算成通过。规则重构在独立 checkout、端口、存档完成。

状态版本仍为 8，可读取 v0.8、v0.9 的复制存档；v7 及更早存档明确拒绝，不隐式迁移。v0.10 默认端口 8885、存档 `saves/scene-autosave.json`（与 v0.9 相同，同时运行时给旧版换端口）。execute 深复制、验证、变更；服务先原子存盘再替换内存，保存失败不生效。固定种子与操作记录可重放。快照与预览不改变原状态，不抽新随机数。

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
