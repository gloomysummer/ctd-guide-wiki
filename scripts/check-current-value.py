#!/usr/bin/env python3
"""Check that the copy actually moved when the table moved.

`verify-copy-numbers.py` answers "does this figure have a source?". This answers a
different question: "when a unit's value changed, did the sentences that describe
it change too?" A description may legitimately mention the old number — "up from
8,000 on Oct 25" is the whole point of a price history — so the test is not
absence. It is:

  1. the new value must appear in the unit's `quickAnswer` and `description`;
  2. the old value must not sit behind a present-tense verb, which would assert
     it as the price today.

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
        if nv and f"{nv:,}" not in desc:
            missing_new.append(f"{uid}.description does not mention {nv:,}")

        if ov:
            for label, text in (("quickAnswer", qa), ("description", desc)):
                hit = asserts_as_current(text, ov)
                if hit:
                    stale_claim.append(f"{uid}.{label}: {hit}")

    print(f"units whose value moved : {len(moved)}")
    print(f"copy missing the new price: {len(missing_new)}")
    print(f"old price asserted as current: {len(stale_claim)}")
    print()

    for line in missing_new:
        print("  MISSING ", line)
    for line in stale_claim:
        print("  STALE   ", line)

    if missing_new or stale_claim:
        print(f"\nFAIL: {len(missing_new)} missing mention(s), {len(stale_claim)} stale claim(s).")
        return 1
    print("\nPASS: every moved unit states its new price, and no old price is presented as current.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
