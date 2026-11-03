#!/usr/bin/env python3
"""
GSC 手动 Request Indexing 批量提交（走 UI，非 API）

依赖：老大已登录 GSC 的 Chrome 开着 CDP
  /Applications/Google Chrome.app/Contents/MacOS/Google Chrome \
    --remote-debugging-port=18800

用法：
  /usr/bin/python3 scripts/gsc_request_indexing.py            # 用内置清单
  /usr/bin/python3 scripts/gsc_request_indexing.py --dry-run  # 只查状态不提交

行为：
  - 逐个 URL 走 GSC 搜索框 → Inspect → Request Indexing
  - 遇 Quota Exceeded 立即停止（GSC 按太平洋时间日切，约 10-12 个/天）
  - 结果写 state/gsc-index-requests-<date>.json
"""
import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    sys.exit("需要 playwright：/usr/bin/python3 -m pip install playwright")

CDP = "http://127.0.0.1:18800"
SITE_PARAM = "sc-domain%3Actd-guide.wiki"
HOME = f"https://search.google.com/search-console?resource_id={SITE_PARAM}"
INPUT = 'input[aria-label="Inspect any URL in ctd-guide.wiki"]'

URLS = [
    "https://ctd-guide.wiki/values/",
    "https://ctd-guide.wiki/codes/",
    "https://ctd-guide.wiki/tier-list/",
    "https://ctd-guide.wiki/units/",
    "https://ctd-guide.wiki/how-to-solo-nightmare-mode/",
    "https://ctd-guide.wiki/units/tv-spider/",
    "https://ctd-guide.wiki/units/chaos-cameraman/",
    "https://ctd-guide.wiki/units/upgraded-titan-cameraman/",
    "https://ctd-guide.wiki/units/engineer-cameraman/",
    "https://ctd-guide.wiki/units/executioner-tv-man/",
]

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state"


async def inspect_and_request(page, url):
    """返回 dict：coverage / result"""
    await page.goto(HOME, wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(5)

    inp = page.locator(INPUT).first
    await inp.click()
    await inp.fill(url)
    await inp.press("Enter")

    for _ in range(15):
        await asyncio.sleep(2)
        if "/inspect" in page.url:
            break
    await asyncio.sleep(4)

    body = await page.inner_text("body")
    coverage = ""
    for line in body.split("\n"):
        s = line.strip()
        if "Discovered" in s or "Page is indexed" in s or "Page is not indexed" in s or "unknown to Google" in s:
            coverage = s[:90]
            break

    btn = page.locator('div[role="button"]:has-text("REQUEST INDEXING")').first
    if await btn.count() == 0:
        return {"coverage": coverage, "result": "no_button"}

    await btn.click()

    # live test 要 1-2 分钟，轮询最多 150 秒
    for _ in range(30):
        await asyncio.sleep(5)
        dlg = page.locator('[role="alertdialog"]')
        if await dlg.count():
            t = (await dlg.first.inner_text()).strip()
            if "Indexing requested" in t:
                return {"coverage": coverage, "result": "requested"}
            if "quota" in t.lower():
                return {"coverage": coverage, "result": "quota_exceeded"}
    return {"coverage": coverage, "result": "timeout"}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只查状态，不点 Request Indexing")
    ap.add_argument("--urls", nargs="*", default=None)
    args = ap.parse_args()
    urls = args.urls or URLS

    results = []
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(CDP)
        except Exception as e:
            sys.exit(f"连不上 Chrome CDP {CDP}：{e}\n请先启动带 --remote-debugging-port=18800 的 Chrome")
        ctx = browser.contexts[0]
        page = await ctx.new_page()
        try:
            for i, url in enumerate(urls, 1):
                try:
                    if args.dry_run:
                        await page.goto(HOME, wait_until="domcontentloaded", timeout=60000)
                        await asyncio.sleep(4)
                        inp = page.locator(INPUT).first
                        await inp.click(); await inp.fill(url); await inp.press("Enter")
                        for _ in range(15):
                            await asyncio.sleep(2)
                            if "/inspect" in page.url:
                                break
                        await asyncio.sleep(4)
                        body = await page.inner_text("body")
                        cov = ""
                        for line in body.split("\n"):
                            if "Discovered" in line or "Page is indexed" in line or "unknown to Google" in line:
                                cov = line.strip()[:90]; break
                        r = {"coverage": cov, "result": "dry_run"}
                    else:
                        r = await inspect_and_request(page, url)
                    r = {"url": url, **r}
                except Exception as e:
                    r = {"url": url, "coverage": "", "result": f"error:{str(e)[:80]}"}
                results.append(r)
                print(f"[{i}/{len(urls)}] {url}\n    {r['coverage']} | {r['result']}", flush=True)
                if r["result"] == "quota_exceeded":
                    print(">>> 配额耗尽，停止后续提交", flush=True)
                    break
                await asyncio.sleep(2)
        finally:
            await page.close()

    cst = timezone(timedelta(hours=8))
    stamp = datetime.now(cst).strftime("%Y-%m-%d")
    STATE.mkdir(exist_ok=True)
    out = STATE / f"gsc-index-requests-{stamp}.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")

    ok = sum(1 for r in results if r["result"] == "requested")
    print(f"\n成功提交 {ok}/{len(results)}，明细：{out}")


if __name__ == "__main__":
    asyncio.run(main())
