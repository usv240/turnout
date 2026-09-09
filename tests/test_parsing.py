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


# The two defects the UCI SMS corpus found. Both were substring matches over arbitrary text, and
# both put somebody on the board who was not coming, which is the one error this system exists to
# prevent. See evals/wild_eval.py.

def test_a_long_message_goes_to_the_model_rather_than_being_guessed_at():
    """The longest genuine reply in this whole file is four words."""
    from turnout.parsing import MAX_RULE_WORDS

    long_one = ("Your gonna have to pick up a $1 burger for yourself on your way home. "
                "I can't even move. Pain is killing me.")
    assert len(long_one.split()) > MAX_RULE_WORDS
    assert parse_reply(long_one).intent == "unknown"

    spam = ("SIX chances to win CASH! From 100 to 20,000 pounds txt> CSH11 and send to 87575. "
            "Cost 150p/day, 6days, 16+ TsandCs apply")
    assert parse_reply(spam).intent == "unknown"


def test_the_time_words_match_whole_words_only():
    """'Goodmorning sleeping ga.' is a real message and it used to read as available until noon."""
    assert parse_reply("Goodmorning sleeping ga.").intent == "unknown"
    assert parse_reply("morning only").intent == "partial"      # still reads
    assert parse_reply("afternoon").intent == "partial"


def test_i_can_does_not_match_i_cannot():
    assert parse_reply("i can").intent == "yes"
    assert parse_reply("i can't").intent == "no"
    assert parse_reply("i cant").intent == "no"
    assert parse_reply("i cannot").intent == "no"


def test_away_matches_a_whole_word():
    assert parse_reply("away").intent == "no"
    assert parse_reply("always").intent != "no"
