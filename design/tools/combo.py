"""用引擎的组合规则生成 design/content.md 的 3.3、3.4 节。

    uv run python design/tools/combo.py           # 打印 Markdown，贴进 content.md 的生成区
    uv run python design/tools/combo.py --write   # 直接改写 content.md 的生成区
    uv run python design/tools/combo.py grid      # 打印数字矩阵（-2..2），方便检查

规则在 src/drugstory/engine/rules/combo.py，数据在 src/drugstory/content/*.toml。
tests/test_combo.py 会检查 content.md 和这里的输出一致。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from drugstory.content import default_content  # noqa: E402
from drugstory.engine.rules.combo import compat, markdown_tables  # noqa: E402

BEGIN = "<!-- BEGIN combo.py 生成，不要手改 -->\n"
END = "<!-- END combo.py -->"
CONTENT_MD = ROOT / "design" / "content.md"


def generated_block() -> str:
    return "\n" + markdown_tables(default_content()) + "\n"


def write() -> None:
    text = CONTENT_MD.read_text(encoding="utf-8")
    start, end = text.index(BEGIN) + len(BEGIN), text.index(END)
    CONTENT_MD.write_text(text[:start] + generated_block() + text[end:], encoding="utf-8")


def grid() -> None:
    content = default_content()
    print("target".ljust(14) + "".join(m.key[:6].rjust(8) for m in content.modalities.values()))
    for t in content.targets.values():
        print(t.key.ljust(14) + "".join(str(compat(t, m, content)[0]).rjust(8) for m in content.modalities.values()))


if __name__ == "__main__":
    if "grid" in sys.argv[1:]:
        grid()
    elif "--write" in sys.argv[1:]:
        write()
    else:
        print(markdown_tables(default_content()))
