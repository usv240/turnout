"""NERIS submission.

The real National Emergency Response Information System requires department credentials.
The mock records the submission payload so the demo shows the full flow. A documented extension
uses AgentCore Browser to fill the portal when no API is available to a small department.
"""

from __future__ import annotations

from datetime import datetime

from turnout.models import NerisDraft


class MockNerisClient:
    def __init__(self) -> None:
        self.submitted: list[dict] = []

    def submit(self, dept_id: str, incident_id: str, draft: NerisDraft, at: datetime) -> str:
        ref = f"NERIS-MOCK-{len(self.submitted) + 1:05d}"
        self.submitted.append({"ref": ref, "dept_id": dept_id, "incident_id": incident_id,
                               "at": at.isoformat(), "draft": draft.model_dump(mode="json")})
        return ref
