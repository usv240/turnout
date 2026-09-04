"""FastAPI app: the web app's backend and the public API.

Read endpoints accept a sandbox API key so anyone can call them from their own code. Write
endpoints that drive the demo are open in judge mode, because a judge should not have to sign up
for anything to see the system work.

Run: uvicorn turnout.api.app:app --reload --port 8000
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import Body, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from turnout.api.service import service

SANDBOX_KEY = os.environ.get("TURNOUT_SANDBOX_KEY", "turnout-sandbox-2026")
WEB_DIR = Path(__file__).resolve().parents[3] / "web"

app = FastAPI(
    title="Turnout API",
    version="1.0.0",
    description=(
        "Turnout keeps volunteer fire and EMS departments covered. It finds the hours when nobody "
        "can respond, fills them by asking the right people and the right neighbours, and "
        "interrupts the chief only for the one decision that needs a human.\n\n"
        "Every read endpoint accepts the public sandbox key in an x-api-key header. The demo data "
        "is synthetic: Millbrook, Riverton and Cedar Hollow are fictional departments."
    ),
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def normalize_phone(phone: str | None) -> str | None:
    """Accept a phone number however it arrives in a query string.

    A leading plus decodes as a space in a query string unless the caller percent-encodes it, which
    is an easy thing to get wrong from curl. Rather than returning a confusing empty result, put the
    plus back and drop the punctuation people type.
    """
    if not phone:
        return None
    cleaned = "".join(ch for ch in phone if ch.isdigit())
    return "+" + cleaned if cleaned else None


def check_key(x_api_key: str | None) -> None:
    """The sandbox key is public and printed on the developers page. It exists to show the shape of
    a real deployment, where each department has its own key, not to keep anyone out."""
    if x_api_key and x_api_key != SANDBOX_KEY:
        raise HTTPException(status_code=401, detail={
            "error": "unknown api key",
            "hint": f"the public sandbox key is {SANDBOX_KEY}, or omit the header entirely in judge mode",
        })


@app.get("/api/health", tags=["ops"])
def health() -> dict:
    """Liveness for the status page. Returns the simulated clock so a stuck demo is obvious."""
    s = service.state()
    return {"ok": True, "now": s["now"], "headline": s["headline"],
            "gaps": len(s["gaps"]), "steps_done": sum(1 for x in s["steps"] if x["done"])}


@app.get("/api/state", tags=["read"])
def get_state(x_api_key: str | None = Header(default=None)) -> dict:
    """Everything the Station Board shows: headline, gaps, ledger, members, incidents, interrupts."""
    check_key(x_api_key)
    return service.state()


@app.get("/api/gaps", tags=["read"])
def get_gaps(x_api_key: str | None = Header(default=None)) -> dict:
    """Coverage gaps for the next seven days, each with the numbers behind its risk score."""
    check_key(x_api_key)
    return {"gaps": service.state()["gaps"]}


@app.get("/api/messages", tags=["read"])
def get_messages(phone: str | None = Query(default=None),
                 x_api_key: str | None = Header(default=None)) -> dict:
    """Every text sent and received. Pass a phone number for one thread."""
    check_key(x_api_key)
    return {"messages": service.messages(normalize_phone(phone))}


@app.get("/api/network", tags=["read"])
def get_network(x_api_key: str | None = Header(default=None)) -> dict:
    """The three departments, their mutual aid balances, and every A2A exchange so far."""
    check_key(x_api_key)
    return service.network()


@app.get("/api/crew", tags=["read"])
def get_crew(x_api_key: str | None = Header(default=None)) -> dict:
    """Every member, and everything the agent knows and has done about them.

    A scheduling agent asks real people for hours of their life. This is the accountability side of
    that: how often each member has been asked this week, the cap that stops it, the hours it will
    not text them, every message it sent, and the response history behind the probability it uses
    to choose. Nothing here is a model's opinion.
    """
    check_key(x_api_key)
    return service.crew()


@app.get("/api/trace", tags=["read"])
def get_trace(since: int = Query(default=0),
              x_api_key: str | None = Header(default=None)) -> dict:
    """Agent trace events. Pass the previous `next` value to poll for new ones."""
    check_key(x_api_key)
    return service.trace(since)


@app.post("/api/roster/parse", tags=["onboarding"])
def parse_roster_endpoint(body: dict = Body(...),
                          x_api_key: str | None = Header(default=None)) -> dict:
    """Read a pasted roster and report what was understood, before anything is saved.

    Accepts whatever the chief already has: a group text, a spreadsheet paste, a printed list.
    Lines it could not read come back in `unreadable` rather than being dropped, because a member
    missing from the roster is a member the agent will never ask.

    Body: {"text": "Dana Ortiz (Chief) 555-298-6397
Luis Reyes - driver 555 111 2222"}
    """
    check_key(x_api_key)
    from turnout.onboarding import CREW_PRESETS, parse_roster

    text = body.get("text") or ""
    parsed = parse_roster(text)
    return {
        "members": [m.model_dump(mode="json") for m in parsed.members],
        "unreadable": parsed.unreadable,
        "duplicates": parsed.duplicates,
        "crew_presets": [{"id": k, "label": v["label"],
                          "crew": {r.value: n for r, n in v["crew"].fire.items()}}
                         for k, v in CREW_PRESETS.items()],
    }


@app.post("/api/risk/score", tags=["try it"])
def score_window_endpoint(body: dict = Body(...),
                          x_api_key: str | None = Header(default=None)) -> dict:
    """Score a coverage window with your own people, and see every number behind the answer.

    The demo answers one question about one fictional department. This is the same engine, pointed
    at whatever you actually have. Nothing is stored.

    Body, all optional except `available`:

        {
          "window_start": "2026-09-10T10:00",   the window, defaults to the next weekday at 10:00
          "hours": 4,                            how long, defaults to 4
          "available": [                         who could respond
            {"roles": ["firefighter"], "responds": 0.45},
            {"roles": ["driver_operator", "firefighter"]}
          ],
          "min_crew": {"driver_operator": 1, "firefighter": 2},
          "calls_per_day": 1.6,                  your department's own rate
          "weather": "ice storm warning",        or none
          "time_critical_share": 0.65            share of your calls that cannot wait
        }

    `responds` defaults to 0.32, the middle of the 17 to 47 percent range reported for volunteer
    first responders. If you know your own rate, pass it.
    """
    check_key(x_api_key)
    from datetime import datetime, timedelta

    from turnout.engine.risk import (
        HAZARD_MULTIPLIERS,
        NATIONAL_DOW_PROFILE,
        NATIONAL_HOUR_PROFILE,
        NATIONAL_MONTH_PROFILE,
        PRIOR_MEAN,
        RateModel,
        score_window,
    )
    from turnout.models import Role, WeatherAlert

    try:
        raw = body.get("available") or []
        if not isinstance(raw, list) or not raw:
            raise ValueError("available must be a non-empty list of people who could respond")
        if len(raw) > 60:
            raise ValueError("that is more people than this endpoint will score in one go")

        available: list[tuple[set[Role], float]] = []
        for i, person in enumerate(raw):
            roles = {Role(r) for r in (person.get("roles") or ["firefighter"])}
            p = float(person.get("responds", PRIOR_MEAN))
            if not 0.0 <= p <= 1.0:
                raise ValueError(f"person {i}: responds must be between 0 and 1")
            available.append((roles, p))

        min_crew = {Role(k): int(v) for k, v in
                    (body.get("min_crew") or {"driver_operator": 1, "firefighter": 2}).items()}
        if sum(min_crew.values()) < 1:
            raise ValueError("min_crew must ask for at least one person")

        start_raw = body.get("window_start")
        if start_raw:
            start = datetime.fromisoformat(str(start_raw))
        else:
            start = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0,
                                                                 microsecond=0)
        hours = max(1, min(24, int(body.get("hours", 4))))
        end = start + timedelta(hours=hours)

        per_day = float(body.get("calls_per_day", 1.6))
        if not 0 < per_day <= 200:
            raise ValueError("calls_per_day must be above 0 and below 200")
        share = float(body.get("time_critical_share", 0.65))
        if not 0.0 <= share <= 1.0:
            raise ValueError("time_critical_share must be between 0 and 1")

        # No call history is supplied, so the national-shaped profile carries the whole estimate and
        # the explanation says so.
        rate = RateModel(history_days=0, base_per_hour=per_day / 24,
                         hour_weights=NATIONAL_HOUR_PROFILE, dow_weights=NATIONAL_DOW_PROFILE,
                         month_weights=NATIONAL_MONTH_PROFILE, severity_by_hour=[share] * 24)

        alerts = []
        weather = (body.get("weather") or "").strip()
        if weather:
            mult = HAZARD_MULTIPLIERS.get(weather.lower())
            if mult is None:
                raise ValueError(f"unknown weather alert {weather!r}; see known_alerts in this response")
            alerts.append(WeatherAlert(event=weather, start=start, end=end, multiplier=mult))

        r = score_window(start, end, available, min_crew, rate, alerts)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail={
            "error": str(exc),
            "known_alerts": sorted(HAZARD_MULTIPLIERS),
            "known_roles": [x.value for x in Role],
        }) from exc

    return {
        "window": {"start": start.isoformat(), "end": end.isoformat(), "hours": hours},
        "level": r.level.value,
        "risk_score": r.risk_score,
        "explanation": r.explanation,
        "inputs": {
            "expected_calls": r.expected_calls,
            "hazard": r.hazard,
            "hazard_names": r.hazard_names,
            "p_understaffed": r.p_understaffed,
            "severity": r.severity,
            "missing_roles": [x.value for x in r.missing_roles],
            "people_available": len(available),
            "history_days": r.history_days,
        },
        "formula": (f"risk = 1 - exp(-3.0 x ({r.expected_calls} x {r.hazard}) x "
                    f"{r.p_understaffed} x {r.severity}) = {r.risk_score}"),
        "note": ("No call history was supplied, so the expected call count comes from a national "
                 "shaped profile scaled to your calls per day. A real department's own twelve "
                 "months would sharpen it."),
    }


@app.post("/api/step", tags=["demo"])
def post_step(body: dict = Body(default={})) -> dict:
    """Run the next step of the demo week, or a named one via {"step": "neighbors"}."""
    return service.step(body.get("step"))


@app.post("/api/reply", tags=["demo"])
def post_reply(body: dict = Body(...)) -> dict:
    """Deliver an inbound text, exactly as a real phone would.

    Body: {"phone": "+1555...", "body": "1"}
    """
    phone, text = normalize_phone(body.get("phone")), body.get("body")
    if not phone or text is None:
        raise HTTPException(status_code=400, detail="phone and body are required")
    return service.reply(phone, text)


@app.post("/api/reset", tags=["demo"])
def post_reset() -> dict:
    """Put the scenario back to Wednesday 06:30."""
    return service.reset()


@app.get("/api/openapi.json", include_in_schema=False)
def openapi_alias() -> JSONResponse:
    return JSONResponse(app.openapi())


if WEB_DIR.is_dir():
    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
