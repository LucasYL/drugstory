import sys
from collections import Counter
from pathlib import Path

import pytest

from drugstory.content import default_content
from drugstory.engine.rules.combo import compat, markdown_tables, multiplier, tier_name

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def content():
    return default_content()


def combo(content, target, modality):
    return compat(content.targets[target], content.modalities[modality], content)


@pytest.mark.parametrize(
    ("target", "modality", "tier", "reason_part"),
    [
        ("pd1", "mab", 2, "抗体的主场"),
        ("egfr", "small_molecule", 2, "有现成的口袋"),
        ("jak", "mab", -2, "单抗进不了细胞"),
        ("tnf", "small_molecule", -2, "没有能结合的口袋"),
        ("trop2", "small_molecule", -2, "没有能结合的口袋"),
        ("tnf", "cart", -2, "CAR-T需要细胞表面的靶点"),
        ("smn", "sirna", -2, "过不了血脑屏障"),
        ("kras", "sirna", -1, "很难送到实体瘤"),
        ("ttr", "degrader", -2, "降解剂对付不了分泌到细胞外的蛋白"),
        ("pcsk9", "sirna", 2, "很适合肝脏"),
        ("cd19", "cart", 2, "很适合血液肿瘤"),
        ("cldn18", "cart", -1, "实体瘤里 CAR-T 很难发挥"),
        ("kras", "small_molecule", 0, "口袋很难做"),
        ("glp1", "peptide", 2, "多肽激动受体是强项"),
        ("glp1", "small_molecule", 0, "口袋很难做"),
        ("smn", "gene_therapy", 2, "直接补上缺失的基因"),
        ("tnf", "bispecific", 0, "用不上第二条臂"),
        ("cd19", "bispecific", 2, "拉来 T 细胞杀血液肿瘤"),
        ("btk", "degrader", 0, "降解剂优势不大"),
        ("her2", "degrader", -1, "降解剂主要对付细胞内的蛋白"),
        ("resp", "mrna", 2, "mRNA 疫苗是强项"),
        ("pd1", "adc", -1, "ADC不擅长抑制"),
    ],
)
def test_rules(content, target, modality, tier, reason_part):
    got_tier, reason = combo(content, target, modality)
    assert got_tier == tier
    assert reason_part in reason


@pytest.mark.parametrize(
    ("target", "modality", "tier"),
    [
        ("smn", "small_molecule", 1),
        ("abeta", "mab", 0),
        ("trop2", "mab", -1),
        ("pd1", "bispecific", 1),
        ("glp1", "protein", 1),
    ],
)
def test_overrides_win(content, target, modality, tier):
    got_tier, reason = combo(content, target, modality)
    assert got_tier == tier
    assert reason == content.overrides[(target, modality)].reason


def test_reasons_list_actions_in_a_fixed_order(content):
    # HER2 既要抑制又要清除，原因里的顺序不能随集合的迭代顺序变化
    assert combo(content, "her2", "mab") == (1, "单抗擅长抑制/清除")


def test_hard_targets_are_left_for_late_game(content):
    best = {t: max(combo(content, t, m)[0] for m in content.modalities) for t in content.targets}
    assert best.pop("kras") == 0
    assert best.pop("abeta") == 0
    assert all(tier == 2 for tier in best.values())


def test_every_starting_target_has_a_perfect_match(content):
    for t in content.balance.start.targets:
        assert any(combo(content, t, m)[0] == 2 for m in content.balance.start.modalities), t


def test_tier_counts_match_content_md(content):
    counts = Counter(combo(content, t, m)[0] for t in content.targets for m in content.modalities)
    assert counts == {2: 32, 1: 22, 0: 21, -1: 79, -2: 134}
    doc = (ROOT / "design" / "content.md").read_text(encoding="utf-8")
    assert "绝配 32、好 22、一般 21、差 79、很差 134" in doc


def test_content_md_is_in_sync_with_the_rules(content):
    sys.path.insert(0, str(ROOT / "design" / "tools"))
    import combo as tool

    doc = (ROOT / "design" / "content.md").read_text(encoding="utf-8")
    assert tool.generated_block() in doc, "规则或数据改了：运行 uv run python design/tools/combo.py --write"
    assert markdown_tables(content).startswith("### 3.3")


def test_names_and_multipliers(content):
    assert tier_name(2, content) == "绝配"
    assert tier_name(-2, content) == "很差"
    assert [multiplier(t, content) for t in (-2, -1, 0, 1, 2)] == [0.4, 0.7, 1.0, 1.2, 1.5]
