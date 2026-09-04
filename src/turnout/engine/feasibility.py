"""Qualified crew feasibility: can the available members fill the minimum crew, one role each?

The matching itself lives in `kernel.py`, which is dependency free so that the identical source can
run inside AgentCore Code Interpreter. This module is the typed front door to it.
"""

from __future__ import annotations

from turnout.engine import kernel
from turnout.models import Role


def max_matching(member_roles: list[set[Role]], slots: list[Role]) -> tuple[int, list[int | None]]:
    return kernel.max_matching([{str(r) for r in s} for s in member_roles], [str(s) for s in slots])


def missing_roles(member_roles: list[set[Role]], min_crew: dict[Role, int]) -> list[Role]:
    """Roles that cannot be filled. Empty list means the crew requirement is feasible."""
    out = kernel.missing_roles([{str(r) for r in s} for s in member_roles],
                               {str(k): v for k, v in min_crew.items()})
    return [Role(r) for r in out]


def is_feasible(member_roles: list[set[Role]], min_crew: dict[Role, int]) -> bool:
    return not missing_roles(member_roles, min_crew)
