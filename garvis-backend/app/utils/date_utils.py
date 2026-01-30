from datetime import datetime
from dataclasses import dataclass


def _ordinal(n: int) -> str:
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return f"{n}{ {1:'st', 2:'nd', 3:'rd'}.get(n % 10, 'th') }"


@dataclass(frozen=True)
class DayInfo:
    weekday: str
    day: str
    month: str


def get_day_info(now: datetime | None = None) -> DayInfo:
    if now is None:
        now = datetime.now()

    return DayInfo(
        weekday=now.strftime("%A"),
        day=_ordinal(now.day),
        month=now.strftime("%B"),
    )
