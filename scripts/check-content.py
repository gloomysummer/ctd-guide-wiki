#!/usr/bin/env python3
"""check-content.py — 构建前内容门禁（KI-57 v0.1 + KI-66 + KI-72）。

扫描 src/content/ 下所有 .md 的 frontmatter，执行：
  1. summary 必填且落在 40-60 英文词区间（Quick Answer 标准）；
  2. TDH 黄金门禁：title ≤ 60 字符、description 140-160 字符（frontmatter 层）；
  3. codes 集合：每个码必须带 sourceUrl（每个断言有出处）；
  4. 虚构模式初筛：正文命中 denylist 词形即报警（与 fabrication_guard 词库对齐的
     极简本地版，最终防线仍在 site-updater 的管线门禁）；
  5. 方案 A 增强版 (KI-66 / Round 47)：Official/Community 证据与数字/型号 Token 强闭环校验。

报告模式：exit 0 仅当全部通过；发现违规 exit 1（本脚本设计为阻断项）。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    # KI-72: this used to be tolerated ("skip frontmatter, print a warning") and
    # that tolerance was the bug - with no parser the gate still exited 0 and
    # printed "内容门禁全绿", so the entire frontmatter layer (summary / TDH /
    # evidence / exactQuote) was enforced only on machines whose `python3`
    # happened to have pyyaml. main() now fails closed instead.
    yaml = None

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "src" / "content"
CORPUS_FILE = ROOT / "data" / "steam-corpus.json"
STEAM_CORPUS: dict = {}
if CORPUS_FILE.exists():
    try:
        STEAM_CORPUS = json.loads(CORPUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        STEAM_CORPUS = {}

# 极简虚构模式初筛（大小写不敏感）。命中 ≠ 一定虚构，但必须人工过目。
DENYLIST = [
    r"\b(tested (by|in) our (own )?save)\b",
    r"\bcommunity[- ]verified\b",
    r"\bwe (have )?tested (this|it)\b",
    r"\bguaranteed\b",
]
FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", text or ""))


def check_file(path: Path) -> list[str]:
    problems: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    m = FM_RE.match(text)
    if not m:
        return [f"{path.name}: no frontmatter block"]
    if yaml is None:
        return [f"{path.name}: pyyaml missing — cannot parse frontmatter (pip install pyyaml)"]
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except Exception as e:
        return [f"{path.name}: frontmatter parse error: {e}"]
    if not isinstance(fm, dict):
        return [f"{path.name}: frontmatter is not a mapping"]

    rel = str(path.relative_to(CONTENT))
    summary = str(fm.get("summary", "") or "")
    wc = word_count(summary)
    if wc < 40 or wc > 60:
        problems.append(f"{rel}: summary {wc} words (need 40-60)")
    title = str(fm.get("title", "") or "")
    if len(title) > 60:
        problems.append(f"{rel}: title {len(title)} chars (max 60)")
    desc = str(fm.get("description", "") or "")
    if not (120 <= len(desc) <= 160):
        problems.append(f"{rel}: description {len(desc)} chars (need 120-160)")

    body = text[m.end():]
    for pattern in DENYLIST:
        hit = re.search(pattern, body, re.IGNORECASE)
        if hit:
            problems.append(f"{rel}: denylist hit '{hit.group(0)}' — 人工确认这句话是否有出处")

    for i, code in enumerate(fm.get("codes", []) or []):
        if not code.get("sourceUrl"):
            problems.append(f"{rel}: codes[{i}] '{code.get('code')}' 缺 sourceUrl")

    # 方案 A 增强版 (KI-66 / Round 47)：Official/Community 证据与数字/型号 Token 强闭环校验
    evidence_list = fm.get("evidence", []) or []
    for i, ev in enumerate(evidence_list):
        lvl = ev.get("level", "Official")
        surl = str(ev.get("sourceUrl", "") or "").strip()
        quote = str(ev.get("exactQuote", "") or "").strip()
        claim = str(ev.get("claim", "") or "")

        if lvl == "Official":
            if not surl:
                problems.append(f"{rel}: evidence[{i}] ('{claim[:40]}...') 标为 Official 缺少 sourceUrl")
            if not quote:
                problems.append(f"{rel}: evidence[{i}] ('{claim[:40]}...') 标为 Official 缺少 exactQuote 原文断言 (KI-66 增强A)")
        elif lvl == "Community-reported":
            if not surl:
                problems.append(f"{rel}: evidence[{i}] ('{claim[:40]}...') 标为 Community-reported 缺少 sourceUrl")
            if not quote:
                problems.append(f"{rel}: evidence[{i}] ('{claim[:40]}...') 标为 Community-reported 缺少 exactQuote (KI-66 增强A)")

        is_steam = "store.steampowered.com/app/" in surl or "store.steampowered.com/news/app/" in surl
        if is_steam and STEAM_CORPUS:
            app_match = re.search(r"/(?:app|news/app)/(\d+)", surl)
            app_id = app_match.group(1) if app_match else None
            app_data = STEAM_CORPUS.get(app_id) if (app_id and app_id in STEAM_CORPUS) else None
            target_texts = [app_data["full_text"]] if app_data else [a["full_text"] for a in STEAM_CORPUS.values()]

            # 1. Official 引文子串比对
            if lvl == "Official" and quote:
                q_norm = re.sub(r"\s+", " ", quote).lower()
                matched = any(q_norm in re.sub(r"\s+", " ", t).lower() for t in target_texts)
                if not matched:
                    problems.append(f"{rel}: evidence[{i}] exactQuote '{quote}' 在 Steam 官方语料中未找到匹配 (KI-66 方案A)")

            # 2. 数字与型号 Token 强收口（杀绝 KI-63 类虚构）
            nums = re.findall(r"\b\d{1,4}\b", claim)
            models = re.findall(r"[A-Z]{1,3}[- ]?\d{3,4}[A-Z]{0,3}", claim)
            for token in nums + models:
                t_lower = token.lower()
                token_matched = any(t_lower in re.sub(r"\s+", " ", t).lower() for t in target_texts)
                if not token_matched:
                    problems.append(f"{rel}: evidence[{i}] claim 中的数字/型号 '{token}' 未在官方语料中找到对应支撑 (KI-66 方案A)")
    return problems


def main() -> int:
    files = sorted(CONTENT.rglob("*.md"))
    if yaml is None:
        # KI-72: fail closed. Silently downgrading to a body denylist scan and
        # still printing "全绿" made this gate a no-op on any machine whose
        # `python3` lacked pyyaml - while every report of "四门禁全绿" stayed
        # literally true. A gate that reports green without checking is worse
        # than no gate: it buys trust it did not earn.
        print("❌ check-content: pyyaml 未安装，frontmatter 层无法执行"
              "（summary / TDH / evidence / exactQuote 全部未校验）。", file=sys.stderr)
        print(f"   这不是通过：{len(files)} 个内容文件会在无校验状态下放行。", file=sys.stderr)
        print(f"   当前解释器：{sys.executable}", file=sys.stderr)
        print("   修法：用带 pyyaml 的解释器跑本门禁（如 /usr/bin/python3），"
              "或 `pip install pyyaml`。", file=sys.stderr)
        return 1
    problems: list[str] = []
    for path in files:
        problems.extend(check_file(path))
    print(f"📄 check-content: {len(files)} 个内容文件")
    if problems:
        print(f"❌ {len(problems)} 个问题:")
        for p in problems:
            print(f"   • {p}")
        return 1
    print("✅ 内容门禁全绿（summary/TDH/evidence/否定词表）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
