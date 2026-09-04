"""A clock that can be real or simulated. Every time read in the system goes through this."""

from __future__ import annotations

from datetime import datetime, timedelta


class Clock:
    def __init__(self, start: datetime | None = None) -> None:
        self._simulated = start is not None
        self._now = start or datetime.now()

    @property
    def simulated(self) -> bool:
        return self._simulated

    def now(self) -> datetime:
        return self._now if self._simulated else datetime.now()

    def advance(self, **delta: int) -> datetime:
        if not self._simulated:
            raise RuntimeError("cannot advance a real clock")
        self._now += timedelta(**delta)
        return self._now

    def set(self, dt: datetime) -> None:
        self._simulated = True
        self._now = dt
