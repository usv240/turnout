"""OpenTelemetry traces from the agent graph, so the trace viewer is not the only witness.

`agents/hooks.py` has a TraceHook that emits an event for every tool call, and the web UI renders
those into a readable story. That is the right thing for a chief looking at what happened last
night, and it has a real limit: it is our own format, read by our own viewer, and it stops at the
edge of this process. If a run goes wrong on the deployed service at two in the morning, nobody is
watching that viewer.

Strands already instruments itself with OpenTelemetry. Every agent invocation, every model call and
every tool call becomes a span with timings and token counts, including the path taken through a
multi-agent graph, which is exactly the part the hand-rolled events describe worst. Turning it on is
one call. Amazon Bedrock AgentCore Observability and CloudWatch both ingest OTLP directly, so the
same spans land somewhere durable without any code here knowing which backend received them.

This is off unless an endpoint is configured, deliberately. A demo should not depend on a collector
being reachable, and an exporter that cannot connect is a slow startup and a confusing log rather
than a useful trace. Nothing below can raise into the request path.

    OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318  send spans to a collector
    TURNOUT_TRACE_CONSOLE=1                            print spans to stderr, no collector needed
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

SERVICE = "turnout"
_state: str | None = None


def status() -> str:
    """What tracing is doing, in one line, for the health endpoint to report honestly."""
    return _state or "not configured"


def setup() -> str:
    """Turn on OTEL export if it was asked for. Safe to call more than once.

    Returns a one line description of what happened, which is also what `status()` reports.
    Never raises: a broken collector must not take down the agent that depends on nothing but
    Bedrock.
    """
    global _state
    if _state is not None:
        return _state

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    console = os.environ.get("TURNOUT_TRACE_CONSOLE") in ("1", "true", "yes")

    if not endpoint and not console:
        _state = ("off: set OTEL_EXPORTER_OTLP_ENDPOINT for a collector, "
                  "or TURNOUT_TRACE_CONSOLE=1 to print spans")
        return _state

    os.environ.setdefault("OTEL_SERVICE_NAME", SERVICE)

    try:
        from strands.telemetry import StrandsTelemetry

        t = StrandsTelemetry()
        parts = []
        if console:
            t.setup_console_exporter()
            parts.append("console")
        if endpoint:
            t.setup_otlp_exporter()
            parts.append(f"otlp to {endpoint}")
        _state = f"on: {', '.join(parts)}"
    except Exception as e:
        # An exporter that will not start is a monitoring problem, not a reason to refuse to run.
        _state = f"failed to start ({type(e).__name__}: {e}); running untraced"
        log.warning("telemetry %s", _state)

    log.info("telemetry %s", _state)
    return _state
