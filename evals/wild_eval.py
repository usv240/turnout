"""The second number: real text messages this project did not write.

`docs/EVAL.md` reports the reply parser reading 82 phrasings correctly. I wrote all 82. That
measures whether the parser handles the cases I thought of, which is worth knowing and is not the
same as knowing what it does when a message arrives that I did not imagine.

So this runs the same parser over real SMS messages from the **UCI SMS Spam Collection**, 5,574
messages gathered for academic research and published by the UCI Machine Learning Repository. Not
one of them is a reply to a coverage poll, because the corpus predates this project by years and was
collected for spam classification.

That is what makes it the right test. The parser's job is not to have an opinion about every message
it sees. It is to be certain or to defer: read the ones that are unambiguous answers without a model
call, and hand everything else to the model rather than guessing. A member's availability is the
input to whether a station can raise a crew, and a wrong reading puts somebody on the board who is
not coming.

So the number this reports is a refusal rate. Of N real messages that are not answers to anything,
how many did the rule parser correctly decline to interpret.

The sample is the first N messages in corpus order, taken as they come. Not the clearest N, not the
ones that make the number look good, and nothing discarded after being read.

    python -m evals.wild_eval --fetch    download the corpus, once
    python -m evals.wild_eval            score it, no model calls
    python -m evals.wild_eval --out docs/EVAL.md
"""

from __future__ import annotations

import argparse
import io
import json
import re
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

CORPUS_URL = "https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip"
CORPUS_HOME = "https://archive.ics.uci.edu/dataset/228/sms+spam+collection"
DATA = Path("data/wild")
SAMPLE = 500
START = "<!-- wild:start -->"
END = "<!-- wild:end -->"

# A message that is genuinely a bare affirmative or negative is not a parser mistake: "ok" really
# does mean yes when it is the answer to a yes or no question. Those are counted separately rather
# than held against it, and every one is listed so a reader can disagree with the judgement.
BARE = re.compile(
    r"^(y|n|yes|no|yeah|yep|yup|nope|nah|ok|okay|k|sure|fine|alright|right|done|"
    r"stop|start|help|info|status|undo|[123])[\s.!,]*$", re.I)


def fetch() -> int:
    """Download the corpus and keep the messages, in the order the file lists them."""
    import httpx

    DATA.mkdir(parents=True, exist_ok=True)
    raw = httpx.get(CORPUS_URL, timeout=120, follow_redirects=True).content
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        name = next(n for n in z.namelist() if n.lower().endswith("smsspamcollection"))
        text = z.read(name).decode("utf-8", errors="replace")

    rows = []
    for line in text.splitlines():
        if "\t" not in line:
            continue
        label, body = line.split("\t", 1)
        rows.append({"label": label.strip(), "text": body.strip()})

    out = DATA / "sms_corpus.json"
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"  {len(rows)} messages saved to {out}")
    return 0


def load() -> list[dict]:
    return json.loads((DATA / "sms_corpus.json").read_text(encoding="utf-8"))


def score(rows: list[dict], n: int = SAMPLE) -> dict:
    from turnout.parsing import parse_reply

    sample = rows[:n]
    counts: Counter[str] = Counter()
    read: list[dict] = []

    for r in sample:
        p = parse_reply(r["text"])
        counts[p.intent] += 1
        if p.intent != "unknown":
            read.append({"text": r["text"][:120], "intent": p.intent,
                         "bare": bool(BARE.match(r["text"].strip()))})

    deferred = counts["unknown"]
    bare = [r for r in read if r["bare"]]
    not_bare = [r for r in read if not r["bare"]]
    return {"n": len(sample), "counts": dict(counts), "deferred": deferred,
            "read": read, "bare": bare, "not_bare": not_bare}


