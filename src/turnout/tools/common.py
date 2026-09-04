from __future__ import annotations

from datetime import datetime

from turnout import runtime
from turnout.models import Department


def rt():
    return runtime.get()


def dept() -> Department:
    r = rt()
    return r.store.get_department(r.dept_id)


def now() -> datetime:
    return rt().clock.now()


def parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


def in_quiet_hours(hour: int, quiet: tuple[int, int]) -> bool:
    start, end = quiet
    if start == end:
        return False
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def quiet_hours_end(at: datetime, quiet: tuple[int, int]) -> datetime:
    """The next moment quiet hours end, given `at` is inside them."""
    _, end = quiet
    candidate = at.replace(hour=end, minute=0, second=0, microsecond=0)
    if candidate <= at:
        from datetime import timedelta

        candidate += timedelta(days=1)
    return candidate
