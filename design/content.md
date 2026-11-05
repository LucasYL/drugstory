# 当前内容结构 · v0.9

唯一在用内容位于 `src/drugstory/career/data/`，由 `career/content.py` 加载并校验。旧 TOML 组合来源在 v0.3.0 tag 中可追溯，288 个组合的档位与理由已提取，运行时不再依赖旧引擎。

| 文件 | 内容与数量 | 稳定编号示例 |
|---|---|---|
| rules.json | 20 角色（名字、外号、背景、外观）、4 开局、5 专业、阶段（含所在房间）、房间表、方案、基础仿制改良、晋阶、销售费用、专利 | beaker、pill、optimize、I、g_pressure、room_tox |
| combinations.json | 24 靶点、12 分子类型、288 适配记录 | egfr、small_molecule |
| abilities.json | 每人一个招牌能力，课题前后两个强度 | beaker，含 asset_id |
| stories.json | 20 个专业问题、故事、搭档专业 | beaker → proc |
| products.json | 9 个仿制/改良产品约束与商业收益 | g_pressure、i_long |

创新项目编号通常为 `n_{target}__{modality}`；保留六个原有别名 n_lung、n_inflammation、n_lipid、n_resistance、n_reset、n_rna。这些别名现在同样代表真实组合，并非额外六个项目。共 297 个立项方向。

角色资源按 `asset_id` 绑定。房间表固定为 room_bio、room_chem、room_proc、room_tox、room_clinical、room_academy 六间，每个阶段在 rules.json 里写明所在房间；事件里不再出现 room_lab。实际场景把药化和制剂合并；场地升级依次开放生物室、共研教室、大会与荣誉室。大会与荣誉室是展示空间，不增加引擎专业编号。未扩建时，生物和培训工作使用共享实验室或办公室，不限制原有玩法。

## 角色

| 专业 | 见习 | 精英 | 大师 | 传奇 |
|---|---|---|---|---|
| 生物与转化 | 许知夏「反例笔记」 | 顾远航「岩点猎人」 | 沈墨言「两栖医生」 | 叶清和「叶老师」 |
| 药化与分子工程 | 陈一鸣「夜猫子」 | 林巧「左右手」 | 司马衡「魔术师」 | 钟砚秋「老钟」 |
| 药代与毒理 | 唐小柚「再核一遍」 | 雷振东「排雷队长」 | 白若霜「退件女王」 | 孟长青「守门人」 |
| 制剂与工艺 | 苏小禾「烘焙师」 | 江屿「晶体摄影师」 | 傅以宁「一月一针」 | 高铁峰「厂长」 |
| 临床与统计 | 米可「曲线猫」 | 周默「数据侦探」 | 欧阳岚「军师」 | 陆观潮「观潮人」 |

每位角色在 rules.json 里有 `story`（一句话）、`bio`（背景）和 `look`（外观）。`look` 的字段：体型 build、高矮 height、年龄段 age、肤色 skin、发型 hair 与发色 hair_color、是否穿白大褂 coat、上衣 top 与颜色 top_color、裤子 pants、配饰 accessories、配饰颜色 accent、手里的道具 prop、空闲时的小动作 idle。真实场景直接读取 `/api/content` 中的这份数据画人；历史原型在改了角色数据后运行 `uv run python design/tools/cast_js.py` 重新生成原型用的 cast.js。内部编号（beaker、pill……）沿用旧版，存档和代码不受改名影响。

能力目前按工作贡献、候选线索、排程、带教四类机制区分，专业与适用阶段不同；不能宣称已有 20 套完全不同的交互。普通角色的成长、课题和履历保留价值，高阶招募不删除他们的成果。

奖项、竞争者行为和部分公式仍在 Python；本轮先将直接对应角色、阶段、项目和资源的内容数据化，没有声称所有文字和规则都已外置。

查看完整组合矩阵：`uv run python design/tools/combo.py`。开发工具会展示全表；正常游戏仅展示已研究组合的适配档位与理由。
