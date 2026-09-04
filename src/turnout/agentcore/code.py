"""Run the risk kernel inside Amazon Bedrock AgentCore Code Interpreter.

The point is not that arithmetic needs a sandbox. The point is that the number a chief is asked to
act on should be produced by code whose execution is recorded, in an environment separate from the
agent that is talking about it, so "the risk engine runs as code" can be checked rather than
believed.

`engine/kernel.py` is uploaded verbatim and its own `score()` is called. It is the same file the
local path imports, so the two cannot drift.

If AgentCore is unavailable, unreachable or slow, this falls back to running the identical kernel
locally and says so. A demo that dies because a managed service had a bad minute is worse than one
that degrades and tells you.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

SYSTEM_INTERPRETER = "aws.codeinterpreter.v1"
SESSION_SECONDS = 900
CALL_TIMEOUT = 25.0

_KERNEL_SRC = Path(__file__).resolve().parents[1] / "engine" / "kernel.py"


class CodeInterpreterUnavailable(RuntimeError):
    pass


class RiskKernelSession:
    """One long lived Code Interpreter session, with the kernel already loaded.

    Starting a session costs about two seconds and every call after that is about a tenth of one, so
    the session is created once and reused rather than per request.
    """

    def __init__(self, region: str = "us-east-1", identifier: str = SYSTEM_INTERPRETER) -> None:
        self.region = region
        self.identifier = identifier
        self._session_id: str | None = None
        self._client = None
        self._lock = threading.Lock()
        self.last_error: str | None = None

    # lifecycle ---------------------------------------------------------------
    def _ensure(self) -> str:
        if self._session_id:
            return self._session_id
        with self._lock:
            if self._session_id:
                return self._session_id
            try:
                import boto3

                self._client = boto3.client("bedrock-agentcore", region_name=self.region)
                r = self._client.start_code_interpreter_session(
                    codeInterpreterIdentifier=self.identifier,
                    name="turnout-risk-kernel",
                    sessionTimeoutSeconds=SESSION_SECONDS,
                )
                self._session_id = r["sessionId"]
                self._load_kernel()
                return self._session_id
            except Exception as exc:
                self.last_error = f"{type(exc).__name__}: {exc}"[:200]
                self._session_id = None
                raise CodeInterpreterUnavailable(self.last_error) from exc

    def _load_kernel(self) -> None:
        """Put the real kernel source in the sandbox, then import it there."""
        src = _KERNEL_SRC.read_text(encoding="utf-8")
        self._client.invoke_code_interpreter(
            codeInterpreterIdentifier=self.identifier, sessionId=self._session_id,
            name="writeFiles",
            arguments={"content": [{"path": "kernel.py", "text": src}]},
        )
        out = self._raw("import kernel, json; print('kernel loaded', kernel.SCALE)")
        if "kernel loaded" not in out:
            raise CodeInterpreterUnavailable(f"kernel did not import in the sandbox: {out[:160]}")

    def _raw(self, code: str) -> str:
        r = self._client.invoke_code_interpreter(
            codeInterpreterIdentifier=self.identifier, sessionId=self._session_id,
            name="executeCode", arguments={"language": "python", "code": code},
        )
        chunks = []
        for event in r["stream"]:
            for c in event.get("result", {}).get("content", []):
                if c.get("type") == "text":
                    chunks.append(c["text"])
        return "".join(chunks)

    def close(self) -> None:
        if self._session_id and self._client:
            try:
                self._client.stop_code_interpreter_session(
                    codeInterpreterIdentifier=self.identifier, sessionId=self._session_id)
            except Exception:
                pass
        self._session_id = None

    # the one call --------------------------------------------------------------
    def score(self, payload: dict) -> dict:
        """Run kernel.score(payload) in the sandbox and return its result plus where it ran."""
        started = time.time()
        self._ensure()
        code = (
            "import json, kernel\n"
            f"payload = json.loads(r'''{json.dumps(payload)}''')\n"
            "print('RESULT:' + json.dumps(kernel.score(payload)))\n"
        )
        out = self._raw(code)
        marker = out.find("RESULT:")
        if marker < 0:
            self._session_id = None  # a broken session should not be reused
            raise CodeInterpreterUnavailable(f"no result from the sandbox: {out[:200]}")
        result = json.loads(out[marker + len("RESULT:"):].strip().splitlines()[0])
        result["ran_in"] = "agentcore_code_interpreter"
        result["session_id"] = self._session_id
        result["ms"] = int((time.time() - started) * 1000)
        return result


_session: RiskKernelSession | None = None


def get_session(region: str = "us-east-1") -> RiskKernelSession:
    global _session
    if _session is None:
        _session = RiskKernelSession(region=region)
    return _session


def score(payload: dict, region: str = "us-east-1", use_agentcore: bool = True) -> dict:
    """Score a window, in AgentCore when it is available and locally when it is not.

    The result always says where it ran, because a claim about where code executed is only worth
    making if the answer is on the screen.
    """
    from turnout.engine import kernel

    if use_agentcore:
        try:
            return get_session(region).score(payload)
        except Exception as exc:
            local = kernel.score(payload)
            local["ran_in"] = "local_fallback"
            local["fallback_reason"] = f"{type(exc).__name__}: {exc}"[:160]
            return local
    local = kernel.score(payload)
    local["ran_in"] = "local"
    return local
