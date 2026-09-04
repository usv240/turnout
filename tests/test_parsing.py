import pytest

from turnout.parsing import parse_reply


@pytest.mark.parametrize("text,intent", [
    ("Y", "yes"), ("y", "yes"), ("yes", "yes"), ("Yep!", "yes"), ("sure", "yes"), ("ok", "yes"), ("can do", "yes"),
    ("I can", "yes"), ("count me in", "yes"), ("10-4", "yes"),
    ("N", "no"), ("no", "no"), ("nope", "no"), ("can't", "no"), ("not available", "no"), ("working", "no"),
    ("out of town", "no"), ("not this week", "no"), ("sorry, can't make it", "no"),
    ("STOP", "stop"), ("stop", "stop"), ("unsubscribe", "stop"), ("START", "start"), ("HELP", "help"),
    ("limits", "limits"), ("status", "status"), ("gaps", "gaps"),
    ("1", "decision"), ("2", "decision"), ("3", "decision"), ("2b", "decision"), ("UNDO", "decision"),
])
def test_intents(text, intent):
    assert parse_reply(text).intent == intent


@pytest.mark.parametrize("text,start,end", [
    ("till 2", None, 14), ("until 2pm", None, 14), ("til noon", None, 12), ("before 11", None, 11),
    ("morning only", None, 12), ("afternoon", 12, None), ("after 1", 13, None), ("from 3pm", 15, None),
    ("can do till 2", None, 14), ("yes until 3", None, 15),
])
def test_partial_windows(text, start, end):
    p = parse_reply(text)
    assert p.intent == "partial"
    assert p.window_start_hour == start
    assert p.window_end_hour == end


def test_unknown():
    p = parse_reply("depends on the kids")
    assert p.intent == "unknown"
    assert p.confidence == 0.0


def test_decision_choice():
    assert parse_reply("2a").decision_choice == "2a"
    assert parse_reply("undo").decision_choice == "undo"
