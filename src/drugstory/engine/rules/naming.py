"""给药起名：前缀 + 中缀 + 按真实命名规则的后缀（design/content.md 第 4 节）。"""

from __future__ import annotations

import random

from drugstory.content import Content, Modality, Target


def suggest_name(rng: random.Random, target: Target, modality: Modality, content: Content, taken: set[str]) -> str:
    n = content.texts.naming
    name = ""
    for _ in range(100):
        stem = rng.choice(n.prefixes) + rng.choice(n.middles)
        suffix = modality.suffix or target.sm_suffix
        name = stem + (suffix or rng.choice(n.generic_endings))
        if modality.key == "adc":
            name = f"{name} {rng.choice(n.adc_payloads)}"
        if name not in taken:
            return name
    return f"{name}-{len(taken) + 1}"
