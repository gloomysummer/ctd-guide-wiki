#!/usr/bin/env python3
"""Decide whether ctd-guide.wiki is ready to join the site-update-loop pipeline.

WHY THIS EXISTS
---------------
2026-11-04: the site was asked "can the daily update loop be switched on yet?".
The answer was no, and the reason was arithmetic, not opinion — `page_build_queue`
drops any query below `min_impressions=20`, and the largest single query on the
whole property was 12 impressions. Wiring the site into the loop at that volume
produces an empty queue every day, which reads as "nothing to do" forever.

So the switch-on decision is reduced to three hard, checkable numbers instead of
a judgement call. This script prints them and a GO / NO-GO verdict.

TRIGGERS (any one is enough to switch on)
  1. a single query reaches 20+ impressions      -> the queue can produce candidates
  2. any URL other than `/` earns an impression  -> a subpage is competing on its own
  3. site-wide impressions reach 300              -> enough surface for cluster decisions

The thresholds are not tuning knobs to fidget with: #1 is copied from
`page_build_queue.py`'s default, #2 is the signal we actually want to see
(`/values/` should be taking the calculator queries instead of the homepage),
#3 is roughly the point where a 7-day window stops being pure noise.

Usage:
    python3 scripts/watch-gsc-trigger.py
    python3 scripts/watch-gsc-trigger.py --days 28 --json

Exit code: 0 = GO (at least one trigger fired), 1 = NO-GO, 2 = data/auth error.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

SITE_URL = "sc-domain:ctd-guide.wiki"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GSC_QUERY_ENDPOINT = "https://searchconsole.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query"

TRIGGER_QUERY_IMPRESSIONS = 20.0   # page_build_queue.py min_impressions default
TRIGGER_ANY_SUBPAGE = 1.0          # any non-homepage URL with >= 1 impression
TRIGGER_SITE_IMPRESSIONS = 300.0   # weekly-ish noise floor for cluster work


def _api_post(url: str, payload: dict, token: str, timeout: int = 40) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _access_token(client_file: str, token_file: str) -> str:
    """Refresh the stored OAuth token. The cached access_token expires hourly."""
    with open(client_file, encoding="utf-8") as fh:
        client = json.load(fh)
    client = client.get("installed") or client.get("web") or client
    with open(token_file, encoding="utf-8") as fh:
        stored = json.load(fh)

    body = urllib.parse.urlencode({
        "client_id": client["client_id"],
        "client_secret": client["client_secret"],
        "refresh_token": stored["refresh_token"],
        "grant_type": "refresh_token",
    }).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_ENDPOINT, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))["access_token"]


def _rows(token: str, start: str, end: str, dims: list[str]) -> list[dict]:
    url = GSC_QUERY_ENDPOINT.format(site=urllib.parse.quote(SITE_URL, safe=""))
    data = _api_post(url, {
        "startDate": start,
        "endDate": end,
        "dimensions": dims,
        "rowLimit": 200,
        "dataState": "final",
    }, token)
    return data.get("rows") or []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--days", type=int, default=28, help="lookback window (default 28)")
    ap.add_argument("--lag", type=int, default=3, help="days to drop from the end (GSC lag, default 3)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--token-file",
                    default=os.path.expanduser("~/.gemini/config/google-oauth-token.json"))
    ap.add_argument("--client-file",
                    default=os.path.expanduser("~/.gemini/config/google-oauth-client.json"))
    args = ap.parse_args(argv)

    end = date.today() - timedelta(days=args.lag)
    start = end - timedelta(days=args.days - 1)

    try:
        token = _access_token(args.client_file, args.token_file)
        query_rows = _rows(token, start.isoformat(), end.isoformat(), ["query"])
        page_rows = _rows(token, start.isoformat(), end.isoformat(), ["page"])
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError) as exc:
        print(f"ERROR: could not read Search Console: {exc}", file=sys.stderr)
        return 2

    total_imp = sum(float(r.get("impressions", 0)) for r in query_rows)
    total_clicks = sum(float(r.get("clicks", 0)) for r in query_rows)
    top_query = max(query_rows, key=lambda r: float(r.get("impressions", 0)), default=None)
    max_q_imp = float(top_query.get("impressions", 0)) if top_query else 0.0

    subpages = [r for r in page_rows
                if r["keys"][0].rstrip("/") != "https://ctd-guide.wiki"
                and float(r.get("impressions", 0)) >= TRIGGER_ANY_SUBPAGE]

    triggers = {
        "single_query_20imp": {
            "fired": max_q_imp >= TRIGGER_QUERY_IMPRESSIONS,
            "value": max_q_imp,
            "threshold": TRIGGER_QUERY_IMPRESSIONS,
            "detail": top_query["keys"][0] if top_query else None,
        },
        "subpage_impressions": {
            "fired": bool(subpages),
            "value": len(subpages),
            "threshold": 1,
            "detail": [{"page": r["keys"][0], "impressions": float(r.get("impressions", 0))}
                       for r in subpages],
        },
        "site_impressions_300": {
            "fired": total_imp >= TRIGGER_SITE_IMPRESSIONS,
            "value": total_imp,
            "threshold": TRIGGER_SITE_IMPRESSIONS,
            "detail": None,
        },
    }
    go = any(t["fired"] for t in triggers.values())

    report = {
        "site": SITE_URL,
        "window": {"start": start.isoformat(), "end": end.isoformat(), "days": args.days},
        "clicks": total_clicks,
        "impressions": total_imp,
        "attributable_queries": len(query_rows),
        "top_query": ({"query": top_query["keys"][0],
                       "impressions": max_q_imp,
                       "position": round(float(top_query.get("position", 0)), 1)}
                      if top_query else None),
        "pages_with_impressions": len(page_rows),
        "triggers": triggers,
        "verdict": "GO" if go else "NO-GO",
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if go else 1

    print(f"ctd-guide.wiki  {start} -> {end}  ({args.days}d, GSC lag {args.lag}d)")
    print(f"  clicks {total_clicks:.0f} | impressions {total_imp:.0f} | "
          f"attributable queries {len(query_rows)} | URLs with impressions {len(page_rows)}")
    if top_query:
        print(f"  top query: {top_query['keys'][0]!r} "
              f"{max_q_imp:.0f} imp @ pos {float(top_query.get('position', 0)):.1f}")
    print()
    for name, t in triggers.items():
        mark = "FIRED " if t["fired"] else "  -   "
        print(f"  [{mark}] {name}: {t['value']} vs threshold {t['threshold']}")
    print()
    if go:
        print("VERDICT: GO — switch the site into the update loop "
              "(config.json entry + launchd plist).")
    else:
        print("VERDICT: NO-GO — do not wire the loop yet. An empty queue every morning "
              "is indistinguishable from 'nothing to do'.")
    return 0 if go else 1


if __name__ == "__main__":
    sys.exit(main())
