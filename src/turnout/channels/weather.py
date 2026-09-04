"""Weather alerts. Live source is the National Weather Service API (public, no key).

FixtureWeather returns alerts injected by the demo scenario. The landing page states this.
"""

from __future__ import annotations

from datetime import datetime

from turnout.engine.risk import hazard_multiplier
from turnout.models import WeatherAlert


class FixtureWeather:
    def __init__(self, alerts: list[WeatherAlert] | None = None) -> None:
        self.alerts: dict[str, list[WeatherAlert]] = {}
        if alerts:
            self.alerts["*"] = alerts

    def add(self, zone: str, alert: WeatherAlert) -> None:
        self.alerts.setdefault(zone, []).append(alert)

    def active_alerts(self, zone: str, start: datetime, end: datetime) -> list[WeatherAlert]:
        out = self.alerts.get(zone, []) + self.alerts.get("*", [])
        return [a for a in out if a.start < end and a.end > start]


class NwsWeather:
    """Live National Weather Service alerts for a forecast zone, for example TXZ191."""

    def __init__(self, user_agent: str = "turnout (contact: ujwalvanjare6@gmail.com)") -> None:
        import httpx

        self.client = httpx.Client(timeout=8.0, headers={"User-Agent": user_agent, "Accept": "application/geo+json"})

    def active_alerts(self, zone: str, start: datetime, end: datetime) -> list[WeatherAlert]:
        try:
            r = self.client.get(f"https://api.weather.gov/alerts/active/zone/{zone}")
            r.raise_for_status()
        except Exception:
            return []
        out: list[WeatherAlert] = []
        for f in r.json().get("features", []):
            p = f.get("properties", {})
            event = p.get("event", "")
            try:
                s = datetime.fromisoformat(p["onset"].replace("Z", "+00:00")).replace(tzinfo=None)
                e = datetime.fromisoformat(p["ends"].replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                continue
            if s < end and e > start:
                out.append(WeatherAlert(event=event, start=s, end=e, multiplier=hazard_multiplier(event)))
        return out
