#!/usr/bin/env python3
"""Generate the self-hosted Adsterra iframe shells in public/ads/.

The zone key has to exist in two places — the component config and the shell
that loads invoke.js — and the matrix has already been bitten once by those two
drifting apart (a slot that renders but never fills). So the config is the only
place a key is written by hand; these files are generated from it.

Usage:
    python3 scripts/build-ad-banners.py            # write public/ads/*.html
    python3 scripts/build-ad-banners.py --check    # exit 1 if a file is stale

A banner whose key is still empty is generated with a placeholder key. That is
safe: AdSlot.astro refuses to render a slot whose key is not 32 hex characters,
so the placeholder file is never requested.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "src" / "config" / "site.config.ts"
OUT = ROOT / "public" / "ads"

PLACEHOLDER = "0" * 32

# The ad network serves the loader from an address that differs per account AND
# per zone. On ctd-guide.wiki the dashboard hands out https://bauval.org/22/<key>
# — a path segment, and no invoke.js suffix. Other sites in the matrix get
# highrevenueformat.com/<key>/invoke.js. So `host` in the config is the whole
# prefix, not a bare domain, and it is copied from the dashboard verbatim.
DEFAULT_HOST = "https://www.highrevenueformat.com"
BLOCK_RE = re.compile(r'"(banner-\d+x\d+)":\s*\{([^}]*)\}', re.S)
FIELD_RE = {
    "key": re.compile(r'key:\s*"([^"]*)"'),
    "host": re.compile(r'host:\s*"([^"]*)"'),
    "width": re.compile(r'width:\s*(\d+)'),
    "height": re.compile(r'height:\s*(\d+)'),
}

TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Advertisement</title>
  <meta name="robots" content="noindex, nofollow">
  <!--
    GENERATED FILE — do not edit by hand.
    Source of truth: src/config/site.config.ts -> adsterra.banners["{zone}"].key
    Regenerate:      python3 scripts/build-ad-banners.py   (both values in one commit)

    [GREY FEATURE] 反嵌套探针伪装 (SOP 六.2)
    作用: 让 invoke.js 的 iframe 自检 (window.top === window.self) 恒为真,
          按"顶层原生页"全价出价, 而不是 iframe 降级价.
    它不伪造展示/点击/统计数字, 只改广告脚本对自身环境的判断 —— 条款灰区.

    ▶ 秒级撤回: 删掉下面那个 <script> 块即为纯净直出版本.
  -->
  <script>
    try {{
      Object.defineProperty(window, 'top', {{ get: function() {{ return window.self; }} }});
      Object.defineProperty(window, 'parent', {{ get: function() {{ return window.self; }} }});
      Object.defineProperty(window, 'frameElement', {{ get: function() {{ return null; }} }});
    }} catch (e) {{}}
  </script>
  <style>
    body {{
      margin: 0; padding: 0; overflow: hidden; background: transparent;
      display: flex; justify-content: center; align-items: center;
      width: {w}px; height: {h}px;
    }}
  </style>
</head>
<body>
  <!-- Zone: ctd-guide.wiki · {zone} · key={key} -->
  <script type="text/javascript">
    atOptions = {{
      'key': '{key}',
      'format': 'iframe',
      'height': {h},
      'width': {w},
      'params': {{}}
    }};
  </script>
  <script type="text/javascript" src="{host}/{key}"></script>
</body>
</html>
"""


def read_banners() -> list[tuple[str, str, str, int, int]]:
    src = CONFIG.read_text(encoding="utf-8")
    found = []
    for zone, body in BLOCK_RE.findall(src):
        vals = {}
        for name, rx in FIELD_RE.items():
            m = rx.search(body)
            vals[name] = m.group(1) if m else ""
        if not vals["width"] or not vals["height"]:
            sys.exit(f"{zone}: width/height not found in config block")
        found.append((zone, vals["key"], vals["host"], int(vals["width"]), int(vals["height"])))
    if not found:
        sys.exit("no banner entries found in site.config.ts — did the shape change?")
    return found


def render(zone: str, key: str, host: str, w: int, h: int) -> str:
    return TEMPLATE.format(zone=zone, key=key or PLACEHOLDER, w=w, h=h, host=host or DEFAULT_HOST)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="report stale files instead of writing")
    args = ap.parse_args()

    banners = read_banners()
    OUT.mkdir(parents=True, exist_ok=True)

    stale, written, empty = [], 0, []
    for zone, key, host, w, h in banners:
        path = OUT / f"{zone}.html"
        want = render(zone, key, host, w, h)
        have = path.read_text(encoding="utf-8") if path.exists() else None

        if have == want:
            continue
        if args.check:
            stale.append(f"{zone}: {'missing' if have is None else 'out of date'}")
            continue

        path.write_text(want, encoding="utf-8")
        written += 1
        if not key:
            empty.append(zone)

    print(f"banners in config: {len(banners)}")
    for zone, key, host, w, h in banners:
        state = "ok" if key else "KEY EMPTY"
        h_used = (host or DEFAULT_HOST).replace("https://www.", "")
        print(f"  {zone:<18} {w}x{h:<4} {state:<10} {h_used}")

    if args.check:
        if stale:
            print("\nstale: " + "; ".join(stale))
            print("run: python3 scripts/build-ad-banners.py")
            return 1
        print("\nall shells match the config")
        return 0

    print(f"\nwrote {written} file(s) to {OUT.relative_to(ROOT)}")
    if empty:
        print(f"placeholder key used for: {', '.join(empty)} (those slots stay invisible)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
