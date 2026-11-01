#!/usr/bin/env python3
"""
Universal Microsoft Bing & IndexNow Batch Submitter
Protocol: https://www.indexnow.org/documentation

Supported Engines: Microsoft Bing, Yandex, Seznam, Naver
Features:
- Auto-detects domain/host from site.config.ts, site_config.ts, or astro.config.mjs
- Auto-detects IndexNow key from public/<hex32>.txt or site configuration
- Supports batch sitemap submission or incremental modified URL submission
- Online verification check before submission
"""

import sys
import os
import re
import json
import uuid
import argparse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path

INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"

STATUS_EXPLANATIONS = {
    200: "✅ 200 OK: URLs submitted successfully and validated by IndexNow.",
    202: "🟡 202 Accepted: URLs received, Key validation in progress by search engines.",
    400: "❌ 400 Bad Request: Invalid payload structure or formatting.",
    403: "❌ 403 Forbidden: Key not found or does not match host.",
    422: "❌ 422 Unprocessable: URLs don't belong to the host or key invalid.",
}

def detect_project_root() -> Path:
    """Find the current Astro project root directory."""
    cwd = Path.cwd().resolve()
    for parent in [cwd] + list(cwd.parents):
        if (parent / "package.json").exists() and ((parent / "astro.config.mjs").exists() or (parent / "astro.config.ts").exists()):
            return parent
    return cwd

def detect_host(root: Path) -> str:
    """Extract domain/host from site config files."""
    # 1. Check src/config/site.config.ts
    cfg1 = root / "src" / "config" / "site.config.ts"
    if cfg1.exists():
        content = cfg1.read_text(encoding="utf-8")
        m = re.search(r'siteUrl:\s*["\']https?://([^"\'/]+)["\']', content)
        if m:
            return m.group(1).strip()

    # 2. Check src/site_config.ts
    cfg2 = root / "src" / "site_config.ts"
    if cfg2.exists():
        content = cfg2.read_text(encoding="utf-8")
        m = re.search(r'siteUrl:\s*["\']https?://([^"\'/]+)["\']', content)
        if m:
            return m.group(1).strip()

    # 3. Check astro.config.mjs
    astro_cfg = root / "astro.config.mjs"
    if astro_cfg.exists():
        content = astro_cfg.read_text(encoding="utf-8")
        m = re.search(r'site:\s*["\']https?://([^"\'/]+)["\']', content)
        if m:
            return m.group(1).strip()

    return ""

def detect_key(root: Path) -> tuple[str, str]:
    """Detect (key, key_relative_path) from public/ directory or site config."""
    public_dir = root / "public"
    if public_dir.exists():
        # Look for standard hex key text file (8 to 128 chars, typically 32 chars)
        for f in public_dir.glob("*.txt"):
            stem = f.stem
            if re.fullmatch(r"[0-9a-fA-F]{8,128}", stem):
                content = f.read_text(encoding="utf-8").strip()
                if content == stem:
                    return stem, f"{stem}.txt"

    # Also check site.config.ts for indexing.indexNowKey
    cfg1 = root / "src" / "config" / "site.config.ts"
    if cfg1.exists():
        content = cfg1.read_text(encoding="utf-8")
        m = re.search(r'indexNowKey:\s*["\']([0-9a-fA-F]{8,128})["\']', content)
        if m:
            key_val = m.group(1).strip()
            return key_val, f"{key_val}.txt"

    return "", ""

