#!/usr/bin/env python3
"""
people.py: Look up person notes by name fragment.

Why this exists: $OV/archive/people/ contains many files named with
embedded spaces (e.g., "Pinyin Pinyin.md"). Ad-hoc `find ... | xargs grep`
silently splits filenames on whitespace and returns false negatives, so
"the vault has no note for X" assertions made through that pipeline are
unreliable. This script is the canonical lookup tool: it walks the
people directory directly with pathlib (no xargs), matches the query
against the filename stem, and optionally against a body field whose
label the user configures via env var.

Body matching is opt-in. The person-note schema (which field holds the
non-English name) is user-private and not committed. Set
`ATELIER_PEOPLE_NAME_FIELD` to the literal label that precedes the
non-English name in the user's notes (e.g., a label like `Name (lang)`)
to enable body matching. Without it, only filename matching runs and
queries written in non-English script will simply not match unless the
filename itself contains them.

Usage:
    scripts/people.py "fragment"            # match by filename stem
    scripts/people.py "fragment" --json     # JSON output

    # Enable body match for non-English queries:
    ATELIER_PEOPLE_NAME_FIELD='<label>' scripts/people.py "fragment"

Exit codes:
    0  one or more matches printed
    1  no matches found
    2  invalid args or setup error
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import vault_root, fmt  # type: ignore[import-not-found]  # noqa: E402

PEOPLE_DIR = vault_root() / "archive" / "people"
HEAD_LINES = 30  # the bio block sits at the top of every person note

_NAME_FIELD = os.environ.get("ATELIER_PEOPLE_NAME_FIELD", "").strip()
_BODY_NAME_RE: re.Pattern[str] | None = (
    re.compile(rf"^\s*-\s*{re.escape(_NAME_FIELD)}\s*:\s*(\S.*?)\s*$")
    if _NAME_FIELD
    else None
)


def scan(query: str) -> list[dict]:
    if not PEOPLE_DIR.is_dir():
        print(f"ERROR: {fmt(PEOPLE_DIR)} not found.", file=sys.stderr)
        sys.exit(2)
    q_lower = query.lower()
    results: list[dict] = []
    for path in sorted(PEOPLE_DIR.glob("*.md")):
        stem = path.stem
        match_src: str | None = None
        if q_lower in stem.lower():
            match_src = "filename"
        elif _BODY_NAME_RE is not None:
            try:
                head = path.read_text(encoding="utf-8").splitlines()[:HEAD_LINES]
            except OSError:
                continue
            for line in head:
                m = _BODY_NAME_RE.match(line)
                if m and query in m.group(1):
                    match_src = "body"
                    break
        if match_src:
            results.append({"path": fmt(path), "match": match_src, "stem": stem})
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scripts/people.py",
        description="Search $OV/archive/people/ by name fragment.",
    )
    parser.add_argument("query", help="Name fragment.")
    parser.add_argument("--json", action="store_true", help="JSON output.")
    args = parser.parse_args(argv)

    query = args.query.strip()
    if not query:
        print("ERROR: empty query", file=sys.stderr)
        sys.exit(2)

    results = scan(query)

    if args.json:
        json.dump(results, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        for r in results:
            sys.stdout.write(f"{r['path']}\t[{r['match']}]\n")

    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
