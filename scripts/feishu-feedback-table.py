#!/usr/bin/env python3
"""Create (or find) the user-feedback table in the shared Feishu Bitable.

Run once per Bitable document. Idempotent: if a table with the target name
already exists, it prints its id and changes nothing.

Usage:
    python3 scripts/feishu-feedback-table.py --env-file <profile .env>
    python3 scripts/feishu-feedback-table.py --env-file ... --dry-run

Credentials are read from the named .env (FEISHU_APP_ID / FEISHU_APP_SECRET /
FEISHU_BITABLE_APP_TOKEN). Nothing is written into the repository.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://open.feishu.cn/open-apis"
TABLE_NAME = "ctd-guide 用户吐槽"

# type: 1 text, 2 number, 3 single select, 5 datetime
FIELDS = [
    {"field_name": "提交时间", "type": 5, "property": {"date_formatter": "yyyy/MM/dd HH:mm"}},
    {"field_name": "站点", "type": 3, "property": {"options": [{"name": "ctd-guide.wiki"}]}},
    {"field_name": "页面", "type": 1},
    {"field_name": "满意度", "type": 3, "property": {"options": [
        {"name": "很好 · 直接能用"}, {"name": "还行 · 有点绕"}, {"name": "难用 · 用不下去"}]}},
    {"field_name": "吐槽", "type": 1},
    {"field_name": "想做什么", "type": 1},
    {"field_name": "当前这手牌", "type": 1},
    {"field_name": "设备", "type": 3, "property": {"options": [{"name": "手机"}, {"name": "桌面"}]}},
    {"field_name": "视口", "type": 1},
    {"field_name": "来源页面", "type": 1},
    {"field_name": "版本", "type": 1},
    {"field_name": "处理状态", "type": 3, "property": {"options": [
        {"name": "待看"}, {"name": "已修"}, {"name": "不修"}]}},
    {"field_name": "备注", "type": 1},
]


def load_env(path: Path) -> dict[str, str]:
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def call(token: str, method: str, path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        API + path, data=data, method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        return json.loads(urllib.request.urlopen(req, timeout=20).read())
    except urllib.error.HTTPError as exc:
        return json.loads(exc.read())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--env-file", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true", help="show the schema, create nothing")
    args = ap.parse_args()

    env = load_env(args.env_file)
    for key in ("FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_BITABLE_APP_TOKEN"):
        if not env.get(key):
            sys.exit(f"{args.env_file} is missing {key}")

    if args.dry_run:
        print(f"would create table {TABLE_NAME!r} with {len(FIELDS)} fields")
        for f in FIELDS:
            print(f"  {f['field_name']:<10} type={f['type']}")
        return 0

    auth = call("", "POST", "/auth/v3/tenant_access_token/internal", {
        "app_id": env["FEISHU_APP_ID"], "app_secret": env["FEISHU_APP_SECRET"]})
    if auth.get("code") != 0:
        sys.exit(f"auth failed: {auth.get('code')} {auth.get('msg')}")
    token = auth["tenant_access_token"]
    app_token = env["FEISHU_BITABLE_APP_TOKEN"]

    existing = call(token, "GET", f"/bitable/v1/apps/{app_token}/tables?page_size=100")
    if existing.get("code") != 0:
        sys.exit(f"list tables failed: {existing.get('code')} {existing.get('msg')}")
    for item in existing["data"]["items"]:
        if item.get("name") == TABLE_NAME:
            print(f"already exists: {item['table_id']}  {TABLE_NAME}")
            return 0

    created = call(token, "POST", f"/bitable/v1/apps/{app_token}/tables", {
        "table": {"name": TABLE_NAME, "default_view_name": "全部吐槽", "fields": FIELDS}})
    if created.get("code") != 0:
        sys.exit(f"create table failed: {created.get('code')} {created.get('msg')}")

    table_id = created["data"]["table_id"]
    print(f"created: {table_id}  {TABLE_NAME}")

    fields = call(token, "GET", f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields?page_size=100")
    if fields.get("code") == 0:
        print(f"fields ({len(fields['data']['items'])}):",
              ", ".join(f["field_name"] for f in fields["data"]["items"]))
    print()
    print("config line for the site:")
    print(f"  FEISHU_FEEDBACK={env['FEISHU_APP_ID']}:<secret>:{app_token}:{table_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
