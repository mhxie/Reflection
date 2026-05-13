#!/usr/bin/env python3
"""rewrite_paths.py: Rename a tier segment across all committed docs.

Why this exists: before the path registry, a tier rename (e.g., `drafts`
→ `wip`) had to be applied by hand across a dozen markdown files. That's
the antipattern `harness/paths.toml` exists to fix; this script is the
mechanical half. One command, one source of truth, one diff.

Workflow:
    1. Edit `harness/paths.toml`: rename the segment to its new value.
    2. Run `uv run scripts/rewrite_paths.py --from <old> --to <new>`.
    3. Review the diff and commit.

The script replaces `$OV/<old>/` → `$OV/<new>/` and `$OV/<old>` (end of
line / no trailing slash) → `$OV/<new>` across all `.md` files under
`CLAUDE.md`, `protocols/`, `.claude/`, and `harness/`. TOML files are
NOT touched (the registry edit in step 1 is the only TOML change
needed; other TOML files reference paths through helper functions, not
literals).

After running, `harness_lint.py path-registry-drift` should pass.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# tomllib is stdlib on Python 3.11+. Fall back to the third-party `tomli`
# backport on older interpreters so the script doesn't hard-fail on a
# user box that's still on 3.10 (uncommon but possible for OSS forks).
try:
    import tomllib  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - exercised only on <3.11
    import tomli as tomllib  # type: ignore[import-not-found, no-redef]

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_registry_segments() -> set[str]:
    """Return the set of registered segments from paths.toml (canonical
    only — paths.local.toml is per-user and ignored here)."""
    return set(load_segment_to_name().keys())


def load_segment_to_name() -> dict[str, str]:
    """Return `{segment: logical_name}` from paths.toml.

    `logical_name` is the canonical key for top-level entries
    (`wip`, `daily_notes`, ...) and `wiki_localized.<lang>` for
    localized shadow wikis. Used by --templatize to choose the
    placeholder form.
    """
    paths_toml = REPO_ROOT / "harness" / "paths.toml"
    if not paths_toml.is_file():
        sys.exit("ERROR: harness/paths.toml not found")
    with paths_toml.open("rb") as f:
        data = tomllib.load(f)
    reg = data.get("paths", {})
    mapping: dict[str, str] = {}
    for k, v in reg.items():
        if isinstance(v, str):
            mapping[v] = k
    for k, v in (reg.get("wiki_localized") or {}).items():
        if isinstance(v, str):
            mapping.setdefault(v, f"wiki_localized.{k}")
    return mapping


def walk_md_files() -> list[Path]:
    """Walk committed-doc roots and return all `.md` files."""
    roots = [
        REPO_ROOT / "CLAUDE.md",
        REPO_ROOT / "protocols",
        REPO_ROOT / ".claude",
        REPO_ROOT / "harness",
    ]
    files: list[Path] = []
    for root in roots:
        if root.is_file() and root.suffix == ".md":
            files.append(root)
        elif root.is_dir():
            files.extend(sorted(root.rglob("*.md")))
    return files


def rewrite_segment(text: str, old: str, new: str) -> tuple[str, int]:
    """Rewrite `$OV/<old>/` → `$OV/<new>/` and `$OV/<old>` boundary
    forms in `text`. Returns (new_text, count_of_replacements).

    Boundary forms:
      - `$OV/<old>/` — trailing slash (directory reference, most common)
      - `$OV/<old>` at end-of-segment (whitespace, punctuation, EOL) —
        for prose like "saved under `$OV/<old>`"
    """
    # Use a single regex with a lookahead for the boundary so we don't
    # accidentally rewrite `$OV/wipfoo/` when renaming `wip`.
    boundary = r"(?=/|\s|[.,;:)`'\"]|$)"
    pattern = re.compile(rf"\$OV/{re.escape(old)}{boundary}")
    new_text, count = pattern.subn(f"$OV/{new}", text)
    return new_text, count


def templatize_text(text: str, mapping: dict[str, str]) -> tuple[str, int]:
    """Replace every `$OV/<seg>/` and `$OV/<seg>` literal in `text` with
    `<paths.<name>>` based on `mapping`. Longer segments first so a
    rename like `wiki-cn` isn't half-consumed by `wiki`.
    """
    count = 0
    new_text = text
    for seg in sorted(mapping.keys(), key=len, reverse=True):
        name = mapping[seg]
        placeholder = f"<paths.{name}>"
        # Trailing slash form: keep the slash inside the placeholder
        # output so downstream substitution yields `<paths.X>/file.md`.
        boundary = r"(?=/|\s|[.,;:)`'\"]|$)"
        pattern = re.compile(rf"\$OV/{re.escape(seg)}{boundary}")
        new_text, n = pattern.subn(placeholder, new_text)
        count += n
    return new_text, count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rename or templatize path-registry tier segments across committed docs."
    )
    parser.add_argument("--from", dest="old", default=None,
                        help="Existing segment name (e.g., drafts). For rename mode.")
    parser.add_argument("--to", dest="new", default=None,
                        help="New segment name (e.g., wip). For rename mode.")
    parser.add_argument("--templatize", action="store_true",
                        help="Replace every $OV/<seg>/ literal in committed .md with <paths.<name>> based on the registry. Run once to convert docs from path literals to placeholders.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without writing.")
    parser.add_argument("--force", action="store_true",
                        help="Skip the registry-membership check for --to.")
    args = parser.parse_args(argv)

    if args.templatize:
        if args.old or args.new:
            sys.exit("ERROR: --templatize is exclusive with --from/--to")
        mapping = load_segment_to_name()
        files = walk_md_files()
        total_files = 0
        total_repls = 0
        for path in files:
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            new_text, count = templatize_text(text, mapping)
            if count == 0:
                continue
            total_files += 1
            total_repls += count
            rel = path.relative_to(REPO_ROOT)
            if args.dry_run:
                print(f"[dry-run] {rel}: {count} literal(s) → placeholder")
            else:
                path.write_text(new_text, encoding="utf-8")
                print(f"{rel}: {count} literal(s) → placeholder")
        summary = f"{'[dry-run] ' if args.dry_run else ''}templatized {total_repls} literal(s) across {total_files} file(s)"
        print(summary)
        return 0

    if not args.old or not args.new:
        sys.exit("ERROR: --from and --to are required for rename mode (or use --templatize)")

    if args.old == args.new:
        sys.exit("ERROR: --from and --to are the same; nothing to do")

    segs = load_registry_segments()
    if not args.force and args.new not in segs:
        sys.exit(
            f"ERROR: target segment '{args.new}' is not in harness/paths.toml. "
            "Add it there first (rename the source entry to its new value), "
            "or pass --force to rewrite anyway."
        )
    if not args.force and args.old in segs:
        sys.exit(
            f"ERROR: source segment '{args.old}' is still in harness/paths.toml. "
            "Rename it to the new value in the registry first; this script "
            "applies the rewrite across docs after the registry update."
        )

    files = walk_md_files()
    total_files = 0
    total_repls = 0
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        new_text, count = rewrite_segment(text, args.old, args.new)
        if count == 0:
            continue
        total_files += 1
        total_repls += count
        rel = path.relative_to(REPO_ROOT)
        if args.dry_run:
            print(f"[dry-run] {rel}: {count} replacement(s)")
        else:
            path.write_text(new_text, encoding="utf-8")
            print(f"{rel}: {count} replacement(s)")

    summary = f"{'[dry-run] ' if args.dry_run else ''}rewrote {total_repls} occurrence(s) across {total_files} file(s)"
    print(summary)
    if not args.dry_run:
        print("Next: review the diff and run `uv run scripts/harness_lint.py` to confirm clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
