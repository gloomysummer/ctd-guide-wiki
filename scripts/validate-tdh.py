#!/usr/bin/env python3
"""
TDH Industrial Quality Gate Linter
----------------------------------
Validates built HTML pages against Google SERP standards:
- Title <= 60 characters
- Meta Description between 100 and 160 characters
- Exactly one H1 tag per page, H1 <= 60 characters
"""

import argparse
import os
import sys
from pathlib import Path
from bs4 import BeautifulSoup


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"


def validate_dist(dist_dir: Path, strict: bool = True) -> bool:
    if not dist_dir.exists():
        print(f"{Colors.RED}[✗] Error: Dist directory {dist_dir} does not exist.{Colors.END}")
        return False

    html_files = []
    for root, _, files in os.walk(dist_dir):
        for f in files:
            if f.endswith(".html") and not f.startswith("google") and f != "404.html":
                html_files.append(Path(root) / f)

    if not html_files:
        print(f"{Colors.YELLOW}[!] Warning: No HTML files found in {dist_dir}.{Colors.END}")
        return True

    print("\n" + "=" * 78)
    print(f"{Colors.BOLD}TDH Quality Gate Verification (Google SERP Standard){Colors.END}")
    print(f"Scanning Directory: {Colors.CYAN}{dist_dir}{Colors.END} ({len(html_files)} pages)")
    print("=" * 78)
    print(f"{'PAGE PATH':<44} | {'TITLE':<6} | {'DESC':<5} | {'H1':<4} | {'STATUS'}")
    print("-" * 78)

    all_passed = True
    violations = []

    for fpath in sorted(html_files):
        rel_path = str(fpath.relative_to(dist_dir))
        with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
            soup = BeautifulSoup(fp.read(), "html.parser")

        title_el = soup.find("title")
        title = title_el.get_text().strip() if title_el else ""

        desc_el = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        desc = desc_el.get("content", "").strip() if desc_el else ""

        h1s = [h.get_text().strip() for h in soup.find_all("h1")]

        t_len = len(title)
        d_len = len(desc)
        h1_len = len(h1s[0]) if h1s else 0
        h1_count = len(h1s)

        t_ok = (0 < t_len <= 60)
        d_ok = (100 <= d_len <= 160)
        h1_ok = (h1_count == 1 and 0 < h1_len <= 60)

        is_pass = t_ok and d_ok and h1_ok
        if not is_pass:
            all_passed = False
            issues = []
            if not t_ok:
                issues.append(f"Title length {t_len} > 60 chars")
            if not d_ok:
                issues.append(f"Desc length {d_len} not in [100, 160]")
            if h1_count != 1:
                issues.append(f"H1 count is {h1_count} (must be 1)")
            elif not h1_ok:
                issues.append(f"H1 length {h1_len} > 60 chars")
            violations.append((rel_path, issues, title, desc))

        status_str = f"{Colors.GREEN}✓ PASS{Colors.END}" if is_pass else f"{Colors.RED}✗ FAIL{Colors.END}"
        print(f"{rel_path[:44]:<44} | {t_len:<6} | {d_len:<5} | {h1_len:<4} | {status_str}")

    print("-" * 78)

    if all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}[✓] 100% PERFECT PASS! All pages strictly satisfy Google SERP TDH standards.{Colors.END}\n")
        return True
    else:
        print(f"{Colors.RED}{Colors.BOLD}[✗] Quality Gate FAILED! Found {len(violations)} pages with TDH violations:{Colors.END}")
        for path, issues, t, d in violations:
            print(f"\n  • {Colors.YELLOW}/{path}{Colors.END}:")
            for issue in issues:
                print(f"    - {issue}")
            print(f"    - Current Title ({len(t)}): \"{t}\"")
            print(f"    - Current Desc  ({len(d)}): \"{d}\"")
        print()
        return False


def main():
    parser = argparse.ArgumentParser(description="Validate built HTML against Google SERP TDH standards.")
    parser.add_argument("--dist", default="dist", help="Path to built static directory (default: dist)")
    parser.add_argument("--lenient", action="store_true", help="Do not exit with code 1 on failure")
    args = parser.parse_args()

    success = validate_dist(Path(args.dist).resolve())
    if not success and not args.lenient:
        sys.exit(1)


if __name__ == "__main__":
    main()
