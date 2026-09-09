"""Turnout's risk engine against the thing a reasonable engineer would build instead.

The obvious alternative to all of this is a roster check: look at who marked themselves available
for the window, see whether those people can form a legal crew, and call it covered if they can.
Every volunteer scheduling tool on the market does exactly that. It is not a strawman, it is the
incumbent.

It is also wrong, and this measures by how much.

A member marking themselves available is saying they are not at work. It is not a promise to turn
out. Published response rates for volunteer first responders run between 17 and 47 percent, so four
available people can be a legal crew on paper and no crew at all at two in the afternoon.

Ground truth here is simulated, and it has to be, because nobody publishes per-member turnout
records for a real department. So the simulation is kept honest in three ways:

  1. The per-member response probabilities are not invented for this file. They come from the same
     Beta posterior the product uses, over each member's own answer history.
  2. Each window's outcome is drawn once, not averaged, so the ground truth is a coin that actually
     landed rather than the expectation the engine is computing.
  3. The seed is fixed and printed, so the number is reproducible rather than the best of several
     runs.

What is being compared:

  Roster check (baseline)   covered if the available members can form a legal crew
  Turnout                   at risk if the window scores high or critical

    python -m evals.baseline_eval
    python -m evals.baseline_eval --out docs/EVAL.md
"""

from __future__ import annotations

import argparse
import random
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

SCENARIO = "data/scenarios/demo_week.json"
START = "<!-- baseline:start -->"
END = "<!-- baseline:end -->"
SEED = 20260914
WINDOWS = 2000


@dataclass
class Window:
    start: datetime
    available: list[tuple[set, float]]   # (roles, probability this person actually turns out)
    feasible_on_paper: bool
    turnout_at_risk: bool
    actually_failed: bool


def build_windows(seed: int = SEED, n: int = WINDOWS) -> tuple[list[Window], dict]:
    from turnout import runtime
    from turnout.clock import Clock
    from turnout.engine.feasibility import is_feasible
    from turnout.engine.risk import Level, RateModel, response_probability, score_window, window_type
    from turnout.models import ResponseStats
    from turnout.sim.runner import load_scenario

    store, sc = load_scenario(SCENARIO)
    now = datetime.fromisoformat(sc["clock_start"])
    rt = runtime.local_runtime("millbrook", clock=Clock(now), store=store)
    runtime.configure(rt)

    d = store.get_department("millbrook")
    members = [m for m in store.list_members("millbrook") if not m.opted_out]
    calls = store.list_calls("millbrook", now - timedelta(days=365))
    rate = RateModel.from_history(calls, now)

    rng = random.Random(seed)
    out: list[Window] = []

    for _ in range(n):
        # A window somewhere in the next year, at an hour that varies the way real demand does.
        start = now + timedelta(hours=rng.randrange(24 * 365))
        start = start.replace(minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=4)
        wt = window_type(start)

        # Who marked themselves available. Availability is higher out of working hours, which is the
        # whole shape of the problem: the roster looks best exactly when it is least true.
        base_avail = 0.35 if wt.endswith("day") and not wt.startswith("weekend") else 0.7
        available = []
        for m in members:
            if rng.random() > base_avail:
                continue
            s = m.response_stats.get(wt, ResponseStats())
            available.append((set(m.roles), response_probability(s.yes, s.no)))

        roles_only = [roles for roles, _ in available]
        feasible = is_feasible(roles_only, d.min_crew.fire)

        scored = score_window(start, end, available, d.min_crew.fire, rate, [])
        at_risk = scored.level in (Level.HIGH, Level.CRITICAL)

        # Ground truth: one draw. Each available person independently turns out or does not, and a
        # crew either forms from those who did or it does not.
        turned_out = [roles for roles, p in available if rng.random() < p]
        actually_failed = not is_feasible(turned_out, d.min_crew.fire)

        out.append(Window(start, available, feasible, at_risk, actually_failed))

    meta = {"members": len(members), "min_crew": dict(d.min_crew.fire),
            "history_days": rate.history_days, "seed": seed, "windows": n}
    return out, meta


