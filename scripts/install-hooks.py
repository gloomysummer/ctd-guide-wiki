#!/usr/bin/env python3
"""install-hooks.py — 把门禁挂上 git pre-push（KI-57 v0.1 + KI-64 + KI-72）。

AnvilWiki 的教训：门禁如果不挂进 git，全靠自觉。本脚本生成 .git/hooks/pre-push。
KI-64 & KI-72 强化：
  1. 共享事实门禁（若存在 FACT_GATE 且配置了 SITE_KEY，先跑事实门禁）；
  2. 解释器探测与自选（按 /usr/bin/python3 -> /usr/local/bin/python3 -> python3 探测 pyyaml），
     直接调用脚本，消除 npm/PATH 漂移导致的静默降级；
  3. 四道模板门禁（check:config -> check:content -> build -> check:links --strict）。
"""
from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".git" / "hooks" / "pre-push"

SITE_KEY = os.environ.get("SITE_KEY", "")
FACT_GATE = os.environ.get("FACT_GATE", "/Users/kira/Projects/site-updater/guard_push.py")

# 2026-10-15: SITE_KEY 为空时自动从 site-updater/config.json 按 repo_path 反查。
# 此前默认空字符串 → 生成的钩子里 SITE_KEY 永远为空 → fact gate 从不执行，
# 新站推送完全没有 fabrication 保护（themakerway 实测踩坑）。
if not SITE_KEY:
    try:
        import json as _json
        _cfg_path = Path("/Users/kira/Projects/site-updater/config.json")
        if _cfg_path.exists():
            _cfg = _json.loads(_cfg_path.read_text(encoding="utf-8"))
            _here = str(ROOT.resolve())
            for _k, _v in _cfg.items():
                if isinstance(_v, dict) and _v.get("repo_path") and \
                   str(Path(_v["repo_path"]).resolve()) == _here:
                    SITE_KEY = _k
                    break
    except Exception:
        pass  # site key lookup is best-effort; the hook still works without it

TEMPLATE = """#!/bin/sh
# KI-57 gate hook — installed by scripts/install-hooks.py (KI-64 / KI-72)
set -u
echo "[gates] pre-push: running verification gates..."
cd "$(git rev-parse --show-toplevel)" || exit 1

# 1) Shared fact gate (optional/conditional on site-updater presence)
FACT_GATE="${FACT_GATE:-__FACT_GATE__}"
SITE_KEY="${SITE_KEY:-__SITE_KEY__}"
if [ -n "$SITE_KEY" ] && [ -f "$FACT_GATE" ]; then
  echo "[gates] running shared fact gate for site '$SITE_KEY'..."
  /usr/bin/python3 "$FACT_GATE" --site "$SITE_KEY" --repo "$(pwd)" || exit 1
fi

# 2) Interpreter selection (KI-72: fail closed if no pyyaml, pin interpreter)
PYTHON=""
for cand in /usr/bin/python3 /usr/local/bin/python3 python3; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c "import yaml" >/dev/null 2>&1; then
    PYTHON="$(command -v "$cand")"
    break
  fi
done
if [ -z "$PYTHON" ]; then
  echo "[gates] ABORT: no python3 with pyyaml found; check-content cannot verify frontmatter." >&2
  echo "        Fix: pip install pyyaml, then retry." >&2
  exit 1
fi
echo "[gates] interpreter for python gates: $PYTHON"

# 3) Template gates
if [ -f scripts/asset-isolation-audit.py ]; then
  "$PYTHON" scripts/asset-isolation-audit.py || exit 1
fi
"$PYTHON" scripts/check-config.py || exit 1
"$PYTHON" scripts/check-content.py || exit 1
if [ -f scripts/check-codes.py ]; then
  "$PYTHON" scripts/check-codes.py || exit 1
fi
npm run --silent build || exit 1
"$PYTHON" scripts/check-links.py --strict || exit 1
echo "[gates] all green."
""".replace("__FACT_GATE__", FACT_GATE).replace("__SITE_KEY__", SITE_KEY)


def main() -> int:
    if not (ROOT / ".git").is_dir():
        print("❌ 不是 git 仓库（先 git init）")
        return 1
    HOOK.write_text(TEMPLATE, encoding="utf-8")
    HOOK.chmod(HOOK.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"✅ pre-push 门禁已安装: {HOOK}")
    print("   推送将依次执行：事实门禁(若配置) → check:config → check:content → build → check:links(--strict)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
