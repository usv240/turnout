"""Runtime context shared by tools and agents.

Tools are plain functions decorated with @tool. They reach the store, clock, and channels through
`ctx`, which is configured once per process (local demo, test, or AgentCore runtime). Keeping this
explicit makes every tool testable with a MemoryStore and a simulated clock.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from turnout.clock import Clock
from turnout.config import Settings, settings as default_settings
from turnout.store import MemoryStore, Store

EventListener = Callable[[str, dict[str, Any]], None]


@dataclass
class Runtime:
    store: Store
    clock: Clock
    sms: Any  # channels.sms.SmsChannel
    weather: Any  # channels.weather.WeatherSource
    neris: Any  # channels.neris.NerisClient
    settings: Settings = field(default_factory=lambda: default_settings)
    dept_id: str = ""  # the department this process serves
    use_a2a: bool = False
    """Talk to peers over the Agent-to-Agent protocol. False runs peers in-process, which is what the
    single-command local demo does. Deployments and the A2A tests set this to True."""
    peers: dict[str, Any] = field(default_factory=dict)  # dept_id -> A2A client or in-process peer
    listeners: list[EventListener] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)

    def emit(self, kind: str, **payload: Any) -> None:
        """Publish an event for the web app and the trace viewer."""
        evt = {"kind": kind, "at": self.clock.now().isoformat(), "dept_id": self.dept_id, **payload}
        self.trace.append(evt)
        for fn in list(self.listeners):
            try:
                fn(kind, evt)
            except Exception:  # listeners must never break the agent
                pass


ctx: Runtime | None = None


def configure(rt: Runtime) -> Runtime:
    global ctx
    ctx = rt
    return rt


def get() -> Runtime:
    if ctx is None:
        raise RuntimeError("turnout.runtime.configure() has not been called")
    return ctx


def local_runtime(dept_id: str, clock: Clock | None = None, store: Store | None = None) -> Runtime:
    """A fully simulated runtime for tests and the local demo."""
    from turnout.channels.neris import MockNerisClient
    from turnout.channels.sms import SimSmsChannel
    from turnout.channels.weather import FixtureWeather

    clk = clock or Clock()
    st = store or MemoryStore()
    rt = Runtime(store=st, clock=clk, sms=SimSmsChannel(st, clk), weather=FixtureWeather(),
                 neris=MockNerisClient(), dept_id=dept_id)
    rt.sms.runtime = rt
    return rt
