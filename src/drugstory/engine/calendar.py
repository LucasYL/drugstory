"""周编号和"第几年几月第几周"之间的换算。周编号从 0 开始。"""

from __future__ import annotations

from drugstory.content import Content


def year_of(week: int, content: Content) -> int:
    return week // content.balance.time.weeks_per_year + 1


def month_of(week: int, content: Content) -> int:
    t = content.balance.time
    return week % t.weeks_per_year // t.weeks_per_month + 1


def week_in_month(week: int, content: Content) -> int:
    return week % content.balance.time.weeks_per_month + 1


def label(week: int, content: Content) -> str:
    return f"第 {year_of(week, content)} 年 {month_of(week, content)} 月 第 {week_in_month(week, content)} 周"
