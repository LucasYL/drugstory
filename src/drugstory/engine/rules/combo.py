"""组合规则：按靶点和分子类型的科学标签算出组合档位和原因。

规则见 design/content.md 3.1 节。各分子类型的特殊情况（主场、例外、扣分）都写在 modalities.toml 里，
这里只有通用的算法。档位：2 绝配 / 1 好 / 0 一般 / -1 差 / -2 很差。
"""

from __future__ import annotations

from drugstory.content import ACTIONS, Content, Modality, Target


def _join_actions(actions: frozenset[str], content: Content) -> str:
    names = content.texts.names.actions
    return "/".join(names[a] for a in ACTIONS if a in actions)


def compat(target: Target, modality: Modality, content: Content) -> tuple[int, str]:
    """返回 (档位, 原因)。原因是给玩家看的一句话，多条理由用"；"连起来。"""
    override = content.overrides.get((target.key, modality.key))
    if override is not None:
        return override.tier, override.reason

    # 硬性不行：直接判"很差"
    if modality.requires_surface and target.location != "surface":
        return -2, f"{modality.name}需要细胞表面的靶点"
    if target.location == "intracellular" and not modality.enters_cell:
        return -2, f"{modality.name}进不了细胞"
    if target.location == "nucleic" and not modality.nucleic:
        return -2, f"{modality.name}作用不到基因层面"
    if modality.pocket == "functional" and target.pocket == "no":
        return -2, "没有能结合的口袋"
    if target.location in modality.blocked_locations:
        return -2, modality.blocked_locations[target.location]

    score, why = 0, []
    tissue_name = content.texts.names.tissues[target.tissue]

    # 干预方式
    shared = target.actions & modality.actions
    condition = modality.action_bonus_when
    if shared and condition is not None and not condition.matches(target):
        why.append(condition.reason)
    elif shared:
        score += 1
        why.append(f"{modality.name}擅长{_join_actions(shared, content)}")
    else:
        score -= 1
        why.append(f"{modality.name}不擅长{_join_actions(target.actions, content)}")

    # 主场
    if modality.sweet_spot is not None and modality.sweet_spot.matches(target):
        score += 1
        why.append(modality.sweet_spot.reason)
    if target.location in modality.location_penalties:
        adjustment = modality.location_penalties[target.location]
        score += adjustment.delta
        why.append(adjustment.reason)

    # 口袋
    if modality.pocket == "functional" and target.pocket == "hard":
        score -= 1
        why.append("口袋很难做")
    if modality.pocket == "binder" and target.pocket == "no":
        score -= 1
        why.append("先得找到能结合它的分子")

    # 组织与递送（做疫苗时不受递送限制）
    if target.tissue == "cns" and not modality.crosses_bbb:
        score -= 2
        why.append("过不了血脑屏障")
    elif modality.delivery and target.tissue not in modality.delivery and "immunize" not in shared:
        score -= 2
        why.append(f"很难送到{tissue_name}")
    if target.tissue in modality.prefers:
        score += 1
        why.append(f"很适合{tissue_name}")
    if target.tissue in modality.tissue_penalties:
        adjustment = modality.tissue_penalties[target.tissue]
        score += adjustment.delta
        why.append(adjustment.reason)

    return max(-2, min(2, score)), "；".join(why)


def tier_name(tier: int, content: Content) -> str:
    return content.texts.names.tiers[str(tier)]


def multiplier(tier: int, content: Content) -> float:
    return content.balance.combo.tier_multipliers[tier + 2]


def markdown_tables(content: Content) -> str:
    """生成 design/content.md 3.3、3.4 节。"""
    lines = ["### 3.3 每个靶点的结果", "", "| 靶点 | 绝配 | 好 | 一般 | 差 | 很差 |", "|---|---|---|---|---|---|"]
    for target in content.targets.values():
        groups: dict[int, list[str]] = {tier: [] for tier in (2, 1, 0, -1, -2)}
        for modality in content.modalities.values():
            groups[compat(target, modality, content)[0]].append(modality.name)
        cells = ["、".join(groups[tier]) or "—" for tier in (2, 1, 0, -1, -2)]
        lines.append(f"| {target.name} | " + " | ".join(cells) + " |")

    start_targets = [t for t in content.targets.values() if t.key in content.balance.start.targets]
    start_modalities = [m for m in content.modalities.values() if m.key in content.balance.start.modalities]
    lines += [
        "",
        f"### 3.4 开局能做的 {len(start_targets)} × {len(start_modalities)}",
        "",
        "| 靶点 | " + " | ".join(m.name for m in start_modalities) + " |",
        "|---|" + "---|" * len(start_modalities),
    ]
    for target in start_targets:
        cells = []
        for modality in start_modalities:
            tier, why = compat(target, modality, content)
            cells.append(f"{tier_name(tier, content)}（{why}）")
        lines.append(f"| {target.name} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"
