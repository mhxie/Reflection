#!/usr/bin/env python3
"""Deterministic stripper + hasher for /sync.

Reads a wiki entry under zk/wiki/, strips fenced ```anchors blocks,
renders each claim's @anchor / @cite / @pass markers as a human-readable
**Sources:** bullet list, appends a synced-from footer, and prints either
the stripped body or its sha256.

Usage:
    scripts/sync_export.py hash zk/wiki/foo.md
    scripts/sync_export.py body zk/wiki/foo.md [--synced-at YYYY-MM-DD]
    scripts/sync_export.py manifest zk/wiki/   # walks dir, emits JSON per file

The LLM should never touch the bytes directly. This script is the single
source of truth for what gets hashed and what gets sent to create_note.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

CLAIM_HEADING_RE = re.compile(r"^###\s+\[C(\d+)\]")
FENCE_OPEN_RE = re.compile(r"^```anchors\s*$")
FENCE_CLOSE_RE = re.compile(r"^```\s*$")


MARKER_PREFIX_RE = re.compile(r"^@(anchor|cite|pass):\s*")


def prettify_marker(raw: str) -> str:
    """Turn `@anchor: arxiv:2501.13956 | valid_at: 2026-04-06` into
    `arxiv:2501.13956 (valid from 2026-04-06)`. Unknown forms pass through
    with the leading `@kind:` prefix stripped."""
    line = MARKER_PREFIX_RE.sub("", raw).strip()
    parts = [p.strip() for p in line.split("|")]
    head = parts[0]
    meta = {}
    for p in parts[1:]:
        if ":" in p:
            k, _, v = p.partition(":")
            meta[k.strip()] = v.strip()
    suffix_bits = []
    if "valid_at" in meta and "invalid_at" in meta:
        suffix_bits.append(f"valid {meta['valid_at']} — {meta['invalid_at']}")
    elif "valid_at" in meta:
        suffix_bits.append(f"valid from {meta['valid_at']}")
    elif "invalid_at" in meta:
        suffix_bits.append(f"invalidated {meta['invalid_at']}")
    for k in ("status", "at", "by"):
        if k in meta:
            suffix_bits.append(f"{k}: {meta[k]}")
    if suffix_bits:
        return f"{head} ({'; '.join(suffix_bits)})"
    return head


def render_sources_footer(markers: list[str]) -> list[str]:
    if not markers:
        return []
    out = ["", "**Sources:**"]
    out.extend(f"- {prettify_marker(m)}" for m in markers)
    return out


def strip_body(path: Path, synced_at: str) -> str:
    """Single streaming pass mirroring scripts/trust.py positional scoping.

    Anchor markers live inside fenced ```anchors blocks; each block is
    positionally scoped to the most recent `### [Cn]` heading. We drop the
    fenced blocks from the output and render their markers as a human-readable
    `**Sources:**` footer under the corresponding claim (before the next
    heading).
    """
    raw_lines = path.read_text(encoding="utf-8").splitlines()

    # Strip a leading H1 (and any blank lines immediately after it) — Reflect
    # auto-prepends the subject as an H1, so including our own produces a
    # duplicate title in the rendered note.
    lines = list(raw_lines)
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# ") and not stripped.startswith("## "):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            lines = lines[j:]
        break

    # Pass 1: collect markers per claim, using positional scoping.
    claim_markers: dict[int, list[str]] = {}
    current_claim: int | None = None
    in_fence = False
    for raw in lines:
        line = raw.rstrip()
        heading_match = CLAIM_HEADING_RE.match(line)
        if heading_match and not in_fence:
            current_claim = int(heading_match.group(1))
            claim_markers.setdefault(current_claim, [])
            continue
        if FENCE_OPEN_RE.match(line):
            in_fence = True
            continue
        if in_fence and FENCE_CLOSE_RE.match(line):
            in_fence = False
            continue
        if in_fence and current_claim is not None and line.strip():
            claim_markers[current_claim].append(line.strip())

    # Pass 2: rebuild the body, dropping fences and inserting Sources footers
    # immediately before the next heading after a claim's prose.
    out: list[str] = []
    current_claim = None
    pending: list[str] = []
    in_fence = False
    for raw in lines:
        line = raw.rstrip()
        if FENCE_OPEN_RE.match(line):
            in_fence = True
            continue
        if in_fence:
            if FENCE_CLOSE_RE.match(line):
                in_fence = False
            continue
        heading_match = CLAIM_HEADING_RE.match(line)
        is_any_heading = line.startswith("## ") or line.startswith("### ")
        if is_any_heading and pending:
            out.extend(render_sources_footer(pending))
            out.append("")
            pending = []
        if heading_match:
            current_claim = int(heading_match.group(1))
            pending = list(claim_markers.get(current_claim, []))
        elif is_any_heading:
            current_claim = None
        out.append(line)
    if pending:
        out.extend(render_sources_footer(pending))

    # Collapse trailing blank lines and append the synced-from footer.
    while out and not out[-1].strip():
        out.pop()
    stripped = "\n".join(out) + "\n"
    footer = (
        "\n---\n\n"
        f"_Synced from `{path.as_posix()}` on {synced_at}. "
        "Local is authoritative — edits here will not be pulled back._\n"
    )
    return stripped + footer


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_hash = sub.add_parser("hash", help="print sha256 of stripped body")
    p_hash.add_argument("path", type=Path)
    p_hash.add_argument("--synced-at", default=date.today().isoformat())

    p_body = sub.add_parser("body", help="print the stripped body to stdout")
    p_body.add_argument("path", type=Path)
    p_body.add_argument("--synced-at", default=date.today().isoformat())

    p_manifest = sub.add_parser(
        "manifest",
        help="walk a directory and emit JSON {slug, path, sha256, title} per file",
    )
    p_manifest.add_argument("dir", type=Path)
    p_manifest.add_argument("--synced-at", default=date.today().isoformat())

    args = parser.parse_args()

    if args.cmd == "hash":
        body = strip_body(args.path, args.synced_at)
        print(sha256_hex(body))
        return 0

    if args.cmd == "body":
        sys.stdout.write(strip_body(args.path, args.synced_at))
        return 0

    if args.cmd == "manifest":
        entries = []
        for md in sorted(args.dir.glob("*.md")):
            body = strip_body(md, args.synced_at)
            title = ""
            for line in md.read_text(encoding="utf-8").splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
            entries.append(
                {
                    "slug": md.stem,
                    "path": md.as_posix(),
                    "title": title,
                    "sha256": sha256_hex(body),
                }
            )
        print(json.dumps(entries, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
