#!/usr/bin/env python3
"""apply-template.py — 起站命令（KI-57 v0.2 清污加固版）。

从模板克隆后跑一次，把三处真相源（site.config.ts / astro.config.mjs /
robots.txt）与示例内容替换成你的站点。设计原则学自 AnvilWiki apply-template：
只动 Config 层与 Content 层示例，永不碰 Code 层。

特性升级（v0.2）：
- 增加 `--purge-content` 彻底净化：
  1. 清理全部旧图片资产（public/images/*）防跨站哈希污染
  2. 清理其他站点的 GSC 验证文件（google*.html / google*.txt）与旧 IndexNow 密钥
  3. 严格保护 `public/_redirects` 白名单（防权重分散与 301 误删）
  4. 重置 `src/content.config.ts` 为极简模式（阻断 Collection 幽灵警告）
  5. 自动清理模板遗留的未实装动态路由目录（如 src/pages/guide/）

用法（问答式，也可全参数）:
    python3 scripts/apply-template.py \
        --game "Anime Zero" --site-name "Anime Zero Wiki" \
        --domain "animezero.top" --suffix "| AnimeZero" \
        [--purge-content] [--yes]
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def ask(prompt: str, default: str = "") -> str:
    val = input(f"{prompt} [{default}]: ").strip()
    return val or default


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply the template to a new game site (Config layer only)")
    ap.add_argument("--game", help="游戏官方名")
    ap.add_argument("--site-name", help="站点品牌名，如 'Duckov Wiki'")
    ap.add_argument("--domain", help="站点域名，如 duckov.wiki")
    ap.add_argument("--suffix", help="SERP 品牌后缀，如 ' | DuckWiki'（≤12 字符）")
    ap.add_argument("--email", default="")
    ap.add_argument("--adsense", default="")
    ap.add_argument("--ga", default="")
    ap.add_argument("--purge-content", action="store_true", help="彻底清空模板示例内容、残留资产与历史验证文件")
    ap.add_argument("--yes", action="store_true", help="跳过确认提示，全自动执行")
    args = ap.parse_args()

    game = args.game or ask("游戏官方名")
    site_name = args.site_name or ask("站点品牌名", f"{game} Wiki")
    domain = args.domain or ask("域名", f"{game.lower().replace(' ', '')}.com")
    suffix = args.suffix or ask("品牌后缀", f" | {site_name.split()[0][:8]}")
    email = args.email or ask("联系邮箱", f"admin@{domain}")

    if len(suffix) > 12:
        print(f"❌ 品牌后缀 '{suffix}' 超过 12 字符（SERP 红线）")
        return 1

    site_url = f"https://{domain}"

    def sub_file(path: Path, pairs: list[tuple[str, str]]) -> None:
        if not path.exists():
            return
        text = path.read_text(encoding="utf-8")
        for old, new in pairs:
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")
        print(f"  ✓ {path.relative_to(ROOT)}")

    print(f"→ 应用配置: {site_name} @ {site_url}")
    index_now_key = uuid.uuid4().hex
    sub_file(ROOT / "src" / "config" / "site.config.ts", [
        ('gameName: "Demo Game"', f'gameName: "{game}"'),
        ('siteName: "DemoGame Wiki"', f'siteName: "{site_name}"'),
        ('siteUrl: "https://demo-game.example.com"', f'siteUrl: "{site_url}"'),
        ('titleSuffix: "| DemoWiki"', f'titleSuffix: "{suffix}"'),
        ('contactEmail: "admin@example.com"', f'contactEmail: "{email}"'),
        ('adsenseClient: ""', f'adsenseClient: "{args.adsense}"'),
        ('gaMeasurementId: ""', f'gaMeasurementId: "{args.ga}"'),
        ('indexNowKey: ""', f'indexNowKey: "{index_now_key}"'),
    ])
    
    # 写入新站专属 IndexNow Key
    (ROOT / "public" / f"{index_now_key}.txt").write_text(f"{index_now_key}\n", encoding="utf-8")
    print(f"  ✓ public/{index_now_key}.txt (Microsoft Bing IndexNow Key)")

    sub_file(ROOT / "astro.config.mjs", [
        ("https://demo-game.example.com", site_url),
    ])
    sub_file(ROOT / "public" / "robots.txt", [
        ("https://demo-game.example.com", site_url),
    ])
    sub_file(ROOT / "public" / "llms.txt", [
        ("DemoGame Wiki", site_name),
        ("Demo Game", game),
        ("https://demo-game.example.com", site_url),
    ])

    should_purge = args.purge_content or args.yes
    if not should_purge:
        should_purge = ask("是否彻底清空模板示例内容、残留资产与历史验证文件？(y/N)").lower() == "y"

    if should_purge:
        print("\n🧹 执行模板清污与去毒工程 (--purge-content):")
        # 1. 清理 src/content 示例 markdown
        content_dir = ROOT / "src" / "content"
        if content_dir.exists():
            for md in content_dir.rglob("*.md"):
                md.unlink()
                print(f"  ✓ 删除示例 Markdown: {md.name}")

        # 2. 清理 public/images 残留图片（防跨站 SHA-256 碰撞）
        img_dir = ROOT / "public" / "images"
        if img_dir.exists():
            for f in img_dir.rglob("*"):
                if f.is_file():
                    f.unlink()
                    print(f"  ✓ 清理历史图片资产: {f.name}")

        # 3. 清理他人 GSC 验证文件与历史 IndexNow 密钥（严格保留白名单）
        WHITELIST_FILES = {"robots.txt", "_redirects", f"{index_now_key}.txt", "favicon.svg", "favicon.ico"}
        for f in (ROOT / "public").iterdir():
            if f.is_file() and f.name not in WHITELIST_FILES:
                if f.name.startswith("google") or re.match(r"^[a-f0-9]{32}\.txt$", f.name):
                    f.unlink()
                    print(f"  ✓ 清除他人/历史验证令牌: public/{f.name}")

        # 4. 净化 src/content.config.ts（防 Collection 幽灵警告）
        content_config = ROOT / "src" / "content.config.ts"
        if content_config.exists():
            content_config.write_text("export const collections = {};\n", encoding="utf-8")
            print("  ✓ 净化 src/content.config.ts 为极简集合（消除 Collection 幽灵警告）")

        # 5. 清理残留模板动态路由
        guide_pages_dir = ROOT / "src" / "pages" / "guide"
        if guide_pages_dir.exists():
            shutil.rmtree(guide_pages_dir)
            print("  ✓ 移除未挂载模板路由: src/pages/guide/")
        codes_slug = ROOT / "src" / "pages" / "codes" / "[slug].astro"
        if codes_slug.exists():
            codes_slug.unlink()
            print("  ✓ 移除残留动态路由: src/pages/codes/[slug].astro")
    else:
        # 文案里的游戏名占位替换
        for md in list((ROOT / "src" / "content").rglob("*.md")):
            text = md.read_text(encoding="utf-8")
            md.write_text(text.replace("Demo Game", game), encoding="utf-8")

    print("\n✅ 模板起站与净化完成。下一步：")
    print("   1. npm install && npm run build")
    print("   2. npm run check:assets && npm run check:config && npm run check:content && npm run check:links")
    print("   3. npm run setup:hooks   # 门禁挂上 pre-push，物理上锁")
    print("   4. 推到 GitHub，Cloudflare Pages 连仓库（build: npm run build，输出: dist，NODE_VERSION=22）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
