# 当前技术方案 · v0.8

## 单一规则引擎

入口为 career：CLI、网页、回放和模拟共用 engine.execute。旧 MVP engine/ui/sim/content 与对应 186 项测试从当前树移除，完整历史保存在已存在的 v0.3.0 tag；没有将删除的测试算成通过。规则重构在独立 checkout、端口、存档完成。

状态版本 8，旧存档明确拒绝，不隐式迁移；v0.8 默认端口 8884、存档 `saves/institute-autosave.json`。execute 深复制、验证、变更；服务先原子存盘再替换内存，保存失败不生效。固定种子与操作记录可重放。快照与预览不改变原状态，不抽新随机数。

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

## 时间、存盘与下一步

本轮保留按钮推进以及每个成功动作落盘。持续时钟属于场景接入的工作：串行逐周请求、可调速、等待决策/弹窗/隐藏标签页/网络失败自动暂停；以请求编号防重，回包后才能继续。

场景原型 `design/ui-claude` 的驱动层只有三个函数：`tick()`、`act(name, args)`、`view()`。接真实引擎时写一个同接口的驱动调用上述接口即可，渲染和界面代码不用改；原型里的角色数据由 `design/tools/cast_js.py` 从 `career/data` 生成，与引擎同源。Python 引擎继续独立，文字列表始终保留作为快捷操作入口。
