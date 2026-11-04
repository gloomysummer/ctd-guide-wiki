#!/usr/bin/env python3
"""List every sentence whose number contradicts the value table.

REPORT ONLY. It does not rewrite anything, and that is deliberate: an earlier
version swapped the numbers automatically and the first review killed it. In the
same corpus, "250" was also a DPS figure ("1,250 area DPS") and a component of
arithmetic ("460 pts ... a 455-point win"), so a blind substitution silently
corrupted combat data and made the sums wrong. Copy like this has to be rewritten
by someone who can read the sentence, not by a regex.

What it produces is the worklist for that rewrite: which sentences assert a
current price (must move), and which are anchored to a date or a recorded move
(must stay exactly as written).

`values.json` is re-read from HEAD, so it works before any re-sync is applied:
compare the committed table against a fresh sync run in the same session.

`values.json` drives numbers that appear in three places: the value column, each
unit's one-line description, and the long-form editorial prose. When the numbers
move, sentences that assert "its 7,000-point tag" become quietly wrong — the
table says 4,200 and the paragraph below it still says 7,000.

The hard part is that the same prose also records genuine history ("Listed at
6,000 on release, peaked near 8,800"), and the editorial was written against the
25 October list on purpose. Those sentences are true and must not be rewritten:
changing 8,000 to 10,000 inside "holding 8,000 trade points ... on the dated
October 25 list" would replace a correct historical statement with a false one.

So the rule is sentence-level:
  * sentence asserts a current price  -> substitute the number
  * sentence is anchored to a date or a movement -> leave it alone, report it

What it never touches: `unit-price-history.json` (it carries `listDate` and is
the dated record by design).

Usage:
    python3 scripts/refresh-value-copy.py          # report only
    python3 scripts/refresh-value-copy.py --write

Exit: 0 = nothing pending, 1 = changes pending or history still quoted.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VALUES = ROOT / "src" / "data" / "values.json"
EDITORIAL = ROOT / "src" / "data" / "unit-editorial.json"

HISTORY_MARKERS = re.compile(
    r"(october 25|oct 25|dated|on release|launch|peaked|bottomed|stabilized|"
    r"listed at|halved|climbed|doubled|slid|fell|dropped to|rose from|spiked|"
    r"swung|went from|down from|gave it back|revision)",
    re.I,
)


def committed_values() -> dict[str, int]:
    try:
        raw = subprocess.run(["git", "show", "HEAD:src/data/values.json"],
                             cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError:
        print("ERROR: cannot read HEAD:src/data/values.json", file=sys.stderr)
        sys.exit(2)
    return {u["id"]: u.get("value", 0) for u in json.loads(raw)}


def variants(n: int) -> list[str]:
    return [f"{n:,}", str(n)] if n >= 1000 else [str(n)]


def rewrite(text: str, old: int, new: int, uid: str,
            applied: list, skipped: list) -> str:
    parts = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if HISTORY_MARKERS.search(sentence):
            if any(v in sentence for v in variants(old)):
                skipped.append((uid, sentence.strip()))
            parts.append(sentence)
            continue
        for token in variants(old):
            if token in sentence:
                new_token = f"{new:,}" if "," in token else str(new)
                applied.append((uid, sentence.strip(), token, new_token))
                sentence = sentence.replace(token, new_token)
        parts.append(sentence)
    return " ".join(parts)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--against", type=Path,
                    help="a synced values.json to compare against HEAD, instead of the working copy")
    args = ap.parse_args(argv)

    before = committed_values()
    rows = json.loads((args.against or VALUES).read_text(encoding="utf-8"))
    editorial = json.loads(EDITORIAL.read_text(encoding="utf-8"))
    values = {u["id"]: u for u in rows}

    moved = {uid: (before.get(uid, 0), u.get("value", 0))
             for uid, u in values.items()
             if before.get(uid, 0) != u.get("value", 0) and u.get("value", 0) > 0}
    if not moved:
        print("nothing moved since HEAD — nothing to rewrite")
        return 0

    applied: list = []
    skipped: list = []

    for uid, (old, new) in moved.items():
        if not old:
            continue
        if values[uid].get("description"):
            values[uid]["description"] = rewrite(
                values[uid]["description"], old, new, uid, applied, skipped)
        for field, text in list(editorial.get(uid, {}).items()):
            if isinstance(text, str) and text:
                editorial[uid][field] = rewrite(text, old, new, uid, applied, skipped)

    print(f"units whose value moved : {len(moved)}")
    print(f"sentences asserting a current price (must move) : {len(applied)}")
    print(f"sentences anchored to a date or a move (must stay) : {len(skipped)}")

    if applied:
        print("\n-- must move: these state the price as it is now --")
        for uid, sentence, old_t, new_t in applied:
            print(f"  {uid}: {old_t} -> {new_t}  | {sentence[:110]}")

    if skipped:
        print("\n-- must stay: these record a date or a past move --")
        seen = set()
        for uid, sentence in skipped:
            key = (uid, sentence[:60])
            if key in seen:
                continue
            seen.add(key)
            print(f"  {uid}: {sentence[:130]}")

    print("\nreport only — no files written. See the module docstring for why.")
    return 1 if (applied or skipped) else 0


if __name__ == "__main__":
    sys.exit(main())
