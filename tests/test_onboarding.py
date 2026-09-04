from turnout.models import Role
from turnout.onboarding import CREW_PRESETS, clean_name, find_roles, normalise_phone, parse_roster

GROUP_TEXT = """
Dana Ortiz (Chief) 555-298-6397
Luis Reyes - driver 555 111 2222
Marcy Kowalski EMT (555) 333-4444
Tom Bright ff +1 555 555 6666
"""

SPREADSHEET = """
Name,Phone,Role
Priya Nair,5551234567,EMT
Dave Miller,555-765-4321,Driver Operator
Ellen Shaw,(555) 888-9999,Firefighter
"""


def test_phone_formats_all_normalise():
    for raw in ["555-298-6397", "555 298 6397", "(555) 298-6397", "+1 555 298 6397",
                "1.555.298.6397", "5552986397"]:
        assert normalise_phone(raw) == "+15552986397", raw


def test_a_line_with_no_phone_number_is_not_a_member():
    assert normalise_phone("Dana Ortiz, chief") is None


def test_group_text_paste():
    r = parse_roster(GROUP_TEXT)
    assert [m.name for m in r.members] == ["Dana Ortiz", "Luis Reyes", "Marcy Kowalski", "Tom Bright"]
    assert r.members[0].phone == "+15552986397"
    assert not r.unreadable


def test_spreadsheet_paste_including_the_header_row():
    r = parse_roster(SPREADSHEET)
    assert [m.name for m in r.members] == ["Priya Nair", "Dave Miller", "Ellen Shaw"]
    # The header line has words but no number, so it is reported rather than dropped in silence.
    assert any("Name" in u for u in r.unreadable)


def test_roles_are_read_from_the_line():
    r = parse_roster(GROUP_TEXT)
    by_name = {m.name: m.roles for m in r.members}
    assert Role.OFFICER in by_name["Dana Ortiz"]
    assert Role.DRIVER_OPERATOR in by_name["Luis Reyes"]
    assert Role.EMT in by_name["Marcy Kowalski"]
    assert Role.FIREFIGHTER in by_name["Tom Bright"]


def test_everyone_is_a_firefighter_unless_they_are_ems_only():
    """The minimum crew is counted in firefighters, so a chief or a driver who is not also recorded
    as a firefighter would make a department look short the moment it onboarded."""
    assert find_roles("Sam Cole 555 111 2222") == [Role.FIREFIGHTER]
    assert set(find_roles("Dana Ortiz (Chief) 555 111 2222")) == {Role.OFFICER, Role.FIREFIGHTER}
    assert set(find_roles("Luis Reyes driver 555 111 2222")) == {Role.DRIVER_OPERATOR, Role.FIREFIGHTER}
    assert find_roles("Marcy Kowalski EMT 555 111 2222") == [Role.EMT]


def test_an_onboarded_roster_can_actually_make_a_crew():
    """The whole point of the roles: three people off a pasted roster must satisfy an engine crew."""
    from turnout.engine.feasibility import is_feasible
    from turnout.onboarding import CREW_PRESETS

    r = parse_roster(GROUP_TEXT)
    role_sets = [set(m.roles) for m in r.members]
    assert is_feasible(role_sets, CREW_PRESETS["engine"]["crew"].fire)


def test_role_words_are_taken_out_of_the_name():
    assert clean_name("Marcy Kowalski EMT (555) 333-4444") == "Marcy Kowalski"
    assert clean_name("Dana Ortiz (Chief) 555-298-6397") == "Dana Ortiz"


def test_a_repeated_number_is_reported_not_added_twice():
    r = parse_roster("Dana Ortiz 555-298-6397\nD. Ortiz 5552986397")
    assert len(r.members) == 1
    assert r.duplicates and "same number" in r.duplicates[0]


def test_blank_input_produces_nothing_and_complains_about_nothing():
    r = parse_roster("\n\n   \n")
    assert not r.members and not r.unreadable


def test_the_crew_presets_are_real_requirements():
    for key, preset in CREW_PRESETS.items():
        assert preset["label"]
        assert sum(preset["crew"].fire.values()) >= 2, key
