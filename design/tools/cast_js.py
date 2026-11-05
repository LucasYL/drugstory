"""把 v0.8 的角色数据（名字、外号、背景、外观、招牌能力、个人课题）导出给 design/ui-claude 原型用。

改了 src/drugstory/career/data 里的角色以后运行：uv run python design/tools/cast_js.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "src/drugstory/career/data"


def build():
    rules = json.loads((DATA / "rules.json").read_text())
    abilities = json.loads((DATA / "abilities.json").read_text())
    stories = json.loads((DATA / "stories.json").read_text())
    stages = rules["STAGES"]
    stats = rules["STATS"]
    cast = []
    for key, c in rules["ROSTER"].items():
        a = abilities[key]
        if a["kind"] == "work":
            ability = f"在{stages[a['stage']]['name']}多贡献 {a['base'] * 10} 点{stats[a['stat']]}"
        elif a["kind"] == "schedule":
            stage = stages[a["stage"]]["name"] if a["stage"] != "*" else "所有临床阶段"
            ability = f"{stage}工期缩短 {a['base']} 周"
        elif a["kind"] == "screen":
            ability = f"候选筛选多给 {a['base']} 条备选线索"
        else:
            ability = f"带教时学徒多得 {a['base']} 点经验"
        cast.append(
            {
                "id": key,
                "name": c["name"],
                "nickname": c["nickname"],
                "profession": c["profession"],
                "profession_name": rules["PROFESSIONS"][c["profession"]],
                "tier": c["tier"],
                "tier_name": rules["RANKS"][str(c["tier"])],
                "ability": c["ability"],
                "story": c["story"],
                "bio": c["bio"],
                "look": c["look"],
                "signature": {"name": a["name"], "text": ability},
                "quest": stories[key][0],
            }
        )
    return (
        "/* 由 design/tools/cast_js.py 从 src/drugstory/career/data 生成，不要手改。 */\n"
        + "window.DrugstoryCast = "
        + json.dumps(cast, ensure_ascii=False, indent=1)
        + ";\n"
    )


if __name__ == "__main__":
    (ROOT / "design/ui-claude/cast.js").write_text(build())
    print("wrote design/ui-claude/cast.js")
