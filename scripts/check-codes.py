#!/usr/bin/env python3
"""check-codes.py — 兑换码门禁：校验 verified-codes.json 规范性与反编造检查。

门禁断言：
1. 若存在 src/data/verified-codes.json，其必须为标准合法 JSON。
2. 每一个条目必须具备非空的 code、rewards、status、lastVerified 与 sourceUrl。
3. 状态枚举仅限 active | expired | unverified。
4. 严禁出现大小写重复 Code。
5. 若构建产物 dist/ 存在，扫描 HTML 页面中出现的 Code 必须是 verified-codes.json 的子集（防 AI 凭空捏造未登记的码）。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CODES_JSON = REPO_ROOT / "src" / "data" / "verified-codes.json"
DIST_DIR = REPO_ROOT / "dist"

EXCLUDE_WORDS = {
    "CODE", "CODES", "REWARD", "REWARDS", "STATUS", "DEVELOPER",
    "PRIORITY", "ROLLS", "COINS", "GEMS", "HOW", "EXPIRED", "ACTIVE",
    "DETAILS", "NONE", "UPDATE", "PATCH", "ROBLOX", "ANIME", "ZERO",
    "SPINS", "TIER", "LIST", "RAID", "RAIDS", "LEVEL", "REQUIREMENT"
}


def main() -> int:
    if not CODES_JSON.exists():
        # 如果不是 Roblox 站点或无兑换码需求，优雅跳过
        print("ℹ️ check-codes: 未发现 src/data/verified-codes.json，跳过兑换码门禁。")
        return 0

    print(f"🔍 check-codes: 正在校验兑换码数据源 {CODES_JSON} ...")
    try:
        with open(CODES_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ check-codes: JSON 解析失败: {e}", file=sys.stderr)
        return 1

    codes_list = data.get("codes", [])
    if not isinstance(codes_list, list):
        print("❌ check-codes: codes 字段必须为数组", file=sys.stderr)
        return 1

    seen_codes = set()
    active_count = 0
    expired_count = 0

    for idx, entry in enumerate(codes_list, 1):
        code = entry.get("code", "").strip()
        rewards = entry.get("rewards", "").strip()
        status = entry.get("status", "").strip().lower()
        last_verified = entry.get("lastVerified", "").strip()
        source_url = entry.get("sourceUrl", "").strip()

        if not code:
            print(f"❌ check-codes: 第 {idx} 项兑换码的 'code' 字段为空", file=sys.stderr)
            return 1

        code_upper = code.upper()
        if code_upper in seen_codes:
            print(f"❌ check-codes: 发现重复兑换码 '{code}'", file=sys.stderr)
            return 1
        seen_codes.add(code_upper)

        if not rewards:
            print(f"❌ check-codes: 兑换码 '{code}' 缺少 rewards 奖励描述", file=sys.stderr)
            return 1

        if status not in ("active", "expired", "unverified"):
            print(f"❌ check-codes: 兑换码 '{code}' 的 status '{status}' 非法（必须为 active/expired/unverified）", file=sys.stderr)
            return 1

        if not last_verified:
            print(f"❌ check-codes: 兑换码 '{code}' 缺少 lastVerified 核验日期", file=sys.stderr)
            return 1

        if not source_url:
            print(f"❌ check-codes: 兑换码 '{code}' 缺少 sourceUrl 事实来源链接（严禁无源收录）", file=sys.stderr)
            return 1

        if status == "active":
            active_count += 1
        elif status == "expired":
            expired_count += 1

    print(f"  ✓ 基础 Schema 校验通过: 共 {len(codes_list)} 个码 ({active_count} active, {expired_count} expired)")

    # 检查 dist/ 中 codes 页面上的码是否均在登记表中
    codes_page_dist = DIST_DIR / "codes" / "index.html"
    if codes_page_dist.exists():
        html_content = codes_page_dist.read_text(encoding="utf-8")
        # 匹配诸如 data-code="..." 或 copyable text
        candidate_matches = re.findall(r'data-code=["\']([A-Za-z0-9_!]{3,35})["\']', html_content)
        for m in candidate_matches:
            if m.upper() not in seen_codes and m.upper() not in EXCLUDE_WORDS:
                print(f"❌ check-codes 拦截: 页面渲染了未在 verified-codes.json 登记的兑换码 '{m}'！疑似 AI 幻觉！", file=sys.stderr)
                return 1
        print(f"  ✓ 页面防编造核查通过: 页面渲染全部码均在数据源白名单内")

    print("✅ 兑换码真实性与数据规范门禁全绿")
    return 0


if __name__ == "__main__":
    sys.exit(main())