def check_online_key(key_location: str, key: str) -> bool:
    """Verify if the key file is publicly accessible on the live website."""
    print(f"[*] Checking if verification key is live at: {key_location}", flush=True)
    req = urllib.request.Request(key_location, headers={"User-Agent": "IndexNow-Checker/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8").strip()
            if key in content:
                print("    ✅ Online key verified successfully!", flush=True)
                return True
            else:
                print(f"    ⚠️ Key file returned different content: {content[:50]}", flush=True)
                return False
    except Exception as e:
        print(f"    ⚠️ Key file not reachable yet online ({e}).", flush=True)
        print("    ℹ️ Please ensure the key file in public/ has been deployed via git push / Cloudflare Pages.", flush=True)
        return False

def fetch_sitemap_urls(sitemap_url: str) -> list[str]:
    """Recursively parse XML sitemaps to extract all target URLs."""
    print(f"[*] Fetching sitemap: {sitemap_url}", flush=True)
    req = urllib.request.Request(sitemap_url, headers={"User-Agent": "IndexNow-Submitter/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_content = resp.read()
    except Exception as e:
        print(f"❌ Failed to download sitemap: {e}", file=sys.stderr)
        return []

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        print(f"❌ Failed to parse sitemap XML: {e}", file=sys.stderr)
        return []

    urls = []
    for loc in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
        if loc.text:
            url = loc.text.strip()
            if url.endswith(".xml"):
                urls.extend(fetch_sitemap_urls(url))
            else:
                urls.append(url)
    return list(dict.fromkeys(urls))

def submit_indexnow(host: str, key: str, key_location: str, urls: list[str]) -> bool:
    """Send batch URLs to IndexNow endpoint."""
    if not urls:
        print("❌ No URLs provided to submit.", file=sys.stderr)
        return False

    print(f"[*] Preparing to submit {len(urls)} URLs to IndexNow for {host}...", flush=True)
    payload = {
        "host": host,
        "key": key,
        "keyLocation": key_location,
        "urlList": urls[:10000]
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        INDEXNOW_ENDPOINT,
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "IndexNow-Batch-Submitter/1.0"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            code = resp.getcode()
            print(STATUS_EXPLANATIONS.get(code, f"Status code: {code}"))
            return code in (200, 202)
    except urllib.error.HTTPError as e:
        code = e.code
        err_msg = e.read().decode('utf-8', errors='ignore')
        print(STATUS_EXPLANATIONS.get(code, f"HTTP Error {code}: {err_msg}"), file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ Submission network error: {e}", file=sys.stderr)
        return False

def generate_key(root: Path) -> str:
    """Generate a new 32-character hex IndexNow key and write to public/<key>.txt."""
    public_dir = root / "public"
    public_dir.mkdir(parents=True, exist_ok=True)
    new_key = uuid.uuid4().hex
    key_file = public_dir / f"{new_key}.txt"
    key_file.write_text(f"{new_key}\n", encoding="utf-8")
    print(f"✨ Generated new IndexNow key: {new_key}")
    print(f"📁 Created verification file: {key_file}")
    return new_key

def main():
    root = detect_project_root()
    default_host = detect_host(root)
    detected_key, detected_key_file = detect_key(root)

    parser = argparse.ArgumentParser(description="Universal Microsoft Bing & IndexNow Submitter for Game Wikis")
    parser.add_argument("--host", default=default_host, help=f"Domain host (e.g. scavland.wiki, default: '{default_host}')")
    parser.add_argument("--key", default=detected_key, help="IndexNow 32-char hex API Key")
    parser.add_argument("--sitemap", help="URL of the XML sitemap (default: https://<host>/sitemap-index.xml)")
    parser.add_argument("--urls", nargs="+", help="Specific modified URLs to submit (space or comma-separated)")
    parser.add_argument("--generate-key", action="store_true", help="Generate a new IndexNow key in public/ and exit")
    parser.add_argument("--skip-key-check", action="store_true", help="Skip checking key online before submitting")
    args = parser.parse_args()

    if args.generate_key:
        generate_key(root)
        sys.exit(0)

    host = args.host.strip() if args.host else ""
    # Strip protocol if user passed https://...
    if host.startswith("http://") or host.startswith("https://"):
        host = host.split("://", 1)[1].split("/", 1)[0]

    key = args.key.strip() if args.key else ""

    if not key:
        print("⚠️ No IndexNow key found in public/ or site.config.ts.")
        print("   Generating a fresh key automatically now...")
        key = generate_key(root)
        print("   ⚠️ Note: Deploy the site first before online key verification will pass.")

    if not host:
        print("❌ Could not determine host domain. Please pass --host <domain>.", file=sys.stderr)
        sys.exit(1)

    key_location = f"https://{host}/{key}.txt"
    default_sitemap = f"https://{host}/sitemap-index.xml"

    print("=" * 65)
    print(f"🚀 Microsoft Bing & IndexNow Submitter [{host}]")
    print("=" * 65)

    if not args.skip_key_check:
        check_online_key(key_location, key)

    target_urls = []
    if args.urls:
        for item in args.urls:
            target_urls.extend([u.strip() for u in item.split(",") if u.strip()])
    else:
        sitemap_target = args.sitemap or default_sitemap
        target_urls = fetch_sitemap_urls(sitemap_target)

    if not target_urls:
        print("❌ No URLs found to submit.", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Target URLs ({len(target_urls)} total):")
    for u in target_urls[:5]:
        print(f"    - {u}")
    if len(target_urls) > 5:
        print(f"    ... and {len(target_urls) - 5} more.")

    success = submit_indexnow(host, key, key_location, target_urls)
    if success:
        print("\n✨ Done! Microsoft Bing, Yandex, and IndexNow network have queued these URLs.")
        sys.exit(0)
    else:
        print("\n⚠️ Submission failed or returned an error. Check key deployment status.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
