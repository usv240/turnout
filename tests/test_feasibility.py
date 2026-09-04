from turnout.engine.feasibility import is_feasible, missing_roles
from turnout.models import Role

FIRE = {Role.DRIVER_OPERATOR: 1, Role.FIREFIGHTER: 2}
EMS = {Role.EMT: 1, Role.DRIVER_OPERATOR: 1}


def test_exact_fill():
    members = [{Role.DRIVER_OPERATOR}, {Role.FIREFIGHTER}, {Role.FIREFIGHTER}]
    assert is_feasible(members, FIRE)


def test_multi_role_member_counts_once():
    # One person who is both driver and firefighter cannot fill two slots.
    members = [{Role.DRIVER_OPERATOR, Role.FIREFIGHTER}, {Role.FIREFIGHTER}]
    assert not is_feasible(members, FIRE)
    assert missing_roles(members, FIRE) in ([Role.FIREFIGHTER], [Role.DRIVER_OPERATOR])


def test_matching_prefers_assignment_that_works():
    # Two dual-role members plus one firefighter: driver can be either dual member.
    members = [{Role.DRIVER_OPERATOR, Role.FIREFIGHTER}, {Role.DRIVER_OPERATOR, Role.FIREFIGHTER}, {Role.FIREFIGHTER}]
    assert is_feasible(members, FIRE)


def test_missing_driver_reported():
    members = [{Role.FIREFIGHTER}, {Role.FIREFIGHTER}, {Role.FIREFIGHTER}]
    assert missing_roles(members, FIRE) == [Role.DRIVER_OPERATOR]


def test_nobody():
    assert missing_roles([], EMS) == [Role.EMT, Role.DRIVER_OPERATOR]


def test_empty_requirement():
    assert missing_roles([], {}) == []
