import shutil
from pathlib import Path

import pytest

from drugstory.content import CONTENT_DIR, ContentError, default_content, load_content


def test_default_content_loads():
    c = default_content()
    assert len(c.targets) == 24
    assert len(c.modalities) == 12
    assert len(c.overrides) == 12
    assert len(c.contracts) == 6
    assert c.phase_keys == ["I", "II", "III", "NDA"]
    assert c.facility("center").capacity == 60
    assert c.channel("headhunter").cost == 200


def test_sections_report_the_missing_path():
    c = default_content()
    with pytest.raises(AttributeError, match="balance.scoring 里没有 nope"):
        _ = c.balance.scoring.nope


def test_balance_overrides_change_numbers_without_touching_files():
    c = load_content(balance_overrides={"scoring.yearly_growth": 0.01, "start.cash": 9999})
    assert c.balance.scoring.yearly_growth == 0.01
    assert c.balance.start.cash == 9999
    assert default_content().balance.start.cash != 9999  # 默认内容不受影响
    with pytest.raises(ContentError, match="balance 里没有 scoring.nope"):
        load_content(balance_overrides={"scoring.nope": 1})


@pytest.fixture
def content_copy(tmp_path: Path) -> Path:
    target = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, target, ignore=shutil.ignore_patterns("*.py", "__pycache__"))
    return target


def edit(directory: Path, name: str, old: str, new: str) -> None:
    path = directory / name
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{name} 里找不到要改的内容"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


@pytest.mark.parametrize(
    ("name", "old", "new", "message"),
    [
        ("targets.toml", 'disease = "多种实体瘤"\n', "", "pd1 缺少字段 disease"),
        ("targets.toml", 'location = "surface"', 'location = "space"', "'space' 不在"),
        ("targets.toml", "market = 5", 'market = "big"', "market 类型不对"),
        ("modalities.toml", 'requires_all = [["mab", 2]]', 'requires_all = [["nope", 2]]', "不存在的分子类型 nope"),
        ("modalities.toml", 'pocket = "functional"', 'pocket = "magic"', "'magic' 不在"),
        ("overrides.toml", 'target = "smn"', 'target = "nope"', "不存在的靶点或分子类型"),
        ("balance.toml", 'targets = ["egfr", "pd1", "tnf", "jak"]', 'targets = ["egfr", "nope"]', "nope 不存在"),
        ("balance.toml", "safety = { I = 20,", "safety = { XX = 20,", "不存在的阶段 XX"),
        (
            "balance.toml",
            "manufacturability = { NDA = 100 }",
            "manufacturability = { I = 100 }",
            "没有 manufacturability 专家",
        ),
        ("texts.toml", "[results.rare]", "[results.not_rare]", "缺少 rare 的结果文案"),
    ],
)
def test_bad_content_is_rejected(content_copy, name, old, new, message):
    edit(content_copy, name, old, new)
    with pytest.raises(ContentError, match=message):
        load_content(content_copy)


def test_duplicate_keys_are_rejected(content_copy):
    path = content_copy / "contracts.toml"
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text + '\n[[contracts]]\nkey = "synthesis"\nname = "x"\nattr = "chem"\nrequirement = 1\n'
        "weeks = 1\nreward = 1\ndata = 1\n",
        encoding="utf-8",
    )
    with pytest.raises(ContentError, match="重复的 key：synthesis"):
        load_content(content_copy)
