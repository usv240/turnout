"""Member response history in Amazon Bedrock AgentCore Memory.

What the agent needs to remember is small and specific: which members say yes to which kind of
window. That is the input to the response probability, and it is the thing that should get sharper
every week without anyone retraining anything.

Each department gets its own memory, so one department's history is not reachable from another's,
which is the same boundary the Agent-to-Agent protocol draws.

Falls back to the local store when AgentCore is unavailable, and always reports which one answered.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime

RETENTION_DAYS = 90
ACTOR_PREFIX = "member"


class MemoryUnavailable(RuntimeError):
    pass


class ResponseMemory:
    """One AgentCore memory per department, holding response history as events."""

    def __init__(self, dept_id: str, region: str = "us-east-1") -> None:
        self.dept_id = dept_id
        self.region = region
        self.memory_id: str | None = None
        self._cp = None
        self._dp = None
        self._lock = threading.Lock()
        self.last_error: str | None = None

    # lifecycle ---------------------------------------------------------------
    def _clients(self):
        if self._cp is None:
            import boto3

            self._cp = boto3.client("bedrock-agentcore-control", region_name=self.region)
            self._dp = boto3.client("bedrock-agentcore", region_name=self.region)
        return self._cp, self._dp

    def ensure(self, wait_seconds: int = 20, create: bool = False) -> str:
        """Find this department's memory. Creation is a deploy step, not a request time one.

        Provisioning a memory takes minutes, which is fine once and unacceptable while a chief is
        waiting. `python -m turnout.agentcore.provision` creates them ahead of time; at request time
        this only looks one up, and falls back to the local store if it is not there yet.
        """
        if self.memory_id:
            return self.memory_id
        with self._lock:
            if self.memory_id:
                return self.memory_id
            cp, _ = self._clients()
            name = f"turnout_{self.dept_id}"
            try:
                for m in cp.list_memories(maxResults=100).get("memories", []):
                    if m.get("id", "").startswith(name):
                        self.memory_id = m["id"]
                        if m.get("status") == "ACTIVE":
                            return self.memory_id
                        break
                if not self.memory_id:
                    if not create:
                        raise MemoryUnavailable(
                            f"no memory for {self.dept_id} yet. Run "
                            f"python -m turnout.agentcore.provision to create it.")
                    r = cp.create_memory(
                        name=name,
                        description=f"Response history for {self.dept_id}. Which members turn out "
                                    f"for which kind of window.",
                        eventExpiryDuration=RETENTION_DAYS,
                    )
                    self.memory_id = r["memory"]["id"]

                deadline = time.time() + wait_seconds
                while time.time() < deadline:
                    status = cp.get_memory(memoryId=self.memory_id)["memory"]["status"]
                    if status == "ACTIVE":
                        return self.memory_id
                    if status in ("FAILED", "DELETING"):
                        raise MemoryUnavailable(f"memory is {status}")
                    time.sleep(3)
                raise MemoryUnavailable("memory did not become active in time")
            except Exception as exc:
                self.last_error = f"{type(exc).__name__}: {exc}"[:400]
                raise MemoryUnavailable(self.last_error) from exc

    # writing and reading ------------------------------------------------------
    def record(self, member_id: str, window_type: str, said_yes: bool,
               at: datetime | None = None) -> dict:
        """Record one answer. The unit the probability is built from."""
        _, dp = self._clients()
        self.ensure()
        payload = {"member_id": member_id, "window_type": window_type, "said_yes": said_yes}
        dp.create_event(
            memoryId=self.memory_id,
            actorId=f"{ACTOR_PREFIX}-{member_id}",
            sessionId=window_type,
            eventTimestamp=at or datetime.now(),
            payload=[{"conversational": {
                "role": "USER",
                "content": {"text": json.dumps(payload)},
            }}],
        )
        return {"stored_in": "agentcore_memory", "memory_id": self.memory_id}

    def history(self, member_id: str, window_type: str, limit: int = 60) -> tuple[int, int]:
        """Yes and no counts for one member in one kind of window."""
        _, dp = self._clients()
        self.ensure()
        yes = no = 0
        token = None
        while True:
            kw = {"memoryId": self.memory_id, "actorId": f"{ACTOR_PREFIX}-{member_id}",
                  "sessionId": window_type, "maxResults": min(limit, 100)}
            if token:
                kw["nextToken"] = token
            r = dp.list_events(**kw)
            for ev in r.get("events", []):
                for item in ev.get("payload", []):
                    text = item.get("conversational", {}).get("content", {}).get("text", "")
                    try:
                        blob = json.loads(text)
                    except ValueError:
                        continue
                    if blob.get("said_yes"):
                        yes += 1
                    else:
                        no += 1
            token = r.get("nextToken")
            if not token or yes + no >= limit:
                break
        return yes, no


_memories: dict[str, ResponseMemory] = {}


def for_department(dept_id: str, region: str = "us-east-1") -> ResponseMemory:
    if dept_id not in _memories:
        _memories[dept_id] = ResponseMemory(dept_id, region)
    return _memories[dept_id]


# What this process has actually written, per department, so a page can report it rather than
# assert it. A claim about where data went is only worth making if the answer is on the screen.
written: dict[str, dict] = {}


def record_response(dept_id: str, member_id: str, window_type: str, said_yes: bool,
                    use_agentcore: bool = True) -> dict:
    """Record an answer in AgentCore Memory, or say why it went to the local store instead."""
    stat = written.setdefault(dept_id, {"agentcore": 0, "local": 0, "memory_id": None,
                                        "last_error": None})
    if not use_agentcore:
        stat["local"] += 1
        return {"stored_in": "local"}
    try:
        out = for_department(dept_id).record(member_id, window_type, said_yes)
        stat["agentcore"] += 1
        stat["memory_id"] = out.get("memory_id")
        stat["last_error"] = None  # a stale error next to a live count would read as both
        return out
    except Exception as exc:
        stat["local"] += 1
        stat["last_error"] = f"{type(exc).__name__}: {exc}"[:400]
        return {"stored_in": "local_fallback", "reason": stat["last_error"]}


def status(dept_id: str) -> dict:
    """Where this department's answers went, counted rather than claimed."""
    stat = written.get(dept_id) or {"agentcore": 0, "local": 0, "memory_id": None,
                                    "last_error": None}
    return dict(stat)
