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
