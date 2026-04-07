#!/usr/bin/env python3
"""
semantic.py: local semantic search interface for the zk/ vault.

STUB MODE (current):
    Lexical fallback using tokenized substring matching over the local
    Markdown corpus. Returns path, score, matched-token rows.

REAL MODE (future, Phase B.5-real):
    Embedding-backed search using sentence-transformers + sqlite-vec,
    index stored at zk/.semantic/index.sqlite. Sentinel-detected: if the
    index file exists, real mode is selected; otherwise stub mode runs.

The CLI contract is encoder-agnostic and frozen. Swapping the backend from
stub to real will NOT change caller code in command files or agents.

See also:
    sources/semantic.md                          (teaching doc, stable)
    handoffs/2026-04-06-phase-bcd-trust-engine.md  (Addendum: Phase B.5)

Usage:
    scripts/semantic.py query "<text>" [OPTIONS]
    scripts/semantic.py index [--rebuild]
    scripts/semantic.py --help

Stdlib only. No third-party dependencies in stub mode.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = REPO_ROOT / "zk" / ".semantic" / "index.sqlite"
DEFAULT_PATH = "zk"


def in_real_mode() -> bool:
    """Sentinel check: real mode is active iff the index file exists."""
    return INDEX_PATH.exists()


def mode_label() -> str:
    return "real" if in_real_mode() else "stub"


def warn(msg: str) -> None:
    """Emit a warning to stderr. Never to stdout (which carries results)."""
    print(f"[semantic.py] {msg}", file=sys.stderr)


# Tokenization: split on whitespace and common punctuation including em/en
# dashes and hyphens. Non-ASCII (Chinese, etc.) characters are preserved
# intact since CJK text is typically whitespace-separated at the phrase
# level in this corpus.
_TOKEN_SPLIT = re.compile(r"[\s,./;:!?()\[\]{}\"'`\u2014\u2013-]+")


def tokenize(query: str) -> List[str]:
    return [t.lower() for t in _TOKEN_SPLIT.split(query.strip()) if t]


def parse_date(s: Optional[str], flag_name: str) -> Optional[datetime]:
    if s is None:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        warn(f"invalid {flag_name} value (expected YYYY-MM-DD): {s}")
        sys.exit(2)


def walk_markdown(
    paths: List[str],
    after: Optional[datetime],
    before: Optional[datetime],
) -> Iterator[Path]:
    """Yield .md files under the given paths, filtered by mtime window."""
    seen: set = set()
    for p in paths:
        root = (REPO_ROOT / p) if not Path(p).is_absolute() else Path(p)
        if not root.exists():
            warn(f"path not found, skipping: {p}")
            continue
        if root.is_file():
            candidates: Iterator[Path] = iter([root])
        else:
            candidates = root.rglob("*.md")
        for f in candidates:
            if f in seen:
                continue
            seen.add(f)
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
            except OSError:
                continue
            if after and mtime < after:
                continue
            if before and mtime > before:
                continue
            yield f


def lexical_score(path: Path, tokens: List[str]) -> Tuple[float, List[str]]:
    """
    Stub scoring: count occurrences of any query token in the file.
    Returns (normalized_score, matched_tokens). Score is min(count, 10) / 10,
    so score lives in [0.0, 1.0] and sorts compatibly with cosine similarity.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        return 0.0, []
    matched: List[str] = []
    total = 0
    for tok in tokens:
        n = text.count(tok)
        if n > 0:
            matched.append(tok)
            total += n
    if not matched:
        return 0.0, []
    return min(1.0, total / 10.0), matched


def cmd_query(args: argparse.Namespace) -> int:
    if in_real_mode():
        warn("real mode not implemented yet, falling through to stub")
    warn("stub mode: lexical fallback, results are NOT semantic")

    tokens = tokenize(args.query)
    if not tokens:
        warn("query tokenized to empty; no results")
        return 0

    paths = args.path or [DEFAULT_PATH]
    after = parse_date(args.after, "--after")
    before = parse_date(args.before, "--before")

    if args.lang != "auto":
        warn(f"--lang {args.lang} is a no-op in stub mode")

    results: List[Tuple[str, float, List[str]]] = []
    for md in walk_markdown(paths, after, before):
        score, matched = lexical_score(md, tokens)
        if score > 0:
            try:
                rel = md.relative_to(REPO_ROOT)
            except ValueError:
                rel = md
            results.append((str(rel), score, matched))

    results.sort(key=lambda r: (-r[1], r[0]))
    results = results[: args.top]

    if args.format == "json":
        payload = [
            {"path": p, "score": round(s, 3), "matched_tokens": m}
            for p, s, m in results
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for p, s, m in results:
            print(f"{p}\t{s:.3f}\t{','.join(m)}")
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    if in_real_mode():
        warn("real mode not implemented yet; index command is a no-op")
    else:
        warn("stub mode: no index needed, queries fall through to lexical grep")
    if args.rebuild:
        warn("--rebuild is a no-op in stub mode")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="semantic.py",
        description=(
            f"Local semantic search for zk/ (current mode: {mode_label()}). "
            "STUB mode uses lexical fallback; results are ranked by token "
            "match count and are NOT semantic. REAL mode activates when "
            "zk/.semantic/index.sqlite exists."
        ),
        epilog="See sources/semantic.md for the full contract.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    q = sub.add_parser("query", help="Run a semantic query.")
    q.add_argument("query", help="Query text (quoted).")
    q.add_argument(
        "--path",
        action="append",
        default=None,
        help="Restrict to a subdirectory, relative to repo root. "
        "Repeatable. Default: zk/",
    )
    q.add_argument(
        "--after",
        default=None,
        help="Only files with mtime >= YYYY-MM-DD.",
    )
    q.add_argument(
        "--before",
        default=None,
        help="Only files with mtime <= YYYY-MM-DD.",
    )
    q.add_argument(
        "--top",
        type=int,
        default=10,
        help="Max results. Default: 10.",
    )
    q.add_argument(
        "--lang",
        choices=["zh", "en", "auto"],
        default="auto",
        help="Query language hint. No-op in stub mode.",
    )
    q.add_argument(
        "--format",
        choices=["tsv", "json"],
        default="tsv",
        help="Output format. Default: tsv.",
    )
    q.set_defaults(func=cmd_query)

    i = sub.add_parser("index", help="Build or refresh the embedding index.")
    i.add_argument(
        "--rebuild",
        action="store_true",
        help="Force full rebuild (no-op in stub mode).",
    )
    i.set_defaults(func=cmd_index)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
