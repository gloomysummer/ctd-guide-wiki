#!/usr/bin/env python3
"""check-config.py — 配置一致性门禁（KI-57 v0.1）。

检查三处真相源是否一致（AnvilWiki check-config 同思路）：
  1. src/config/site.config.ts 的 siteUrl
  2. astro.config.mjs 的 site
  3. public/robots.txt 的 Sitemap 域名
不一致即 exit 1。域名替换一律走 apply-template.py，禁止手改单处。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    site_ts = (ROOT / "src" / "config" / "site.config.ts").read_text(encoding="utf-8")
    astro_mjs = (ROOT / "astro.config.mjs").read_text(encoding="utf-8")
    robots = (ROOT / "public" / "robots.txt").read_text(encoding="utf-8")

    m1 = re.search(r'siteUrl:\s*"([^"]+)"', site_ts)
    m2 = re.search(r"site:\s*['\"]([^'\"]+)['\"]", astro_mjs)
    m3 = re.search(r"Sitemap:\s*(https?://[^/]+)", robots)
    problems = []
    if not m1:
        problems.append("site.config.ts: 找不到 siteUrl")
    if not m2:
        problems.append("astro.config.mjs: 找不到 site")
    if not m3:
        problems.append("robots.txt: 找不到 Sitemap 域名")
    if problems:
        print("❌ check-config:"); [print("   •", p) for p in problems]; return 1

    urls = {"site.config.ts": m1.group(1), "astro.config.mjs": m2.group(1), "robots.txt": m3.group(1)}
    values = set(urls.values())
    print(f"📄 check-config: {urls}")
    if len(values) != 1:
        print("❌ 三处域名不一致——只允许通过 apply-template.py 改域名")
        return 1

    # 品牌后缀长度红线（SERP 600px）
    m = re.search(r'titleSuffix:\s*"([^"]*)"', site_ts)
    if m and len(m.group(1)) > 12:
        print(f"❌ titleSuffix '{m.group(1)}' 超过 12 字符")
        return 1

    # Dossier 最小必需键集契约校验（SKILL.md 3.1 节）
    dossier_path = ROOT / "src" / "data" / "dossier.json"
    if dossier_path.exists():
        import json
        try:
            dossier_data = json.loads(dossier_path.read_text(encoding="utf-8"))
            REQUIRED_DOSSIER_KEYS = {
                "gameName", "platform", "universeId", "placeId",
                "fetchedAt", "metadata", "liveStats", "systems", "media"
            }
            missing_keys = REQUIRED_DOSSIER_KEYS - set(dossier_data.keys())
            if missing_keys:
                print(f"❌ dossier.json 缺失最小必需键 (SKILL.md 3.1 违规): {sorted(missing_keys)}")
                return 1
            print("✅ Dossier 最小必需键集完整 (9/9)")
        except Exception as e:
            print(f"❌ dossier.json 解析失败: {e}")
            return 1

    print("✅ 配置三处一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
