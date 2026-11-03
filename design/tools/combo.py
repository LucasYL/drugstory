"""组合规则原型：按靶点和分子类型的科学标签算出组合档位。

规则说明见 design/content.md 第 3 节。改了标签或规则以后运行：

    python design/tools/combo.py          # 打印 content.md 3.3、3.4 节的 Markdown
    python design/tools/combo.py grid     # 打印数字矩阵（-2..2），方便检查

这是给设计评审用的原型，正式代码会在引擎里重写。
"""
from dataclasses import dataclass, field

TIERS = {2: "绝配", 1: "好", 0: "一般", -1: "差", -2: "很差"}
TISSUE_CN = {"liver": "肝脏", "cns": "中枢", "solid_tumor": "实体瘤", "blood": "血液肿瘤", "immune": "免疫细胞", "systemic": "全身"}


@dataclass
class Target:
    key: str
    name: str
    location: str  # secreted / surface / intracellular / nucleic
    pocket: str  # yes / hard / no
    actions: set
    tissue: str


@dataclass
class Modality:
    key: str
    name: str
    enters_cell: bool
    crosses_bbb: bool
    pocket: str  # functional / binder / none
    actions: set
    requires_surface: bool = False
    nucleic: bool = False  # can act at gene / RNA level
    delivery: set | None = None  # reachable tissues; None = anywhere it can bind
    prefers: set = field(default_factory=set)


T = [
    Target("pd1", "PD-1", "surface", "no", {"inhibit"}, "immune"),
    Target("her2", "HER2", "surface", "yes", {"inhibit", "deplete"}, "solid_tumor"),
    Target("egfr", "EGFR", "surface", "yes", {"inhibit"}, "solid_tumor"),
    Target("kras", "KRAS G12C", "intracellular", "hard", {"inhibit"}, "solid_tumor"),
    Target("btk", "BTK", "intracellular", "yes", {"inhibit"}, "blood"),
    Target("parp", "PARP", "intracellular", "yes", {"inhibit"}, "solid_tumor"),
    Target("cd19", "CD19", "surface", "no", {"deplete"}, "blood"),
    Target("bcma", "BCMA", "surface", "no", {"deplete"}, "blood"),
    Target("trop2", "TROP2", "surface", "no", {"deplete"}, "solid_tumor"),
    Target("cldn", "Claudin 18.2", "surface", "no", {"deplete"}, "solid_tumor"),
    Target("glp1", "GLP-1 受体", "surface", "hard", {"activate"}, "systemic"),
    Target("pcsk9", "PCSK9", "secreted", "hard", {"inhibit"}, "liver"),
    Target("lpa", "Lp(a)", "secreted", "hard", {"inhibit"}, "liver"),
    Target("abeta", "β-淀粉样蛋白", "secreted", "no", {"deplete"}, "cns"),
    Target("cgrp", "CGRP", "secreted", "yes", {"inhibit"}, "systemic"),
    Target("smn", "SMN", "nucleic", "no", {"restore"}, "cns"),
    Target("tnf", "TNF-α", "secreted", "no", {"inhibit"}, "systemic"),
    Target("il23", "IL-23", "secreted", "no", {"inhibit"}, "systemic"),
    Target("jak", "JAK", "intracellular", "yes", {"inhibit"}, "immune"),
    Target("il4r", "IL-4Rα", "surface", "no", {"inhibit"}, "immune"),
    Target("ttr", "TTR", "secreted", "yes", {"inhibit"}, "liver"),
    Target("resp", "呼吸道病毒", "surface", "no", {"immunize", "inhibit"}, "systemic"),
    Target("hiv", "HIV", "intracellular", "yes", {"inhibit"}, "immune"),
    Target("hbv", "乙肝病毒", "intracellular", "yes", {"inhibit"}, "liver"),
]

M = [
    Modality("sm", "小分子", True, True, "functional", {"inhibit", "activate"}),
    Modality("mab", "单抗", False, False, "none", {"inhibit", "deplete"}),
    Modality("bsab", "双抗", False, False, "none", {"inhibit", "deplete"}),
    Modality("adc", "ADC", False, False, "none", {"deplete"}, requires_surface=True, prefers={"solid_tumor"}),
    Modality("pep", "多肽", False, False, "none", {"activate"}),
    Modality("prot", "重组蛋白", False, False, "none", {"restore", "immunize"}),
    Modality("sirna", "siRNA", True, False, "none", {"inhibit"}, nucleic=True, delivery={"liver"}, prefers={"liver"}),
    Modality("aso", "ASO", True, True, "none", {"inhibit", "restore"}, nucleic=True, delivery={"liver", "cns"}, prefers={"liver", "cns"}),
    Modality("mrna", "mRNA", True, False, "none", {"immunize", "restore"}, delivery={"liver"}),
    Modality("cart", "CAR-T", False, False, "none", {"deplete"}, requires_surface=True, prefers={"blood"}),
    Modality("gene", "基因治疗", True, True, "none", {"restore"}, nucleic=True, delivery={"cns", "liver"}),
    Modality("deg", "蛋白降解剂", True, False, "binder", {"inhibit"}),
]

ACTION_CN = {"inhibit": "抑制", "activate": "激活", "deplete": "清除", "restore": "补上缺失的功能", "immunize": "诱导免疫"}

