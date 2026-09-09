"""Tracing must be invisible unless somebody asked for it, and must never take the agent down.

Two guarantees, both of which matter more than the traces themselves:

Off by default. The submitted demo runs with no collector reachable. If enabling telemetry were the
default, every start would spend its timeout trying to reach one, which is a slow demo and a
confusing log for no benefit.

Never raises. A monitoring backend is the least important dependency this service has. If the
exporter cannot start, the correct behaviour is to say so and run untraced, not to refuse to serve
a chief or a provider who needs an answer now.
"""

from __future__ import annotations

import turnout.observability as obs


def reset() -> None:
    obs._state = None


def test_off_unless_asked(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.delenv("TURNOUT_TRACE_CONSOLE", raising=False)
    reset()
    s = obs.setup()
    assert s.startswith("off")
    assert obs.status() == s


def test_console_exporter_turns_on(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setenv("TURNOUT_TRACE_CONSOLE", "1")
    reset()
    s = obs.setup()
    assert s.startswith("on")
    assert "console" in s


def test_a_broken_exporter_does_not_take_the_agent_down(monkeypatch):
    monkeypatch.setenv("TURNOUT_TRACE_CONSOLE", "1")
    reset()

    class Boom:
        def __init__(self, *a, **k):
            raise RuntimeError("collector unreachable")

    import strands.telemetry
    monkeypatch.setattr(strands.telemetry, "StrandsTelemetry", Boom)
    s = obs.setup()
    assert "failed to start" in s
    assert "untraced" in s


def test_setup_is_idempotent(monkeypatch):
    monkeypatch.setenv("TURNOUT_TRACE_CONSOLE", "1")
    reset()
    first = obs.setup()
    assert obs.setup() is first


def test_health_reports_the_real_state():
    """The status page must not claim tracing that is not running."""
    assert obs.status() in (obs._state, "not configured")
