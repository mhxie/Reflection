#!/usr/bin/env python3
"""
snapshot_anchors.py: Save url: and gist: wiki anchors to Readwise Reader
and backfill the readwise: document ID into the anchor marker.

Why this exists: wiki anchors with url: or gist: types reference ephemeral
web content. If the URL goes down, the evidence backing the wiki claim is
lost. Readwise Reader snapshots web content at save time and stores it
permanently, making the evidence durable (L3). The readwise: field on an
anchor marker records the Readwise document ID so the evidence can be
retrieved regardless of whether the original URL is still live.

Usage:
    # Dry run: show what would be saved (no writes)
    scripts/snapshot_anchors.py

    # Save to Readwise and backfill IDs into wiki files
    scripts/snapshot_anchors.py --apply

    # Process a single wiki entry
    scripts/snapshot_anchors.py --apply --note zk/wiki/some-entry.md

    # Skip URL categories that don't scrape well
    scripts/snapshot_anchors.py --apply --skip-categories github_code,deepwiki

    # Just report: show URLs grouped by category
    scripts/snapshot_anchors.py --report

Exit codes:
    0  All anchors processed (or dry run)
    1  Some anchors failed to save to Readwise (partial success)
    2  CLI/IO error

See also:
    protocols/wiki-schema.md   anchor evidence resolution, readwise: field
    scripts/lint.py            WARN on missing readwise: (readwise-missing)
    sources/readwise.md        Readwise CLI reference
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

WIKI_DIR = Path("zk/wiki")

# Regex to match anchor lines with url: or gist: types
# Captures: full line, anchor type+id, and optional readwise field
ANCHOR_LINE_RE = re.compile(
    r"^(@anchor:\s+(?:url|gist):(\S+).*?)(\s*\|\s*readwise:\s*\S+)?\s*$"
)

# URL category patterns for --skip-categories and --report
URL_CATEGORIES = {
    "github_code": re.compile(r"github\.com/.+/blob/"),
    "github_issue": re.compile(r"github\.com/.+/(issues|discussions|pull)/"),
    "github_repo": re.compile(r"github\.com/[^/]+/[^/]+/?$"),
    "docs": re.compile(r"docs\.(ray\.io|anyscale\.com)"),
    "deepwiki": re.compile(r"deepwiki\.com"),
    "wikipedia": re.compile(r"wikipedia\.org"),
    "pdf": re.compile(r"\.(pdf|PDF)($|\?)"),
    "article": re.compile(r".*"),  # catch-all, must be last
}


def categorize_url(url: str) -> str:
    """Return the category name for a URL. Categories are checked in order;
    'article' is the catch-all."""
    for name, pattern in URL_CATEGORIES.items():
        if name == "article":
            continue
        if pattern.search(url):
            return name
    return "article"


def find_anchors_missing_readwise(
    note_path: Path | None = None,
) -> list[dict]:
    """Scan wiki files and return anchors missing the readwise: field.

    Returns a list of dicts:
        {path, line_no, line, url, anchor_type, category}
    """
    if note_path:
        files = [note_path]
    else:
        files = sorted(WIKI_DIR.glob("*.md"))

    results = []
    for fpath in files:
        lines = fpath.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines, 1):
            m = ANCHOR_LINE_RE.match(line)
            if not m:
                continue
            # Skip lines that already have readwise: field
            if m.group(3):
                continue
            url = m.group(2)
            atype = "gist" if line.strip().startswith("@anchor: gist:") else "url"
            results.append(
                {
                    "path": fpath,
                    "line_no": i,
                    "line": line,
                    "url": url,
                    "anchor_type": atype,
                    "category": categorize_url(url),
                }
            )
    return results


def search_readwise_for_url(url: str) -> str | None:
    """Check if a URL is already saved in Readwise Reader.
    Returns the document ID if found, None otherwise.

    Uses reader-list-documents with source_url matching rather than
    reader-search-documents, because search uses hybrid/semantic matching
    and may return unrelated results.
    """
    try:
        result = subprocess.run(
            [
                "readwise",
                "reader-search-documents",
                "--query", url,
                "--limit", "5",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        docs = json.loads(result.stdout)
        if not isinstance(docs, list):
            return None
        # Match by source_url field (exact or contained)
        for doc in docs:
            source_url = doc.get("source_url", "") or ""
            doc_url = doc.get("url", "") or ""
            if url in source_url or url in doc_url:
                return doc.get("document_id") or doc.get("id")
        return None
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return None


def save_to_readwise(url: str) -> str | None:
    """Save a URL to Readwise Reader with the anchor-evidence tag.
    Returns the document ID on success, None on failure."""
    try:
        result = subprocess.run(
            [
                "readwise",
                "reader-create-document",
                "--url", url,
                "--tags", "anchor-evidence",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            sys.stderr.write(
                f"  readwise save failed for {url}: {result.stderr.strip()}\n"
            )
            return None
        data = json.loads(result.stdout)
        # The create-document response may have different shapes
        doc_id = data.get("document_id") or data.get("id")
        if doc_id:
            return doc_id
        sys.stderr.write(
            f"  readwise save returned no ID for {url}: {result.stdout.strip()}\n"
        )
        return None
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
        sys.stderr.write(f"  readwise save error for {url}: {e}\n")
        return None


def backfill_readwise_id(path: Path, line_no: int, doc_id: str) -> bool:
    """Add | readwise: <doc_id> to an anchor line in a wiki file.
    Returns True on success."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    idx = line_no - 1  # 0-based
    if idx >= len(lines):
        sys.stderr.write(f"  line {line_no} out of range in {path}\n")
        return False

    line = lines[idx]
    m = ANCHOR_LINE_RE.match(line.rstrip("\n"))
    if not m:
        sys.stderr.write(f"  line {line_no} in {path} no longer matches anchor pattern\n")
        return False

    # Already has readwise: (race condition check)
    if m.group(3):
        return True

    # Insert readwise: field before the newline
    stripped = line.rstrip("\n")
    new_line = f"{stripped} | readwise: {doc_id}\n"
    lines[idx] = new_line
    path.write_text("".join(lines), encoding="utf-8")
    return True