# (靶点, 分子类型): (档位, 原因)——规则管不到的真实特例
OVERRIDES = {
    ("smn", "sm"): (1, "利司扑兰：小分子也能调节 SMN2 的剪接"),
    ("pcsk9", "pep"): (1, "口服大环多肽已经能抑制 PCSK9"),
    ("il23", "pep"): (1, "口服多肽可以阻断 IL-23 受体"),
    ("tnf", "prot"): (1, "受体融合蛋白（依那西普）能中和 TNF-α"),
    ("trop2", "mab"): (-1, "裸抗体杀伤力不够，TROP2 的成功全靠 ADC"),
    ("lpa", "mab"): (-1, "血液里 Lp(a) 颗粒太多，抗体压不住"),
    ("resp", "mab"): (1, "能中和病毒，但变异株容易逃逸"),
    ("kras", "deg"): (0, "降解剂能打，但还在早期，风险很高"),
    ("pd1", "bsab"): (1, "PD-1/VEGF、PD-1/CTLA-4 双抗：一次打两条通路"),
    ("egfr", "bsab"): (1, "EGFR/MET 双抗（埃万妥单抗）"),
    ("glp1", "prot"): (1, "GLP-1 融合蛋白（度拉糖肽），一周一针"),
    ("abeta", "mab"): (0, "能清除斑块，但入脑的量很少，还有脑水肿风险（仑卡奈单抗、多奈单抗）"),
}


def compat(t: Target, m: Modality):
    if (t.key, m.key) in OVERRIDES:
        return OVERRIDES[(t.key, m.key)]
    if m.requires_surface and t.location != "surface":
        return -2, f"{m.name}需要细胞表面的靶点"
    if t.location == "intracellular" and not m.enters_cell:
        return -2, f"{m.name}进不了细胞"
    if t.location == "nucleic" and not m.nucleic:
        return -2, f"{m.name}作用不到基因层面"
    if m.pocket == "functional" and t.pocket == "no":
        return -2, "没有能结合的口袋"
    if m.key == "deg" and t.location == "secreted":
        return -2, "降解剂对付不了分泌到细胞外的蛋白"

    score, why = 0, []
    if m.key == "bsab" and t.actions & m.actions and "deplete" not in t.actions:
        why.append("双抗能打，但单个靶点用不上第二条臂")
    elif m.key == "deg" and t.actions & m.actions and t.pocket != "hard":
        why.append("已经有好用的抑制剂，降解剂优势不大")
    elif t.actions & m.actions:
        score += 1
        why.append(f"{m.name}擅长{'/'.join(ACTION_CN[a] for a in t.actions & m.actions)}")
    else:
        score -= 1
        why.append(f"{m.name}不擅长{'/'.join(ACTION_CN[a] for a in t.actions)}")
    # 各分子类型的主场
    if m.key == "sm" and t.pocket == "yes":
        score += 1
        why.append("有现成的口袋")
    if m.key == "mab" and t.location in ("surface", "secreted") and t.pocket == "no" and "inhibit" in t.actions:
        score += 1
        why.append("细胞外、没有口袋的靶点正是抗体的主场")
    if m.key == "bsab" and "deplete" in t.actions and t.tissue == "blood":
        score += 1
        why.append("拉来 T 细胞杀血液肿瘤")
    if m.key == "pep" and "activate" in t.actions and t.location == "surface":
        score += 1
        why.append("多肽激动受体是强项")
    if m.key == "mrna" and "immunize" in t.actions:
        score += 1
        why.append("mRNA 疫苗是强项")
    if m.key == "gene" and t.location == "nucleic" and "restore" in t.actions:
        score += 1
        why.append("直接补上缺失的基因")
    if m.key == "deg" and t.location != "intracellular":
        score -= 1
        why.append("降解剂主要对付细胞内的蛋白")
    if m.pocket == "functional" and t.pocket == "hard":
        score -= 1
        why.append("口袋很难做")
    if m.pocket == "binder" and t.pocket == "no":
        score -= 1
        why.append("先得找到能结合它的分子")
    # 组织与递送
    if t.tissue == "cns" and not m.crosses_bbb:
        score -= 2
        why.append("过不了血脑屏障")
    elif m.delivery is not None and t.tissue not in m.delivery and "immunize" not in (t.actions & m.actions):
        score -= 2
        why.append(f"很难送到{TISSUE_CN.get(t.tissue, t.tissue)}")
    if t.tissue in m.prefers:
        score += 1
        why.append(f"很适合{TISSUE_CN[t.tissue]}")
    if m.key == "cart" and t.tissue == "solid_tumor":
        score -= 2
        why.append("实体瘤里 CAR-T 很难发挥")
    return max(-2, min(2, score)), "；".join(why)


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "markdown"
    if mode == "grid":
        print("target".ljust(14) + "".join(m.key.rjust(6) for m in M))
        for t in T:
            print(t.key.ljust(14) + "".join(str(compat(t, m)[0]).rjust(6) for m in M))
    else:
        print("### 3.3 每个靶点的结果\n")
        print("| 靶点 | 绝配 | 好 | 一般 | 差 | 很差 |")
        print("|---|---|---|---|---|---|")
        for t in T:
            groups = {k: [] for k in TIERS}
            for m in M:
                groups[compat(t, m)[0]].append(m.name)
            print(f"| {t.name} | " + " | ".join("、".join(groups[k]) or "—" for k in (2, 1, 0, -1, -2)) + " |")
        start_t = [t for t in T if t.key in ("egfr", "pd1", "tnf", "jak")]
        start_m = [m for m in M if m.key in ("sm", "mab")]
        print("\n### 3.4 开局能做的 4 × 2\n")
        print("| 靶点 | " + " | ".join(m.name for m in start_m) + " |")
        print("|---|" + "---|" * len(start_m))
        for t in start_t:
            cells = []
            for m in start_m:
                tier, why = compat(t, m)
                cells.append(f"{TIERS[tier]}（{why}）")
            print(f"| {t.name} | " + " | ".join(cells) + " |")
