from __future__ import annotations

from strands import tool

from turnout.tools.common import dept, parse_dt, rt


@tool
def get_weather_alerts(window_start: str, window_end: str) -> list[dict]:
    """Active National Weather Service alerts for this department's zone overlapping a window, with the
    hazard multiplier each applies to expected calls.

    Args:
        window_start: ISO datetime.
        window_end: ISO datetime.
    """
    d = dept()
    alerts = rt().weather.active_alerts(d.weather_zone, parse_dt(window_start), parse_dt(window_end))
    return [a.model_dump(mode="json") for a in alerts]
