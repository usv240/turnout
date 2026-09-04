"""Qualified crew feasibility: can the available members fill the minimum crew, one role each?

This is a small bipartite matching between members and role slots. Exact, not heuristic.
"""

from __future__ import annotations

from turnout.models import Role


def _slots(min_crew: dict[Role, int]) -> list[Role]:
    out: list[Role] = []
    for role, n in min_crew.items():
        out.extend([role] * n)
    return out


def max_matching(member_roles: list[set[Role]], slots: list[Role]) -> tuple[int, list[int | None]]:
    """Kuhn's algorithm. Returns (matched_count, slot_assignment) where slot_assignment[i] is the member index."""
    slot_to_member: list[int | None] = [None] * len(slots)

    def try_assign(m: int, seen: list[bool]) -> bool:
        for s, role in enumerate(slots):
            if role in member_roles[m] and not seen[s]:
                seen[s] = True
                if slot_to_member[s] is None or try_assign(slot_to_member[s], seen):
                    slot_to_member[s] = m
                    return True
        return False

    matched = 0
    for m in range(len(member_roles)):
        if try_assign(m, [False] * len(slots)):
            matched += 1
    return matched, slot_to_member


def missing_roles(member_roles: list[set[Role]], min_crew: dict[Role, int]) -> list[Role]:
    """Roles that cannot be filled. Empty list means the crew requirement is feasible."""
    slots = _slots(min_crew)
    if not slots:
        return []
    matched, assignment = max_matching(member_roles, slots)
    if matched == len(slots):
        return []
    return [slots[i] for i, m in enumerate(assignment) if m is None]


def is_feasible(member_roles: list[set[Role]], min_crew: dict[Role, int]) -> bool:
    return not missing_roles(member_roles, min_crew)