def report_categories(anchors: list[dict]) -> str:
    """Group missing-readwise anchors by category and return a report."""
    by_cat: dict[str, list[str]] = {}
    seen_urls: set[str] = set()
    for a in anchors:
        url = a["url"]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        cat = a["category"]
        by_cat.setdefault(cat, []).append(url)

    lines = [f"Anchor snapshot report: {len(seen_urls)} unique URLs missing readwise:", ""]
    for cat in URL_CATEGORIES:
        urls = by_cat.get(cat, [])
        if not urls:
            continue
        lines.append(f"  {cat} ({len(urls)}):")
        for url in sorted(urls):
            lines.append(f"    {url}")
        lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scripts/snapshot_anchors.py",
        description="Save wiki url:/gist: anchors to Readwise and backfill document IDs.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually save to Readwise and write IDs back to wiki files. "
             "Without this flag, only a dry run is performed.",
    )
    parser.add_argument(
        "--note",
        type=Path,
        default=None,
        help="Process a single wiki entry instead of all entries.",
    )
    parser.add_argument(
        "--skip-categories",
        type=str,
        default=None,
        help="Comma-separated list of URL categories to skip. "
             "Valid: github_code, github_issue, github_repo, docs, deepwiki, "
             "wikipedia, pdf, article",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Show URLs grouped by category, then exit.",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=1.5,
        help="Seconds to wait between Readwise API calls (default: 1.5).",
    )
    args = parser.parse_args(argv)

    if not WIKI_DIR.is_dir():
        sys.stderr.write(f"error: {WIKI_DIR} not found. Run from the repo root.\n")
        return 2

    anchors = find_anchors_missing_readwise(args.note)

    if not anchors:
        print("All url:/gist: anchors already have readwise: IDs. Nothing to do.")
        return 0

    if args.report:
        print(report_categories(anchors))
        return 0

    # Deduplicate by URL: save each URL once, then backfill all occurrences
    skip_cats = set()
    if args.skip_categories:
        skip_cats = {c.strip() for c in args.skip_categories.split(",")}

    url_to_anchors: dict[str, list[dict]] = {}
    for a in anchors:
        if a["category"] in skip_cats:
            continue
        url_to_anchors.setdefault(a["url"], []).append(a)

    if not url_to_anchors:
        print("All remaining anchors are in skipped categories. Nothing to do.")
        return 0

    print(f"Found {len(url_to_anchors)} unique URLs to process "
          f"({sum(len(v) for v in url_to_anchors.values())} anchor lines total)")

    if not args.apply:
        print("\nDry run (pass --apply to save to Readwise and backfill IDs):\n")
        for url, anchor_list in sorted(url_to_anchors.items()):
            cat = anchor_list[0]["category"]
            locations = ", ".join(
                f"{a['path'].name}:{a['line_no']}" for a in anchor_list
            )
            print(f"  [{cat:15s}] {url}")
            print(f"                    in: {locations}")
        return 0

    # Apply mode: save to Readwise and backfill
    saved = 0
    failed = 0
    already_in_readwise = 0

    for url, anchor_list in sorted(url_to_anchors.items()):
        cat = anchor_list[0]["category"]
        print(f"  [{cat:15s}] {url} ... ", end="", flush=True)

        # Step 1: check if already in Readwise
        doc_id = search_readwise_for_url(url)
        if doc_id:
            print(f"already saved (ID: {doc_id})")
            already_in_readwise += 1
        else:
            # Step 2: save to Readwise
            time.sleep(args.rate_limit)  # rate limiting
            doc_id = save_to_readwise(url)
            if not doc_id:
                print("FAILED")
                failed += 1
                continue
            print(f"saved (ID: {doc_id})")
            saved += 1

        # Step 3: backfill all occurrences in wiki files
        for a in anchor_list:
            ok = backfill_readwise_id(a["path"], a["line_no"], doc_id)
            if ok:
                print(f"    backfilled {a['path'].name}:{a['line_no']}")
            else:
                print(f"    FAILED to backfill {a['path'].name}:{a['line_no']}")

    print(f"\nDone: {saved} newly saved, {already_in_readwise} already in Readwise, "
          f"{failed} failed")
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
