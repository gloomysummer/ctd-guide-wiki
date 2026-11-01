#!/usr/bin/env python3
"""asset-isolation-audit.py — 跨站资产隔离与哈希防污染门禁质检脚本。

逐文件计算当前站点 public/ 目录下所有文件的 SHA-256，
并与本地存量矩阵维基站点对比。

硬性门禁：0 碰撞命中方可通过（Exit Code 0），任何碰撞直接阻断（Exit Code 1）。
"""
from __future__ import annotations

import glob
import hashlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_PUBLIC = ROOT / "public"
PROJECTS_DIR = ROOT.parent


def sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def main() -> int:
    print(f"🔍 启动跨站点资产隔离与 SHA-256 哈希审计: {BASE_PUBLIC}")
    if ROOT.name == "game-wiki-template":
        print("ℹ️ 当前处于母版模板仓库 (game-wiki-template)，跳过自身模板碰撞质检。")
        return 0
    if not BASE_PUBLIC.exists():
        print(f"⚠️ public 目录不存在，跳过资产审计。")
        return 0

    other_public_dirs = [
        Path(p) for p in glob.glob(str(PROJECTS_DIR / "*/public"))
        if str(ROOT) not in p
    ]

    print(f"📦 正在扫描存量比对基线: {len(other_public_dirs)} 个维基工程")
    for d in other_public_dirs:
        print(f"   • {d.parent.name}")

    # 建立存量站点哈希索引（排除纯文本通用配置文件如 robots.txt / _redirects）
    EXCLUDE_FILENAMES = {"robots.txt", "_redirects", ".DS_Store"}
    hash_index: dict[str, list[str]] = {}
    for op in other_public_dirs:
        site_name = op.parent.name
        for root, _, files in os.walk(op):
            for fn in files:
                if fn in EXCLUDE_FILENAMES:
                    continue
                fp = Path(root) / fn
                h = sha256_file(fp)
                if h:
                    hash_index.setdefault(h, []).append(f"{site_name}:{fp.relative_to(op)}")

    # 检查当前站点的 public 资产
    collisions = []
    total_files = 0

    for root, _, files in os.walk(BASE_PUBLIC):
        for fn in files:
            if fn in EXCLUDE_FILENAMES:
                continue
            fp = Path(root) / fn
            total_files += 1
            h = sha256_file(fp)
            if h and h in hash_index:
                rel = fp.relative_to(BASE_PUBLIC)
                collisions.append((rel, hash_index[h][:3]))

    print(f"\n📊 审计结果: 共检查 {total_files} 个 public 文件")
    if collisions:
        print(f"❌ 严重违规: 发现 {len(collisions)} 处跨站点资产哈希碰撞！")
        for rel, matched in collisions:
            print(f"   ⚠️ {rel} ← 与存量站完全同哈希: {matched}")
        print("\n🚫 门禁阻断: 严禁复用其他游戏的图片或模板残留资产！")
        return 1

    print(f"✅ 跨站点哈希审计全绿：0 命中碰撞，所有资产均为 {ROOT.name} 专属物理文件！")
    return 0


if __name__ == "__main__":
    sys.exit(main())
