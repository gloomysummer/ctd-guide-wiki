#!/usr/bin/env python3
"""Static internal link checker for the built site (KI-55).

Scans dist/ HTML files, extracts href/src attributes, and verifies every
INTERNAL target exists on disk. External URLs are counted but not fetched
(network false positives are exactly what the grey rollout avoids).

Rollout policy (Round 40 consensus): REPORT-ONLY. Exit code stays 0 even
when broken links are found; pass --strict (future gate use) to exit 1.
Run after `pnpm build` / `npm run build`.

Usage:
    python3 scripts/check-links.py [--strict] [--output report.json] [--dist DIR]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, unquote

ATTR_RE = re.compile(r'(?:href|src)\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
SKIP_PREFIXES = ("mailto:", "tel:", "javascript:", "data:", "#")
EXTERNAL_RE = re.compile(r"^(https?:)?//", re.IGNORECASE)


def candidates_for(base: Path) -> list[Path]:
    """A URL path may resolve to several on-disk shapes; all are accepted."""
    out = [base]
    if base.suffix == "" or base.suffix == ".html":
        out.append(base / "index.html")
        out.append(base.with_suffix(".html"))
    return out


def resolve_base(dist: Path, page_rel: Path, path: str) -> Path:
    if path.startswith("/"):
        return dist / path.lstrip("/")
    return dist / page_rel.parent / path


def load_redirects(repo_root: Path) -> dict[str, str]:
    """Parse public/_redirects (Cloudflare Pages format): 'source target 301'.

    KI-61 follow-up (Round 43 review): a slug that 301s to a real page is a
    resolved URL, not a broken link. Keys are normalized without trailing slash.
    """
    redirects: dict[str, str] = {}
    rf = repo_root / "public" / "_redirects"
    if not rf.is_file():
        return redirects
    for line in rf.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) == 3 and parts[2] in ("301", "302"):
            redirects[parts[0].rstrip("/")] = parts[1]
    return redirects


def check(dist: Path) -> dict:
    pages = sorted(dist.rglob("*.html"))
    repo_root = dist.parent
    redirects = load_redirects(repo_root)
    broken: list[dict] = []
    checked = 0
    external = 0
    anchors_skipped = 0
    dynamic_skipped = 0
    via_redirect = 0

    for page in pages:
        page_rel = page.relative_to(dist)
        html = page.read_text(encoding="utf-8", errors="replace")
        seen: set[str] = set()
        for raw in ATTR_RE.findall(html):
            link = raw.strip()
            if link in seen:
                continue
            seen.add(link)
            if link.startswith("#") or not link:
                anchors_skipped += 1
                continue
            if "${" in link or "{{" in link:
                # inline-JS template literals extracted from <script>/template
                # strings - not real URLs, would be false positives
                dynamic_skipped += 1
                continue
            if link.startswith(SKIP_PREFIXES):
                continue
            if EXTERNAL_RE.match(link):
                external += 1
                continue
            checked += 1
            parsed = urlparse(link)
            path = unquote(parsed.path)
            base = resolve_base(dist, page_rel, path)
            if any(c.is_file() for c in candidates_for(base)):
                continue
            # 301 白名单：链接路径命中 _redirects 源 = 有落地页（但不 ideal，
            # 内链最好直指最终 URL —— 单独计数供人工收敛）
            if f"/{path.strip('/')}".rstrip("/") in redirects or path.rstrip("/") in redirects:
                via_redirect += 1
                continue
            broken.append({
                "page": str(page_rel),
                "link": link,
                "resolved": str(base.relative_to(dist)),
                "reason": "target not found in dist" + (f" (fragment #{parsed.fragment})" if parsed.fragment else "") + (" (query ignored)" if parsed.query else ""),
            })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dist": str(dist),
        "pages_scanned": len(pages),
        "internal_links_checked": checked,
        "external_links_counted": external,
        "anchors_skipped": anchors_skipped,
        "dynamic_skipped": dynamic_skipped,
        "resolved_via_redirect": via_redirect,
        "broken_count": len(broken),
        "broken": broken,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="KI-55 static internal link check (report-only by default)")
    ap.add_argument("--strict", action="store_true", help="exit 1 when broken links are found")
    ap.add_argument("--output", help="write the JSON report to this path")
    ap.add_argument("--dist", help="dist directory (default: <repo>/dist)")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    dist = Path(args.dist).resolve() if args.dist else repo_root / "dist"
    if not dist.is_dir():
        print(f"ERROR: dist not found: {dist} (run the build first)", file=sys.stderr)
        return 2

    report = check(dist)
    print(f"🔗 Link check: {report['pages_scanned']} pages, {report['internal_links_checked']} internal links, "
          f"{report['external_links_counted']} external (not fetched), {report['anchors_skipped']} pure anchors skipped, "
          f"{report['dynamic_skipped']} JS templates skipped, {report['resolved_via_redirect']} via 301")
    if report["broken_count"]:
        print(f"❌ Broken internal links: {report['broken_count']}")
        for b in report["broken"][:30]:
            print(f"   • {b['page']}  ->  {b['link']}  ({b['reason']})")
        if len(report["broken"]) > 30:
            print(f"   … and {len(report['broken']) - 30} more (see report)")
    else:
        print("✅ No broken internal links.")
    if args.output:
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"📄 Report written: {args.output}")
    if args.strict and report["broken_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
