"""各期结果文案（design/content.md 第 5 节）。"""

from __future__ import annotations

from drugstory.content import Content, Modality, Target
from drugstory.engine.state import Project


def spaced(word: str) -> str:
    """中文后面接英文开头的词时加一个空格：进入 I 期、在 I 期之后。"""
    return f" {word}" if word[:1].isascii() else word


def project_label(project: Project, content: Content) -> str:
    return f"{content.targets[project.target].name} × {content.modalities[project.modality].name}"


def _band(score: int) -> str:
    return "high" if score >= 7 else "mid" if score >= 4 else "low"


def metric(content: Content, category: str, phase_key: str, score: int) -> str:
    """把分数线性换算成这类疾病的指标，比如"客观缓解率 34%"。"""
    m = content.texts.results[category][phase_key]
    value = m.low + (m.high - m.low) * (score - 1) / 9
    return f"{m.label} {value:.{m.decimals}f}{m.unit}"


def phase_text(
    content: Content, target: Target, modality: Modality, phase_key: str, scores: dict[str, int], passed: bool
) -> str:
    t = content.texts
    names = t.names.stats
    if phase_key == "I":
        safety = t.phase_one.safety[_band(scores["safety"])]
        drug = t.phase_one.druggability[modality.route][_band(scores["druggability"])]
        return f"{safety}；{drug.format(hours=6 + 2 * scores['druggability'])}"
    if phase_key == "II":
        text = t.outcomes.II_pass if passed else t.outcomes.II_fail
        return text.format(metric=metric(content, target.category, "II", scores["efficacy"]))
    if phase_key == "III":
        m = metric(content, target.category, "III", scores["efficacy"])
        if passed:
            return t.outcomes.III_pass.format(metric=m)
        line = content.phase("III").pass_
        if scores["efficacy"] < line.get("efficacy", 0):
            return t.outcomes.III_fail_efficacy.format(metric=m)
        return t.outcomes.III_fail_safety.format(metric=m)
    if passed:
        return t.outcomes.NDA_pass
    weakest = min(scores, key=lambda s: scores[s])
    return t.outcomes.NDA_fail.format(total=sum(scores.values()), weakest=names[weakest])


def hazard_text(content: Content, phase_name: str, hazard: str, stat: str, severity: int) -> str:
    return content.texts.outcomes.hazard.format(
        phase=phase_name, hazard=hazard, stat=content.texts.names.stats[stat], severity=severity
    )
