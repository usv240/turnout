"""Hooks that enforce policy in code and record every step for the trace viewer.

ContactPolicyHook: a member who opted out is never texted; targeted asks stop at the weekly limit.
The prompt also says so, but the hook is what makes it true.

TraceHook: emits a trace event for every tool call with its input and output, so the Trace Viewer
and AgentCore Observability show the same story.
"""

from __future__ import annotations

import json
from typing import Any

from strands.hooks import AfterToolCallEvent, BeforeToolCallEvent, HookProvider, HookRegistry

from turnout import runtime


class ContactPolicyHook(HookProvider):
    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeToolCallEvent, self.before_tool)

    def before_tool(self, event: BeforeToolCallEvent) -> None:
        name = event.tool_use.get("name")
        if name != "send_member_sms":
            return
        args = event.tool_use.get("input", {}) or {}
        r = runtime.get()
        d = r.store.get_department(r.dept_id)
        try:
            m = r.store.get_member(d.id, args.get("member_id", ""))
        except KeyError:
            event.cancel_tool = "unknown member id"
            return
        purpose = args.get("purpose") or args.get("template")
        if m.opted_out:
            event.cancel_tool = f"{m.name} opted out (STOP). Policy: never text an opted-out member."
            r.emit("policy_block", member_id=m.id, reason="opted_out", purpose=purpose)
            return
        if purpose == "ask" and m.asks_this_week >= d.weekly_ask_limit:
            event.cancel_tool = (f"{m.name} has already been asked {m.asks_this_week} times this week "
                                 f"(limit {d.weekly_ask_limit}). Policy: pick someone else or move on.")
            r.emit("policy_block", member_id=m.id, reason="weekly_ask_limit", purpose=purpose)
            return


class TraceHook(HookProvider):
    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeToolCallEvent, self.before_tool)
        registry.add_callback(AfterToolCallEvent, self.after_tool)

    def before_tool(self, event: BeforeToolCallEvent) -> None:
        r = runtime.get()
        r.emit("tool_call", agent=self.agent_name, tool=event.tool_use.get("name"),
               input=event.tool_use.get("input", {}))

    def after_tool(self, event: AfterToolCallEvent) -> None:
        r = runtime.get()
        result = getattr(event, "result", None)
        text = ""
        try:
            content = result.get("content", []) if isinstance(result, dict) else []
            text = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
        except Exception:
            text = str(result)[:500]
        r.emit("tool_result", agent=self.agent_name, tool=event.tool_use.get("name"),
               status=(result or {}).get("status") if isinstance(result, dict) else None,
               output=text[:1500])


def hooks_for(agent_name: str) -> list[HookProvider]:
    return [ContactPolicyHook(), TraceHook(agent_name)]


def dumps(obj: Any) -> str:
    return json.dumps(obj, default=str)
