"""AgentCore integration, and the property that makes the claim worth making.

These do not call AWS. The point of the kernel is that one file runs in both places, so what has to
be tested is that the local path and the payload the remote path sends are the same computation, and
that an unavailable service degrades rather than breaks.
"""

from datetime import datetime

import pytest

from turnout.agentcore import code
from turnout.engine import kernel
from turnout.engine.risk import RateModel, score_window
from turnout.models import Level, Role, WeatherAlert

FIRE = {Role.DRIVER_OPERATOR: 1, Role.FIREFIGHTER: 2}
START = datetime(2026, 9, 10, 10, 0)
END = datetime(2026, 9, 10, 14, 0)


def payload(members):
    return {"members": members, "min_crew": {"driver_operator": 1, "firefighter": 2},
            "expected_calls": 0.373, "hazard": 1.8, "severity": 0.825}


def test_the_kernel_imports_only_the_standard_library():
    """It is uploaded into a sandbox that has none of this project on it, so it must stand alone.

    Parsed rather than grepped, because the earlier version of this test matched the word pydantic
    in the module docstring, which is exactly the sort of pass that means nothing."""
    import ast
    import pathlib
    import sys

    tree = ast.parse(pathlib.Path(kernel.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    imported.discard("__future__")
    assert imported <= set(sys.stdlib_module_names), f"kernel imports {imported - set(sys.stdlib_module_names)}"


def test_kernel_reproduces_the_hand_computed_probability():
    p = kernel.p_understaffed([({"driver_operator"}, 0.5), ({"firefighter"}, 1.0),
                               ({"firefighter"}, 1.0)], {"driver_operator": 1, "firefighter": 2})
    assert p == pytest.approx(0.5)


def test_one_person_cannot_fill_two_slots():
    assert not kernel.is_feasible([{"driver_operator", "firefighter"}, {"firefighter"}],
                                  {"driver_operator": 1, "firefighter": 2})


def test_score_is_the_same_whichever_path_runs_it():
    """The whole reason for a shared kernel: the answer cannot depend on where it executed."""
    a = kernel.score(payload([[["firefighter"], 0.45]]))
    b = code.score(payload([[["firefighter"], 0.45]]), use_agentcore=False)
    assert a["risk_score"] == b["risk_score"]
    assert a["level"] == b["level"] == "critical"
    assert a["missing_roles"] == b["missing_roles"]


def test_a_result_always_says_where_it_ran():
    out = code.score(payload([[["firefighter"], 0.45]]), use_agentcore=False)
    assert out["ran_in"] == "local"


def test_an_unavailable_agentcore_degrades_and_explains_itself(monkeypatch):
    """A demo that dies because a managed service had a bad minute is worse than one that says so."""
    class Broken:
        def score(self, _):
            raise RuntimeError("simulated outage")

    monkeypatch.setattr(code, "get_session", lambda region="us-east-1": Broken())
    out = code.score(payload([[["firefighter"], 0.45]]), use_agentcore=True)
    assert out["ran_in"] == "local_fallback"
    assert "simulated outage" in out["fallback_reason"]
    assert out["risk_score"] == kernel.score(payload([[["firefighter"], 0.45]]))["risk_score"]


def test_the_risk_engine_reports_its_execution_location():
    rate = RateModel(0, 1.6 / 24, [1.0] * 24, [1.0] * 7, [1.0] * 12, [0.65] * 24)
    r = score_window(START, END, [({Role.FIREFIGHTER}, 0.45)], FIRE, rate,
                     [WeatherAlert(event="Ice Storm Warning", start=START, end=END, multiplier=1.8)],
                     use_agentcore=False)
    assert r.ran_in == "local"
    # A flat rate profile expects fewer calls than the real one, so this is high rather than
    # critical. What this test is for is the provenance, not the level.
    assert r.level in (Level.HIGH, Level.CRITICAL)
    assert r.p_understaffed == 1.0  # one firefighter can never make a crew of three


def test_the_memory_status_counts_rather_than_claims():
    """A claim about where data went is only worth making if the answer can be checked."""
    from turnout.agentcore import memory

    memory.written.clear()
    assert memory.status("millbrook") == {"agentcore": 0, "local": 0, "memory_id": None,
                                          "last_error": None}
    memory.record_response("millbrook", "m01", "weekday_day", True, use_agentcore=False)
    memory.record_response("millbrook", "m02", "weekday_day", False, use_agentcore=False)
    s = memory.status("millbrook")
    assert s["local"] == 2 and s["agentcore"] == 0
    memory.written.clear()


def test_a_memory_that_does_not_answer_falls_back_and_says_why():
    """A managed service having a bad minute must degrade, not take the answer down with it."""
    from turnout.agentcore import memory

    memory.written.clear()

    class Broken:
        def record(self, *a, **k):
            raise RuntimeError("no memory for millbrook yet")

    memory._memories["millbrook"] = Broken()
    try:
        out = memory.record_response("millbrook", "m01", "weekday_day", True, use_agentcore=True)
    finally:
        memory._memories.pop("millbrook", None)
    assert out["stored_in"] == "local_fallback"
    assert "no memory for millbrook" in out["reason"]
    assert memory.status("millbrook")["local"] == 1
    memory.written.clear()


class _FakeInterpreter:
    """Enough of the bedrock-agentcore client to exercise session handling without AWS.

    Every session it starts is alive until `kill()` is called, after which any invoke against it
    raises the way the real service does for a terminated session.
    """

    def __init__(self):
        self.started = 0
        self.dead: set[str] = set()
        self.stopped: list[str] = []

    def start_code_interpreter_session(self, **kw):
        self.started += 1
        return {"sessionId": f"session-{self.started}"}

    def stop_code_interpreter_session(self, **kw):
        self.stopped.append(kw["sessionId"])
        return {}

    def kill(self, session_id):
        self.dead.add(session_id)

    def invoke_code_interpreter(self, **kw):
        if kw["sessionId"] in self.dead:
            raise RuntimeError("ValidationException: session is not active")
        if kw["name"] == "writeFiles":
            return {"stream": [{"result": {"content": [{"type": "text", "text": "ok"}]}}]}
        src = kw["arguments"]["code"]
        text = "kernel loaded 12" if "kernel loaded" in src else (
            f"{src}\n{code.MARKER}" + '{"p_understaffed": 1.0, "missing_roles": ["driver_operator"], '
            '"risk_score": 0.83, "level": "critical"}\n')
        return {"stream": [{"result": {"content": [{"type": "text", "text": text}]}}]}


def _session_with(fake):
    s = code.RiskKernelSession(region="us-east-1")
    s._client = fake
    # boto3 is only touched inside _ensure when there is no client; give it one and no session.
    return s


def test_a_terminated_session_is_replaced_rather_than_reused():
    """The service ends a session after its timeout. Reusing the dead id made every later score
    fall back to local, silently, about fifteen minutes after each deploy."""
    fake = _FakeInterpreter()
    s = _session_with(fake)
    first = s.score(payload([[["firefighter"], 0.45]]))
    assert first["ran_in"] == "agentcore_code_interpreter" and first["session_id"] == "session-1"

    fake.kill("session-1")
    second = s.score(payload([[["firefighter"], 0.45]]))
    assert second["ran_in"] == "agentcore_code_interpreter"
    assert second["session_id"] == "session-2", "a fresh session, not the dead one"
    assert fake.started == 2


def test_a_session_near_its_deadline_is_renewed_before_it_fails():
    fake = _FakeInterpreter()
    s = _session_with(fake)
    s.score(payload([[["firefighter"], 0.45]]))
    s._started_at -= code.SESSION_SECONDS  # pretend the timeout has all but elapsed
    out = s.score(payload([[["firefighter"], 0.45]]))
    assert out["session_id"] == "session-2"
    assert "session-1" in fake.stopped, "the old one is closed rather than left to expire"


def test_two_failures_in_a_row_give_up_honestly():
    fake = _FakeInterpreter()
    s = _session_with(fake)
    s.score(payload([[["firefighter"], 0.45]]))
    fake.kill("session-1")
    fake.kill("session-2")
    fake.kill("session-3")
    with pytest.raises(code.CodeInterpreterUnavailable) as err:
        s.score(payload([[["firefighter"], 0.45]]))
    assert "not active" in str(err.value)
