"""编年史：研究所二十年里的大事，按时间记下，供任期回顾使用。

事件列表只保留最近 96 条、日志 600 条，都不够回看一整个任期；这里单独记一份精简的大事。
只记已经发生的公开结果，不读候选真值，不抽随机数。
"""

LIMIT = 400


def add(s, kind: str, text: str, actors=(), week=None):
    s.setdefault("chronicle", []).append(
        {"week": s["week"] if week is None else week, "kind": kind, "text": text, "actors": list(actors)}
    )
    if len(s["chronicle"]) > LIMIT:
        del s["chronicle"][: len(s["chronicle"]) - LIMIT]
