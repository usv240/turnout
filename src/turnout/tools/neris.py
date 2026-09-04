"""Scribe's tools: transcript access, draft storage, NERIS submission."""

from __future__ import annotations

from strands import tool

from turnout.models import NerisDraft
from turnout.tools.common import dept, now, rt


@tool
def get_incident(incident_id: str) -> dict:
    """The incident record with its transcript and any context (dispatch time, district, units).

    Args:
        incident_id: the incident id.
    """
    r = rt()
    i = r.store.get_incident(r.dept_id, incident_id)
    return i.model_dump(mode="json")


@tool
def save_neris_draft(incident_id: str, draft_json: str) -> dict:
    """Store the NERIS draft for chief review and tell the chief it is ready.

    Args:
        incident_id: the incident id.
        draft_json: JSON of a NerisDraft.
    """
    r = rt()
    d = dept()
    i = r.store.get_incident(d.id, incident_id)
    i.draft = NerisDraft.model_validate_json(draft_json)
    i.status = "draft"
    r.store.put_incident(i)
    unsure = ", ".join(i.draft.uncertain_fields) if i.draft.uncertain_fields else "none"
    body = f"{d.short_name}: NERIS draft ready for incident {incident_id}. Unsure about: {unsure}. Review on the board."
    r.sms.send(d.id, d.chief_phone, body[:160], "neris")
    r.emit("neris_draft", incident_id=incident_id, uncertain=i.draft.uncertain_fields)
    return {"saved": True, "incident_id": incident_id, "uncertain_fields": i.draft.uncertain_fields}


@tool
def submit_neris(incident_id: str) -> dict:
    """Submit a reviewed draft to NERIS. Only the chief triggers this from the board; agents never call it
    on their own.

    Args:
        incident_id: the incident id.
    """
    r = rt()
    d = dept()
    i = r.store.get_incident(d.id, incident_id)
    if i.draft is None:
        return {"submitted": False, "reason": "no draft"}
    ref = r.neris.submit(d.id, incident_id, i.draft, now())
    i.status = "submitted"
    r.store.put_incident(i)
    r.emit("neris_submitted", incident_id=incident_id, ref=ref)
    return {"submitted": True, "reference": ref}
