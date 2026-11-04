# 当前内容结构 · v0.7

唯一在用内容位于 `src/drugstory/career/data/`，由 `career/content.py` 加载并校验。旧 TOML 组合来源在 v0.3.0 tag 中可追溯，288 个组合的档位与理由已提取，运行时不再依赖旧引擎。

| 文件 | 内容与数量 | 稳定编号示例 |
|---|---|---|
| rules.json | 20 角色、4 开局、5 专业、阶段、方案、基础仿制改良、晋阶 | beaker、pill、optimize、I、g_pressure |
| combinations.json | 24 靶点、12 分子类型、288 适配记录 | egfr、small_molecule |
| abilities.json | 每人一个招牌能力，课题前后两个强度 | beaker，含 asset_id |
| stories.json | 20 个专业问题、故事、搭档专业 | beaker → proc |
| products.json | 9 个仿制/改良产品约束与商业收益 | g_pressure、i_long |

创新项目编号通常为 `n_{target}__{modality}`；保留六个原有别名 n_lung、n_inflammation、n_lipid、n_resistance、n_reset、n_rna。这些别名现在同样代表真实组合，并非额外六个项目。共 297 个立项方向。

角色资源按 `asset_id` 绑定，房间为 room_bio / room_chem / room_tox / room_proc / room_clinical。事件中的 room_lab、room_academy 是可映射的通用工作场所，未来场景适配层可将多个专业工作台映射到同一房间。编号稳定不意味着已经有对应美术。

能力目前按工作贡献、候选线索、排程、带教四类机制区分，专业与适用阶段不同；不能宣称已有 20 套完全不同的交互。普通角色的成长、课题和履历保留价值，高阶招募不删除他们的成果。

奖项、竞争者行为和部分公式仍在 Python；本轮先将直接对应角色、阶段、项目和资源的内容数据化，没有声称所有文字和规则都已外置。

查看完整组合矩阵：`uv run python design/tools/combo.py`。开发工具会展示全表；正常游戏仅展示已研究组合的适配档位与理由。
