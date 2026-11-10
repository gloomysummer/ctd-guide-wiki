#!/usr/bin/env python3
"""Compare our published trade values against the live Vaulted Values X list.

WHY THIS EXISTS
---------------
`src/data/values.json` was read from the Vaulted Values X list in the
2026-10-25 video (refVideoId 7QBiS599euI). The publisher also maintains a live
list on their own site, and it moves. On 2026-11-04 a comparison showed 14 of
19 overlapping units disagreed, by as much as 3.6x (Headless TV Man 1,900 here
vs 525 there).

That matters beyond bookkeeping: the trade calculator compares units against
each other, so values from two different dates produce confident nonsense
("two 2x Lucky still don't buy one Headless TV Man"). Any new asset added to
that table has to arrive on the same footing as the ones already in it.

This script does not decide anything. It prints the diff and exits. Writing is
opt-in via --write, and even then it only touches `value`, `valueStatus` and the
`source` block; `demand`, `trend`, `tier` and every editorial string are left
alone because this source does not publish them.

`--write` also stamps `source.retrievedAt` on every row, not just the drifted
ones: a sync reads the whole list, and a provenance date that lags behind the
figures is how the page ends up citing a list it was not read from. The
`/values/` page derives its visible date from that field.

Usage:
    python3 scripts/sync-vvx-values.py                 # diff against live site
    python3 scripts/sync-vvx-values.py --from-file x.html
    python3 scripts/sync-vvx-values.py --write         # apply, then re-run gates

Exit code: 0 = no drift, 1 = drift found, 2 = fetch/parse failure.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VALUES = ROOT / "src" / "data" / "values.json"
SOURCE_URL = "https://cameraman-td.vaultedvaluesx.com/trade-calculator"

# The publisher's display names do not always match ours. Left side = their
# name (lowercased), right side = the id we already publish. Anything not in
# this map is matched by exact lowercase name; anything still unmatched is
# reported, never guessed.
ALIASES = {
    "spider tv": "tv-spider",
    "cinemaman titan": "titan-cinemaman",
    "large scientist cameraman": "large-scientist-cameraman",
}

# Same-ish name, but we cannot prove it is the same unit. These are reported
# and never applied: "Glitch plungerman" may well be a different unit from our
# "Glitch Cameraman", and a wrong merge silently invents a price.
UNCERTAIN_ALIASES = {
    "glitch plungerman": "glitch-cameraman",
    "videotaper titan": "upgraded-videotapper-prototype",
}

ITEM_RE = re.compile(
    r'\{"id":"[0-9a-f-]{36}","slug":"item-(?:[a-z]+-)?[0-9a-f-]{36}","name":"([^"]*)","category":"([^"]*)"'
)
VALUE_RE = re.compile(r'"displayFields":\[\{"id":"value","label":"Value","value":([0-9]+)')

# The app-router payload is shipped as a run of `self.__next_f.push([1,"..."])`
# calls, and the publisher's serialiser splits strings wherever it likes — a
# single item's `{"id":"<uuid>"` header can be torn across two calls. Unescaping
# the raw HTML without stitching the chunks back together silently loses those
# items (2026-11-10: it dropped Titan TV Man entirely and left Upgraded Titan TV
# Man pinned to the priceless duplicate, so the one unit the whole sync existed
# for came back with value None).
FLIGHT_RE = re.compile(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)')


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "ctd-guide-wiki/1.0 (+value-audit)"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def payload(html: str) -> str:
    """Reassemble the flight chunks into one JSON-ish string before parsing."""
    parts = FLIGHT_RE.findall(html)
    if not parts:
        return html.replace('\\"', '"')
    return "".join(json.loads(p) for p in parts)


def parse(html: str) -> list[dict]:
    """Pull item/value pairs out of the app-router payload.

    The page ships its item list inline as JSON with escaped quotes. Splitting
    on item boundaries before reading the value field is deliberate: a naive
    greedy regex pairs one item's name with the next item's number, which is
    exactly how a "Chaos = 3,650" reading appeared in one audit pass.
    """
    unescaped = payload(html)
    chunks = re.split(r'(?=\{"id":"[0-9a-f-]{36}","slug":"item-)', unescaped)
    items = []
    for chunk in chunks[1:]:
        head = ITEM_RE.match(chunk)
        if not head:
            continue
        value_match = VALUE_RE.search(chunk)
        items.append({
            "name": head.group(1),
            "category": head.group(2),
            "value": int(value_match.group(1)) if value_match else None,
        })
    return items


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--from-file", type=Path, help="parse a saved copy instead of fetching")
    ap.add_argument("--write", action="store_true", help="apply matched value changes")
    ap.add_argument("--as-of", default=date.today().isoformat(),
                    help="date stamped on every row's source.retrievedAt (default: today)")
    args = ap.parse_args(argv)

    try:
        html = args.from_file.read_text(encoding="utf-8", errors="ignore") if args.from_file else fetch(SOURCE_URL)
    except Exception as exc:
        print(f"ERROR: could not read source: {exc}", file=sys.stderr)
        return 2

    remote = [i for i in parse(html) if i["value"] is not None]
    if not remote:
        print("ERROR: parsed 0 priced items — the page shape probably changed.", file=sys.stderr)
        return 2

    ours = json.loads(VALUES.read_text(encoding="utf-8"))
    by_id = {u["id"]: u for u in ours}
    by_name = {u["name"].lower(): u for u in ours}
    by_name["speakerwoman"] = by_name.get("speakerwoman") or by_id.get("speakerwoman")

    matched, changed, unmatched_remote, uncertain = [], [], [], []
    for item in remote:
        key = item["name"].lower()
        if key in UNCERTAIN_ALIASES:
            uncertain.append((UNCERTAIN_ALIASES[key], item))
            continue
        target = by_id.get(ALIASES.get(key, "")) or by_name.get(key)
        if target is None:
            unmatched_remote.append(item)
            continue
        matched.append((target, item))
        if target.get("value") != item["value"]:
            changed.append((target, item))

    print(f"source      {args.from_file or SOURCE_URL}")
    print(f"remote      {len(remote)} priced items")
    print(f"our table   {len(ours)} rows ({sum(1 for u in ours if u.get('value'))} priced)")
    print(f"matched     {len(matched)}")
    print(f"drifted     {len(changed)}")
    print()

    if changed:
        print(f"{'unit':34s} {'ours':>8} {'remote':>8}  ratio")
        for target, item in sorted(changed, key=lambda p: -p[0].get("value", 0)):
            old = target.get("value") or 0
            ratio = f"x{item['value'] / old:.2f}" if old else "ours=0"
            print(f"{target['name']:34s} {old:>8} {item['value']:>8}  {ratio}")
        print()

    if unmatched_remote:
        print(f"on their list, no counterpart here ({len(unmatched_remote)}):")
        for item in unmatched_remote:
            print(f"  {item['name']:34s} {item['value']:>8}  [{item['category']}]")
        print()

    if uncertain:
        print(f"name looks close but identity unproven — needs a human call, not applied ({len(uncertain)}):")
        for our_id, item in uncertain:
            print(f"  theirs {item['name']!r} ({item['value']}) <-> ours {our_id!r}")
        print()

    if not args.write:
        print("dry run — nothing written. Re-run with --write to apply, then run the five gates.")
        return 1 if changed else 0

    for target, item in changed:
        target["value"] = item["value"]
        target["valueStatus"] = "published"
        target.setdefault("source", {})
        target["source"]["notes"] = (
            f"Re-synced to the live Vaulted Values X list on {args.as_of} "
            f"({SOURCE_URL}); previously {target.get('source', {}).get('notes', 'n/a')}"
        )[:400]

    # A sync reads the whole list, so every row's provenance moves to this date —
    # not just the rows whose number happened to change. Leaving retrievedAt behind
    # is how the page ends up sourced to a list the figures were not read from.
    for u in ours:
        src = u.setdefault("source", {})
        src["retrievedAt"] = args.as_of
        src["url"] = SOURCE_URL

    VALUES.write_text(json.dumps(ours, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(changed)} changes to {VALUES.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