def score(windows: list[Window]) -> dict:
    """How often each predictor was wrong, in the direction that costs a crew."""
    def confusion(predicted_at_risk):
        tp = sum(1 for w, p in zip(windows, predicted_at_risk, strict=True) if p and w.actually_failed)
        fp = sum(1 for w, p in zip(windows, predicted_at_risk, strict=True) if p and not w.actually_failed)
        fn = sum(1 for w, p in zip(windows, predicted_at_risk, strict=True) if not p and w.actually_failed)
        tn = sum(1 for w, p in zip(windows, predicted_at_risk, strict=True) if not p and not w.actually_failed)
        recall = tp / (tp + fn) if tp + fn else 0.0
        precision = tp / (tp + fp) if tp + fp else 0.0
        return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "recall": recall, "precision": precision,
                "missed": fn}

    baseline = confusion([not w.feasible_on_paper for w in windows])
    turnout = confusion([w.turnout_at_risk for w in windows])
    failures = sum(1 for w in windows if w.actually_failed)
    return {"failures": failures, "total": len(windows),
            "baseline": baseline, "turnout": turnout}


def render(s: dict, meta: dict) -> str:
    b, t = s["baseline"], s["turnout"]
    caught_extra = t["tp"] - b["tp"]
    lines = [
        START,
        "## Against the obvious alternative",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by "
        "`python -m evals.baseline_eval`.",
        "",
        "The alternative to all of this is a roster check: look at who marked themselves available, "
        "see whether those people can form a legal crew, and call the window covered if they can. "
        "Every volunteer scheduling tool does that. It is the incumbent, not a strawman.",
        "",
        "A member marking themselves available is saying they are not at work. It is not a promise "
        "to turn out, and published response rates for volunteer first responders run between 17 "
        "and 47 percent. So four available people can be a legal crew on paper and no crew at all "
        "at two on a Tuesday.",
        "",
        f"Over **{meta['windows']} simulated windows** for a {meta['members']} member department, "
        f"drawn against each member's own response history, **{s['failures']} could not have raised "
        f"a legal crew** if a call had come.",
        "",
        "That is a count of windows, not of failed calls. Most windows never get tested, because a "
        "small department expects well under one call in any four hours. The number being predicted "
        "is exposure, not outcome: how often the station could not have answered, whether or not "
        "anybody rang.",
        "",
        "| | Roster check | Turnout | ",
        "|---|---|---|",
        f"| Real failures caught | {b['tp']} of {s['failures']} | **{t['tp']} of {s['failures']}** |",
        f"| Recall | {b['recall']:.1%} | **{t['recall']:.1%}** |",
        f"| Failures it called fine | **{b['missed']}** | {t['missed']} |",
        f"| Precision | {b['precision']:.1%} | {t['precision']:.1%} |",
        "",
        f"**Turnout catches {t['tp'] / b['tp']:.1f} times as many as the roster check: "
        f"{t['tp']} against {b['tp']}.** Of the {b['missed']} exposed windows the roster check calls "
        f"covered, Turnout catches {caught_extra}. Those are the windows where enough people are on "
        "the board and not enough of them come.",
        "",
        "The roster check is not merely less sensitive. It is wrong in the one direction that "
        "matters, because the window it calls covered is the window nobody looks at again.",
        "",
        "Turnout pays for that with lower precision: it flags windows that would have held. That "
        "trade is deliberate and is the reason the interrupt budget exists in code. A flagged window "
        "that holds costs one text message. A missed one costs a response.",
        "",
        f"Ground truth is simulated, because nobody publishes per-member turnout records for a real "
        f"department. Each window is drawn once rather than averaged, the per-member probabilities "
        f"come from the same Beta posterior the product uses, and the seed is fixed at "
        f"`{meta['seed']}` so the number is reproducible rather than the best of several runs.",
        END,
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--windows", type=int, default=WINDOWS)
    a = ap.parse_args()

    windows, meta = build_windows(a.seed, a.windows)
    s = score(windows)
    body = render(s, meta)
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
