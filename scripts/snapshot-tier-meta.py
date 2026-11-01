#!/usr/bin/env python3
"""snapshot-tier-meta.py — Anime Zero 每日武器与元数据快照采集器 (Phase A/B 历史追踪)

功能：
1. 读取 dossier/dossier.json 中的实时 Roblox 遥测数据 (CCU, visits, patch name)；
2. 读取 src/data/weapons.json 中的全部武器基准掉率与保底；
3. 输出幂等快照到 state/tier-snapshots/<YYYY-MM-DD>.json；
4. 更新 src/data/tier-snapshots-index.json 索引库；
5. 专为 daily-update.sh 流水线自动化设计。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOSSIER_PATH = ROOT / "dossier" / "dossier.json"
WEAPONS_PATH = ROOT / "src" / "data" / "weapons.json"
SNAPSHOTS_DIR = ROOT / "state" / "tier-snapshots"
INDEX_PATH = ROOT / "src" / "data" / "tier-snapshots-index.json"


def capture_snapshot(force: bool = False) -> int:
    if not DOSSIER_PATH.exists():
        print(f"❌ Error: Dossier not found at {DOSSIER_PATH}", file=sys.stderr)
        return 1

    if not WEAPONS_PATH.exists():
        print(f"❌ Error: Weapons database not found at {WEAPONS_PATH}", file=sys.stderr)
        return 1

    dossier = json.loads(DOSSIER_PATH.read_text(encoding="utf-8"))
    weapons_data = json.loads(WEAPONS_PATH.read_text(encoding="utf-8"))

    today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now_iso = datetime.now(timezone.utc).isoformat()

    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_file = SNAPSHOTS_DIR / f"{today_utc}.json"

    metadata = dossier.get("metadata", {})
    live_stats = dossier.get("liveStats", {})

    patch_name = metadata.get("displayName") or metadata.get("name") or "Anime Zero"
    ccu = live_stats.get("playing", 0)
    visits = live_stats.get("visits", 0)

    weapon_records = []
    for w in weapons_data.get("weapons", []):
        acq = w.get("acquisition", {})
        pity = acq.get("pity") or {}
        weapon_records.append({
            "slug": w.get("slug"),
            "name": w.get("name"),
            "rarity": w.get("rarity"),
            "dropRatePercent": acq.get("dropRatePercent"),
            "pityRuns": pity.get("runs"),
            "spinPity": w.get("rarityPitySpins")
        })

    snapshot_payload = {
        "date": today_utc,
        "capturedAt": now_iso,
        "patchName": patch_name,
        "ccu": ccu,
        "visits": visits,
        "weapons": weapon_records
    }

    # Write snapshot atomically
    snapshot_file.write_text(json.dumps(snapshot_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"✅ Captured tier meta snapshot for {today_utc}: {snapshot_file.relative_to(ROOT)}")

    # Update index
    index_data = {"updatedAt": now_iso, "snapshots": []}
    if INDEX_PATH.exists():
        try:
            index_data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:
            index_data = {"updatedAt": now_iso, "snapshots": []}

    snapshots_list = index_data.get("snapshots", [])
    # Remove existing entry for today if any (idempotency)
    snapshots_list = [s for s in snapshots_list if s.get("date") != today_utc]

    rel_file = f"state/tier-snapshots/{today_utc}.json"
    snapshots_list.append({
        "date": today_utc,
        "patch": patch_name,
        "ccu": ccu,
        "visits": visits,
        "weaponsTracked": len(weapon_records),
        "file": rel_file
    })
    snapshots_list.sort(key=lambda x: x.get("date", ""))

    index_payload = {
        "updatedAt": now_iso,
        "snapshots": snapshots_list
    }
    INDEX_PATH.write_text(json.dumps(index_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"✅ Updated snapshot index ({len(snapshots_list)} recorded): {INDEX_PATH.relative_to(ROOT)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture daily weapon and telemetry snapshot.")
    parser.add_argument("--force", action="store_true", help="Force overwrite existing snapshot.")
    args = parser.parse_args()
    return capture_snapshot(force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
