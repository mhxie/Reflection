#!/usr/bin/env python3
"""Fix broken markdown links after file moves.

Scans every tracked .md for `[text](path.md)` and `![alt](path.{img})` refs.
For each ref where the path doesn't resolve (broken), looks up the filename
stem in a global index and rewrites the ref to point at the file's current
location (relative path from the source file's dir).

Usage:
  uv run scripts/relink.py --dry-run
  uv run scripts/relink.py --apply
  uv run scripts/relink.py --apply --quiet
"""

from __future__ import annotations

import argparse
import re
import sys
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from _paths import vault_root  # type: ignore[import-not-found]  # noqa: E402

OV = vault_root()
SKIP_DIRS = {"secure", "personal", "cache", ".obsidian", ".trash", "raw", "assets"}

LINK_RE = re.compile(r"(!?\[)([^\]]*)(\]\()<?([^)>#]+)(#[^)>]*)?>?(\))")
TRACKED_EXTS = (".md", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")


def is_tracked_path(rel: Path) -> bool:
    return not any(p in SKIP_DIRS for p in rel.parts)


def build_index(zk: Path) -> dict[str, list[Path]]:
    """name (lowercased) → list of paths (relative to zk)."""
    idx: dict[str, list[Path]] = defaultdict(list)
    for f in zk.rglob("*"):
        if not f.is_file():
            continue
        if f.suffix.lower() not in TRACKED_EXTS:
            continue
        rel = f.relative_to(zk)
        if not is_tracked_path(rel):
            continue
        idx[f.name.lower()].append(rel)
    return idx


def resolve_target(name: str, source_rel: Path, idx: dict[str, list[Path]]) -> Optional[Path]:
    """Look up file name in index; return best match (source-tier-aware)."""
    matches = idx.get(name.lower(), [])
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]
    source_tier = source_rel.parts[0] if source_rel.parts else None
    same_tier = [m for m in matches if m.parts and m.parts[0] == source_tier]
    if same_tier:
        return same_tier[0]
    wiki = [m for m in matches if m.parts and m.parts[0] == "wiki"]
    if wiki:
        return wiki[0]
    return matches[0]


def relative_path(target_rel: Path, source_rel: Path) -> str:
    source_parts = source_rel.parts[:-1]
    target_parts = target_rel.parts
    common = 0
    for a, b in zip(source_parts, target_parts):
        if a == b:
            common += 1
        else:
            break
    ups = len(source_parts) - common
    rest = target_parts[common:]
    parts = [".."] * ups + list(rest)
    return "/".join(parts) if parts else target_rel.name


def maybe_wrap(path: str) -> str:
    if any(c in path for c in " ()"):
        return f"<{path}>"
    return path


def relink_file(path: Path, idx: dict[str, list[Path]]) -> tuple[str, list[tuple[str, str]]]:
    """Returns (new_text, list of (old_link, new_link) diffs)."""
    text = path.read_text(encoding="utf-8")
    source_rel = path.resolve().relative_to(OV)
    diffs: list[tuple[str, str]] = []

    def _sub(m: re.Match) -> str:
        bracket_open = m.group(1)
        link_text = m.group(2)
        bracket_close = m.group(3)
        href = m.group(4).strip()
        anchor = m.group(5) or ""
        paren_close = m.group(6)
        # Skip URLs and absolute paths (no rewrite)
        if href.startswith(("http://", "https://", "mailto:", "/", "#")):
            return m.group(0)
        # Skip non-tracked extensions
        if not any(href.lower().endswith(ext) for ext in TRACKED_EXTS):
            return m.group(0)
        # Resolve current href relative to source dir
        source_dir = path.parent
        target_abs = (source_dir / href).resolve()
        try:
            target_rel_existing = target_abs.relative_to(OV)
        except ValueError:
            return m.group(0)  # outside zk
        if target_abs.exists():
            return m.group(0)  # not broken; skip
        # Broken: try to resolve via name index
        name = Path(href).name
        new_target = resolve_target(name, source_rel, idx)
        if not new_target:
            return m.group(0)  # still unresolved; leave alone
        new_rel = relative_path(new_target, source_rel)
        new_path = maybe_wrap(new_rel + anchor)
        new_link = f"{bracket_open}{link_text}{bracket_close}{new_path}{paren_close}"
        diffs.append((m.group(0), new_link))
        return new_link

    new_text = LINK_RE.sub(_sub, text)
    return new_text, diffs


def main() -> None:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    print(f"[index] building name index from {OV}", file=sys.stderr)
    idx = build_index(OV)
    print(f"[index] {sum(len(v) for v in idx.values())} files, {len(idx)} distinct names",
          file=sys.stderr)

    files = [
        f for f in sorted(OV.rglob("*.md"))
        if is_tracked_path(f.relative_to(OV))
    ]
    print(f"[scan] {len(files)} tracked .md files", file=sys.stderr)

    files_changed = 0
    total_replacements = 0
    for f in files:
        new_text, diffs = relink_file(f, idx)
        if not diffs:
            continue
        files_changed += 1
        total_replacements += len(diffs)
        rel = f.relative_to(OV)
        if not args.quiet:
            print(f"\n=== {rel} ({len(diffs)} relinks) ===")
            for old, new in diffs:
                print(f"  - {old}")
                print(f"  + {new}")
        if args.apply:
            f.write_text(new_text, encoding="utf-8")

    action = "applied" if args.apply else "dry-run"
    print(f"\n[done] {files_changed} files changed, {total_replacements} relinks ({action})",
          file=sys.stderr)


if __name__ == "__main__":
    main()
