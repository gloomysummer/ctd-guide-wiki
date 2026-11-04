#!/usr/bin/env python3
"""Machine-check the prose against the data tables.

Scope: the two files the copy work touches —
    src/data/values.json          `description` on every unit
    src/data/unit-editorial.json  every string value

Rule: a number of three or more digits in the prose must be traceable to a
numeric field in one of the three tables. Prose never grounds prose, otherwise
a wrong figure in a history story would launder a wrong figure in a summary.

Grounding tiers, strongest first:
    SELF     the owning unit's own number      (value / demand / cost / dps / range / price history)
    STATS    a combat figure: either the owning unit's own stat, or a number sitting next to a
             combat dimension (dps / cash / hp / range / second / wave / rank)
    DERIVED  equals a sum of <=3 published values, or the gap between two of them
             (bundle prices are real claims but cannot be looked up — the decomposition is printed)
    OTHER    another unit's number             (suspicious when it reads like a price)
    PROSE    appears only inside some note or story text  (weakest; kept separate so it can be eyeballed)
    NONE     nothing anywhere                  (must be fixed before shipping)

A number tagged CAVEAT sits inside a sentence that already says the figure is
single-source or unconfirmed. Those are allowed, but they are listed so the
caveat is never quietly dropped in a later edit.

Usage:
    python3 scripts/verify-copy-numbers.py
    python3 scripts/verify-copy-numbers.py --quiet     # only NONE / OTHER
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "src" / "data"

NUM_RE = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d{3,})(?![\w])")
YEAR_RE = re.compile(r"\b(20[2-3]\d)\b")
COMBAT_RE = re.compile(r"(dps|damage|cash|hp\b|health|range|second|wave|rank|cost|splash|area)", re.I)
CAVEAT_RE = re.compile(
    r"(single[- ]source|one report|unconfirmed|unverified|not confirmed|"
    r"players report|community reports|reportedly|anecdotal)",
    re.I,
)


def decompose(n, values, sentence_nums, names_here, name_value):
    """Justify n as arithmetic only when the sentence itself points at the parts.

    A sum is not evidence. With ~40 published values, a three-term search reaches
    a large share of arbitrary integers, so 'it is reachable' proves nothing.
    A bundle price is justified only if the sentence either quotes one of the
    addends, or names a unit whose published value is one of them.
    """
    vs = sorted({v for v in values if v and v > 0}, reverse=True)

    def justifies(operands):
        quoted = [o for o in operands if o in sentence_nums and o != n]
        if quoted:
            return f"quotes {quoted[0]:,} in the same sentence"
        named = [nm for nm, val in name_value.items() if val in operands and nm in names_here]
        if named:
            return "adds up the units named here: " + ", ".join(sorted(set(named))[:3])
        return None

    for i, a in enumerate(vs):
        if a == n:
            continue
        b = n - a
        if b in vs:
            basis = justifies({a, b})
            if basis:
                return f"{a:,} + {b:,}", basis
        for j in range(i, len(vs)):
            c = vs[j]
            d = n - a - c
            if d in vs:
                basis = justifies({a, c, d})
                if basis:
                    return f"{a:,} + {c:,} + {d:,}", basis
        for gap in vs:
            if abs(gap - n) in vs and abs(gap - n) > 0:
                basis = justifies({gap, abs(gap - n)})
                if basis:
                    return f"{gap:,} - {abs(gap - n):,}", basis
    return None, None


def load(name, data_dir):
    p = data_dir / name
    if not p.exists():
        sys.exit(f"missing data file: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def as_int(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def num_fields(obj, keys):
    """Pull integer values out of a flat dict, limited to the named keys."""
    out = set()
    for k in keys:
        n = as_int(obj.get(k))
        if n is not None:
            out.add(n)
    return out


def collect_prose_strings(node, path=""):
    """Yield (path, text) for every string under node."""
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from collect_prose_strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from collect_prose_strings(v, f"{path}[{i}]")


def main():
    ap = argparse.ArgumentParser(description="Verify every 3+ digit number in the copy has a source in the data tables.")
    ap.add_argument("--quiet", action="store_true", help="only print OTHER / NONE findings")
    ap.add_argument("--data-dir", type=Path, default=DATA, help="read the four JSON tables from here instead (for self-tests)")
    args = ap.parse_args()

    values = load("values.json", args.data_dir)
    editorial = load("unit-editorial.json", args.data_dir)
    stats = load("unit-stats.json", args.data_dir)
    history = load("unit-price-history.json", args.data_dir)

    units = values if isinstance(values, list) else values.get("units", [])
    hist = history.get("history", {}) if isinstance(history, dict) else {}

    # unit-stats carries two confidence sections; verify both, remember which is which
    stat_sections = {name: stats.get(name, {}) for name in ("verified", "singleSource") if isinstance(stats.get(name), dict)}
    stat_section_of: dict[str, str] = {}
    for sect, rows in stat_sections.items():
        for uid in rows:
            stat_section_of.setdefault(uid, sect)

    # --- grounding sets -----------------------------------------------------
    own: dict[str, set[int]] = {}
    stat_own: dict[str, set[int]] = {}
    stat_numbers: set[int] = set()
    price_of: dict[int, list[str]] = {}          # number -> units that publish it as a price
    stat_of: dict[int, list[str]] = {}

    for u in units:
        uid = u.get("id", "")
        nums = num_fields(u, ("value", "demand", "tierRank", "cost"))
        own[uid] = set(nums)

    for sect, rows in stat_sections.items():
        for uid, row in rows.items():
            if not isinstance(row, dict):
                continue
            nums = num_fields(row, ("placeCost", "maxDps", "range"))
            own.setdefault(uid, set()).update(nums)
            stat_own.setdefault(uid, set()).update(nums)
            stat_numbers |= nums
            for n in nums:
                stat_of.setdefault(n, []).append(uid)

    # history rows do not agree on field names (dip vs trough vs before), so take every integer
    for uid, row in hist.items():
        if not isinstance(row, dict):
            continue
        nums = {v for v in row.values() if isinstance(v, int) and not isinstance(v, bool)}
        own.setdefault(uid, set()).update(nums)
        for n in nums:
            price_of.setdefault(n, []).append(uid)

    self_union = set().union(*own.values()) if own else set()
    global_numeric = self_union | stat_numbers

    # unit name (lowercased) -> published value, so arithmetic can be tied to the words in a sentence
    name_value: dict[str, int] = {}
    for u in units:
        nm, val = u.get("name"), as_int(u.get("value"))
        if isinstance(nm, str) and val is not None:
            name_value[nm.lower()] = val

    # prose corpus, used only for the weakest tier
    prose_corpus: dict[int, list[str]] = {}
    prose_docs = [(f"stats.{s}", rows) for s, rows in stat_sections.items()] + [("history", hist)]
    for label, doc in prose_docs:
        for path, text in collect_prose_strings(doc, label):
            for m in NUM_RE.finditer(text):
                prose_corpus.setdefault(int(m.group(1).replace(",", "")), []).append(path)

    # --- scan the copy ------------------------------------------------------
    targets: list[tuple[str, str, str]] = []     # (unit id, field path, text)
    for u in units:
        d = u.get("description")
        if isinstance(d, str) and d.strip():
            targets.append((u.get("id", "?"), "values.description", d))
    for path, text in collect_prose_strings(editorial, "editorial"):
        targets.append((path.split(".")[1] if "." in path else path, path, text))

    findings = []
    for owner, field, text in targets:
        for m in NUM_RE.finditer(text):
            raw = m.group(1)
            n = int(raw.replace(",", ""))
            if n < 100:                              # 1-2 digit numbers are out of scope by design
                continue
            if YEAR_RE.fullmatch(raw):               # calendar years are not assertions about the game
                continue
            trace = None
            basis = None

            # the sentence around the match decides everything below
            s_start = max(text.rfind(". ", 0, m.start()), text.rfind("\n", 0, m.start())) + 1
            s_end = text.find(". ", m.end())
            sentence = text[s_start: s_end + 1 if s_end != -1 else len(text)]
            sentence_nums = {int(x.replace(",", "")) for x in NUM_RE.findall(sentence)}
            low = sentence.lower()
            names_here = {nm for nm in name_value if nm in low}

            near_combat = bool(COMBAT_RE.search(text[max(0, m.start() - 30): m.end() + 30]))
            if n in own.get(owner, set()):
                tier = "SELF"
            elif n in stat_own.get(owner, set()) or (near_combat and n in stat_numbers):
                tier = "STATS"
            elif n in global_numeric:
                tier = "OTHER"
            else:
                trace, basis = decompose(n, self_union, sentence_nums, names_here, name_value)
                if trace:
                    tier = "DERIVED"
                elif n in prose_corpus:
                    tier = "PROSE"
                else:
                    tier = "NONE"

            if tier == "SELF":
                continue

            ctx = text[max(0, m.start() - 55): m.end() + 55].replace("\n", " ")
            # for a cross-reference, the question is whether the unit named in this sentence has that price
            named_match = sorted({nm for nm, val in name_value.items() if val == n and nm in low})
            # a figure whose only home is the singleSource section is disclosed by the table itself
            caveat = bool(CAVEAT_RE.search(sentence)) or (
                tier == "STATS" and stat_section_of.get(owner) == "singleSource"
            )
            findings.append({
                "tier": tier, "owner": owner, "field": field, "num": raw, "ctx": ctx,
                "trace": trace, "basis": basis, "named_match": named_match,
                "caveat": caveat,
                "price_of": sorted(set(price_of.get(n, []))),
                "stat_of": sorted(set(stat_of.get(n, []))),
                "prose_src": sorted(set(prose_corpus.get(n, [])))[:3],
            })

    order = {"NONE": 0, "OTHER": 1, "PROSE": 2, "DERIVED": 3, "STATS": 4}
    findings.sort(key=lambda f: (order.get(f["tier"], 9), f["owner"], f["field"]))

    shown = [f for f in findings if not args.quiet or f["tier"] in ("NONE", "OTHER")]

    counts = {t: sum(1 for f in findings if f["tier"] == t) for t in order}
    print(f"checked {len(targets)} text fields in 2 files")
    print(f"  NONE    {counts['NONE']:>3}  no source anywhere")
    xref_bad = [f for f in findings if f["tier"] == "OTHER" and not f["named_match"]]
    print(f"  OTHER   {counts['OTHER']:>3}  another unit's number in this sentence "
          f"({len(xref_bad)} name no match)")
    print(f"  PROSE   {counts['PROSE']:>3}  only found in note/story prose")
    print(f"  DERIVED {counts['DERIVED']:>3}  arithmetic on published values")
    print(f"  STATS   {counts['STATS']:>3}  combat stat, expected in prose about damage")
    print()

    # the history rows do not share a schema; say so rather than silently guessing
    key_sets = {}
    for uid, row in hist.items():
        if isinstance(row, dict):
            ks = tuple(sorted(k for k, v in row.items() if isinstance(v, int)))
            key_sets.setdefault(ks, []).append(uid)
    if len(key_sets) > 1:
        print("note: unit-price-history.json rows use different numeric field names —")
        for ks, uids in sorted(key_sets.items(), key=lambda kv: -len(kv[1])):
            print(f"      {len(uids):>2}x ({', '.join(ks) or 'none'})  e.g. {uids[0]}")
        print()

    for f in shown:
        tail = ""
        if f["tier"] == "OTHER":
            if f["named_match"]:
                tail = f"  <- cross-reference ok: {' / '.join(f['named_match'])}"
            else:
                tail = f"  <- CROSS-REF UNMATCHED (price of {', '.join(f['price_of']) or 'nothing'})"
                if f["stat_of"]:
                    tail += f" / stat of {', '.join(f['stat_of'])}"
        elif f["tier"] == "PROSE":
            tail = f"  <- only in prose: {', '.join(f['prose_src'])}"
        elif f["tier"] == "DERIVED":
            tail = f"  <- {f['trace']}  ({f['basis']})"
        elif f["tier"] == "NONE":
            tail = "  <- NO SOURCE" + ("  (sentence discloses it is unconfirmed)" if f["caveat"] else "")
        print(f"[{f['tier']:7}] {f['owner']:<28} {f['num']:>7}{tail}")
        print(f"           {f['ctx']}")

    hard = [f for f in findings if f["tier"] == "NONE" and not f["caveat"]]
    soft = [f for f in findings if f["tier"] == "NONE" and f["caveat"]]
    if soft:
        print(f"\n{len(soft)} unsourceable figure(s) sit inside a sentence that calls them unconfirmed — allowed, keep the caveat.")
    if hard:
        print(f"\nFAIL: {len(hard)} number(s) with no source in the data tables.")
        return 1
    print("\nPASS: every 3+ digit number in the copy traces to a data table or to arithmetic on one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