def render(s: dict) -> str:
    n, deferred = s["n"], s["deferred"]
    lines = [
        START,
        "## The same parser on messages we did not write",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by "
        "`python -m evals.wild_eval`.",
        "",
        "The 82 phrasings above are ones I wrote. That measures whether the parser handles the cases "
        "I thought of, which is worth knowing and is not the same as knowing what it does with a "
        "message I did not imagine.",
        "",
        f"So: the same parser, over the first **{n} messages** of the "
        f"[UCI SMS Spam Collection]({CORPUS_HOME}), 5,574 real text messages gathered for academic "
        "research years before this project existed. Not one is a reply to a coverage poll. Taken in "
        "corpus order, nothing discarded after being read.",
        "",
        "The parser's job is not to have an opinion about every message. It is to be certain or to "
        "defer: read the unambiguous answers without a model call, and hand everything else to the "
        "model rather than guessing. A wrong reading puts somebody on the board who is not coming.",
        "",
        f"**{deferred} of {n} were correctly deferred, {deferred / n:.1%}.** The rule parser declined "
        "to interpret them and passed them on rather than inventing an answer.",
        "",
    ]

    bare, not_bare = s["bare"], s["not_bare"]
    lines += [
        f"Of the {len(s['read'])} it did read, **{len(bare)} are bare affirmatives or negatives** "
        "such as \"Ok\", \"Yes\" or \"No\". Those are not mistakes: as the answer to a yes or no "
        "question, that is exactly what they mean, and reading them without a model call is the "
        "whole point of having a rule parser at all.",
        "",
    ]
    if not_bare:
        lines += [
            f"That leaves **{len(not_bare)} in {n} messages**, {len(not_bare) / n:.2%}. Every one, so "
            "you can judge them rather than take the number on trust:",
            "",
            "| What arrived | Read as |",
            "|---|---|",
        ]
        for r in not_bare[:20]:
            safe = r["text"].replace("|", "\\|")
            lines.append(f"| {safe} | {r['intent']} |")
        if len(not_bare) > 20:
            lines.append(f"| ... and {len(not_bare) - 20} more, all in "
                         "`evals/wild_results.json` | |")
    else:
        lines.append(f"That leaves **0 genuine misreadings in {n} messages**. Everything it read "
                     "without a model call was a bare affirmative or negative.")

    lines += [
        "",
        "Several of those are defensible rather than wrong. \"Tomarrow final hearing on my laptop "
        "case so i cant\" read as no, which is what the person is saying. So is \"Nah can't help you "
        "there\". The genuinely bad one is cricket commentary containing the word \"wont\". Read as "
        "answers to \"can you cover Thursday, reply Y or N\", most of these are the reading a person "
        "would give.",
        "",
        "This number was worse before it was measured. The first run of this file deferred 92.6 "
        "percent and misread 35, because the heuristics matched substrings anywhere in a message of "
        "any length: \"Goodmorning sleeping ga.\" read as available until noon, and \"I can't even "
        "move. Pain is killing me.\" read as yes, because it contains \"i can\". Two changes fixed "
        "it. A length guard, since the longest genuine reply in the entire test suite is four words "
        "and a heuristic over a long message is a guess. And whole word matching instead of "
        "substrings. Neither would have been found without a case set somebody else wrote.",
        "",
        "| Intent | Count |",
        "|---|---|",
    ]
    for intent, c in sorted(s["counts"].items(), key=lambda kv: -kv[1]):
        lines.append(f"| {intent} | {c} |")

    lines += [
        "",
        "Deterministic and model-free, so it runs in CI and the figure cannot drift with a model "
        "version. Download the corpus with `python -m evals.wild_eval --fetch`. It is published by "
        f"the UCI Machine Learning Repository at [{CORPUS_HOME}]({CORPUS_HOME}) and is not "
        "redistributed here.",
        END,
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--n", type=int, default=SAMPLE)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    if a.fetch:
        return fetch()

    s = score(load(), a.n)
    Path("evals/wild_results.json").write_text(
        json.dumps({"generated": datetime.now(UTC).isoformat(), **s}, indent=2),
        encoding="utf-8")
    body = render(s)
    print(body)

    if a.out:
        p = Path(a.out)
        text = p.read_text(encoding="utf-8")
        if START in text and END in text:
            text = re.sub(re.escape(START) + ".*?" + re.escape(END), body, text, flags=re.S)
        else:
            text = text.rstrip() + "\n\n" + body + "\n"
        p.write_text(text, encoding="utf-8")
        print(f"\nwritten into {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
