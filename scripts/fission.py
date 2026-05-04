#!/usr/bin/env python3
"""Generic directory fission per protocols/repo-conventions.md (32-entry rule).

Splits the immediate .md children of a directory into bucket subdirs along a
configured axis. Subdirs already inside the target are left in place.

Workflow: this script only moves files. After fission, run scripts/relink.py
to fix any broken markdown refs.

Axes:
  first-letter      Bucket A, B, …, Z, 0-9, CJK by stem[0]
  year-month        YYYY-MM/ from filename prefix YYYY-MM-DD-…
  year-year-month   YYYY/YYYY-MM/ two-level (used by daily-notes)

Usage:
  uv run scripts/fission.py --dir zk/wiki --axis first-letter --dry-run
  uv run scripts/fission.py --dir zk/agent-findings --axis first-letter --apply
  uv run scripts/fission.py --dir zk/reflections --axis year-month --apply
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path
from typing import Callable, Optional, Union

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from _paths import vault_root  # type: ignore[import-not-found]  # noqa: E402

OV = vault_root()


def axis_first_letter(path: Path) -> str:
    stem = path.stem
    if not stem:
        return "_"
    c = stem[0]
    if c.isascii() and c.isalpha():
        return c.upper()
    if c.isdigit():
        return "0-9"
    return "CJK"


def axis_year_month(path: Path) -> Optional[str]:
    m = re.match(r"^(\d{4})-(\d{2})", path.stem)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return None


def axis_year_year_month(path: Path) -> Optional[tuple[str, str]]:
    m = re.match(r"^(\d{4})-(\d{2})", path.stem)
    if m:
        return (m.group(1), f"{m.group(1)}-{m.group(2)}")
    return None


AxisFn = Callable[[Path], Union[str, tuple[str, str], None]]
AXES: dict[str, AxisFn] = {
    "first-letter": axis_first_letter,
    "year-month": axis_year_month,
    "year-year-month": axis_year_year_month,
}


def plan_moves(
    target_dir: Path,
    axis_fn: AxisFn,
    include_dirs: bool = False,
) -> tuple[list[tuple[Path, Path]], list[Path]]:
    """Plan moves. Returns (moves, unmoved) where unmoved are entries the
    axis couldn't bucket (e.g., year-month axis on a non-dated filename).

    If include_dirs=True, also bucket immediate subdirectories (e.g.,
    research/frontier-labs/labs/<lab>/ → labs/<letter>/<lab>/)."""
    moves: list[tuple[Path, Path]] = []
    unmoved: list[Path] = []
    for f in sorted(target_dir.iterdir()):
        is_md = f.is_file() and f.suffix == ".md"
        is_dir_entry = include_dirs and f.is_dir() and not f.name.startswith(".")
        if not (is_md or is_dir_entry):
            continue
        bucket = axis_fn(f)
        if bucket is None:
            unmoved.append(f)
            continue
        if isinstance(bucket, tuple):
            dst = target_dir.joinpath(*bucket, f.name)
        else:
            dst = target_dir / bucket / f.name
        moves.append((f, dst))
    return moves, unmoved


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="Target directory (relative or absolute)")
    ap.add_argument("--axis", required=True, choices=list(AXES))
    ap.add_argument("--include-dirs", action="store_true",
                    help="Also bucket immediate subdirs (not just .md files)")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    target = Path(args.dir).resolve()
    if not target.is_dir():
        print(f"[error] not a directory: {target}", file=sys.stderr)
        sys.exit(1)

    axis_fn = AXES[args.axis]
    moves, unmoved = plan_moves(target, axis_fn, include_dirs=args.include_dirs)
    print(f"[plan] {len(moves)} files to move, {len(unmoved)} unmovable", file=sys.stderr)

    # Bucket count summary
    buckets: dict[str, int] = {}
    for _, dst in moves:
        bucket_name = "/".join(dst.relative_to(target).parts[:-1])
        buckets[bucket_name] = buckets.get(bucket_name, 0) + 1
    print(f"[plan] {len(buckets)} buckets:", file=sys.stderr)
    for b, n in sorted(buckets.items()):
        print(f"        {b}/  ({n} files)", file=sys.stderr)
    if unmoved:
        print(f"[plan] unmovable (no axis match):", file=sys.stderr)
        for f in unmoved[:5]:
            print(f"        {f.name}", file=sys.stderr)
        if len(unmoved) > 5:
            print(f"        ... +{len(unmoved) - 5} more", file=sys.stderr)

    if args.apply:
        for src, dst in moves:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
        print(f"[apply] moved {len(moves)} files", file=sys.stderr)
        print(f"[next] run: uv run scripts/relink.py --apply", file=sys.stderr)
    else:
        print(f"[dry-run] would move {len(moves)} files", file=sys.stderr)


if __name__ == "__main__":
    main()
