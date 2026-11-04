#!/usr/bin/env python3
"""Check that the copy actually moved when the table moved.

`verify-copy-numbers.py` answers "does this figure have a source?". This answers a
different question: "when a unit's value changed, did the sentences that describe
it change too?" A description may legitimately mention the old number — "up from
8,000 on Oct 25" is the whole point of a price history — so the test is not
absence. It is:

  1. the new value must appear in the unit's `quickAnswer`, which is the page's
     lead sentence and the one place a reader looks for the number;
  2. neither field may present the old value as the price today;
  3. no *other* unit's copy may quote this unit's old value as if it were
     current. A unit that did not change price can still go stale because a
     unit it compares itself against did — "ten points below Titan Cinemaman
     (460 pts)" keeps its arithmetic while the 460 becomes fiction.

`description` is not required to quote a figure at all — it sits next to the
value on the card, and "the cheapest mythic on the list" is a perfectly good
sentence. It is only barred from quoting the wrong one.

Sentences anchored to a past date are exempt throughout: on 25 October the old
figure was the real figure, and saying so is the point of a price history.

Usage:
    python3 scripts/check-current-value.py                 # against the last commit
    python3 scripts/check-current-value.py --base 8c961d6  # against a given commit

Exit code: 0 = every moved unit's copy moved with it, 1 = at least one did not.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "src" / "data"

# Present-tense ways of stating a price. Past forms (stood at, fell to, climbed
# to, listed at) are deliberately absent: those are history and must be allowed.
CURRENT_RE = re.compile(
    r"\b(?:holds?|holding|stands? at|sits? at|is valued at|valued at|trades? at|"
    r"carries|currently|now worth|is now|worth)\b[^.]{0,24}$",
    re.I,
)


def load(ref: str | None, name: str):
    path = DATA / name
    if ref is None:
        return json.loads(path.read_text(encoding="utf-8"))
    out = subprocess.run(
        ["git", "show", f"{ref}:src/data/{name}"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if out.returncode != 0:
        sys.exit(f"cannot read {name} at {ref}: {out.stderr.strip()}")
    return json.loads(out.stdout)


def asserts_as_current(text: str, num: int) -> str | None:
    """Return the offending fragment if `num` is stated in the present tense."""
    pat = re.compile(rf"(?<![\d,]){num:,}(?![\d,])")
    for m in pat.finditer(text):
        window = text[max(0, m.start() - 40): m.start()]
        if CURRENT_RE.search(window):
            return text[max(0, m.start() - 45): m.end() + 15].strip()
    return None


PAST_RE = re.compile(
    r"(oct(?:ober)?\.?\s*\d|\d{1,2}\s+october|25 october|at launch|on release|on debut|"
    r"debut|prior to update|before update|after update|first listed|listed at)",
    re.I,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="HEAD", help="git ref holding the previous values (default: HEAD)")
    args = ap.parse_args()

    old_units = {u["id"]: u for u in load(args.base, "values.json")}
    new_units = {u["id"]: u for u in load(None, "values.json")}
    editorial = load(None, "unit-editorial.json")

    moved = [
        (uid, old_units[uid]["value"], u["value"])
        for uid, u in new_units.items()
        if old_units.get(uid, {}).get("value") != u["value"]
    ]
    if not moved:
        print("no unit changed value against", args.base, "— nothing to check")
        return 0

    missing_new, stale_claim = [], []
    for uid, ov, nv in sorted(moved, key=lambda r: -r[2]):
        u = new_units[uid]
        qa = editorial.get(uid, {}).get("quickAnswer", "")
        desc = u.get("description", "")

        if nv and f"{nv:,}" not in qa:
            missing_new.append(f"{uid}.quickAnswer does not mention {nv:,}")

        if ov:
            for label, text in (("quickAnswer", qa), ("description", desc)):
                hit = asserts_as_current(text, ov)
                if hit:
                    stale_claim.append(f"{uid}.{label}: {hit}")

    print(f"units whose value moved : {len(moved)}")
    print(f"copy missing the new price: {len(missing_new)}")
    print(f"old price asserted as current: {len(stale_claim)}")

    # 3. a unit that never moved can still quote a stale figure for one that did
    old_values = {uid: ov for uid, ov, _ in moved if ov}
    names = {uid: u["name"].lower() for uid, u in new_units.items()}
    stale_xref = []
    for uid, fields in editorial.items():
        if not isinstance(fields, dict):
            continue
        for field, text in fields.items():
            if not isinstance(text, str):
                continue
            for sentence in re.split(r"(?<=[.!?])\s+", text):
                if PAST_RE.search(sentence):
                    continue
                low = sentence.lower()
                for other, ov in old_values.items():
                    if other == uid or names.get(other, "\0") not in low:
                        continue
                    # must read as a price: "70 pts" or "70 points". Without this,
                    # "wave 35 ... Scientist Cameraman" looks like a quote of 35.
                    if re.search(rf"(?<![\d,]){ov:,}\s*(?:pts|points|pt)\b", sentence, re.I):
                        stale_xref.append(f"{uid}.{field} quotes {other} at {ov:,}: {sentence.strip()[:120]}")

    print(f"stale figure for another unit: {len(stale_xref)}")
    print()

    for line in missing_new:
        print("  MISSING ", line)
    for line in stale_claim:
        print("  STALE   ", line)
    for line in stale_xref:
        print("  XREF    ", line)

    if missing_new or stale_claim or stale_xref:
        print(f"\nFAIL: {len(missing_new)} missing mention(s), {len(stale_claim)} stale claim(s), "
              f"{len(stale_xref)} stale cross-reference(s).")
        return 1
    print("\nPASS: every moved unit states its new price, and no old price is presented as current.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
