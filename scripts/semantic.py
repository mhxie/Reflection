#!/usr/bin/env python3
"""
semantic.py: local semantic search interface for the zk/ vault.

STUB MODE:
    Lexical fallback using tokenized substring matching over the local
    Markdown corpus. Returns path, score, matched-token rows.
    Active when the index directory does NOT exist.

REAL MODE:
    Embedding-backed search using pluggable Embedder + Store backends.
    Day-one stack: BGE-M3 (sentence-transformers) + LanceDB.
    Active when zk/.semantic/lance/ directory exists (sentinel).

The CLI contract is encoder-agnostic and frozen. Swapping the backend from
stub to real will NOT change caller code in command files or agents.

See also:
    sources/semantic.md                          (teaching doc, stable)
    scripts/semantic_backends.py                 (backend implementations)

Usage:
    scripts/semantic.py query "<text>" [OPTIONS]
    scripts/semantic.py index [--rebuild]
    scripts/semantic.py --help

Stdlib only in stub mode. Real mode requires: sentence-transformers, lancedb.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
# Lance index lives inside zk/ so both laptops share it via Drive.
# LanceDB uses few large columnar files, which syncs well.
LANCE_DIR = REPO_ROOT / "zk" / ".semantic" / "lance"
DEFAULT_PATH = "zk"
# Directories excluded from indexing (ephemeral caches, not worth embedding)
INDEX_EXCLUDE = {"zk/cache"}


def in_real_mode() -> bool:
    """Sentinel check: real mode is active iff the lance directory exists."""
    return LANCE_DIR.exists()


def mode_label() -> str:
    return "real" if in_real_mode() else "stub"


def warn(msg: str) -> None:
    """Emit a warning to stderr. Never to stdout (which carries results)."""
    print(f"[semantic.py] {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Stub mode (lexical fallback) -- unchanged from original
# ---------------------------------------------------------------------------

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
    exclude: Optional[set] = None,
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
            # Check exclusion list against relative path
            if exclude:
                try:
                    rel = str(f.relative_to(REPO_ROOT))
                except ValueError:
                    rel = str(f)
                if any(rel.startswith(ex) for ex in exclude):
                    continue
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


def stub_query(args: argparse.Namespace) -> int:
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


# ---------------------------------------------------------------------------
# Real mode (embedding-backed search)
# ---------------------------------------------------------------------------

def _load_trust_scores() -> dict:
    """Load wiki trust scores from trust.py. Returns {relative_path: score}."""
    try:
        from trust import load_wiki, score_notes
        from datetime import date as _date

        notes = load_wiki(as_of=_date.today())
        _, note_scores = score_notes(notes, as_of=_date.today())
        return {str(p): s for p, s in note_scores.items()}
    except Exception:
        return {}


def _build_retriever(with_reranker: bool = True):
    """Lazy-import and construct the Retriever with day-one backends."""
    from semantic_backends import BGEM3Embedder, LanceStore, Retriever, TierRecencyReranker

    warn("loading BGE-M3 model...")
    embedder = BGEM3Embedder()
    warn(f"model loaded (device: {embedder._device}, dim: {embedder.dimension()}, max_tokens: {embedder._max_tokens})")

    store = LanceStore(
        db_path=str(LANCE_DIR),
        embedding_dim=embedder.dimension(),
        model_name=embedder.model_name(),
    )

    reranker = None
    if with_reranker:
        trust = _load_trust_scores()
        if trust:
            warn(f"loaded trust scores for {len(trust)} wiki entries")
        reranker = TierRecencyReranker(trust_scores=trust)

    return Retriever(embedder=embedder, store=store, reranker=reranker)


def real_query(args: argparse.Namespace) -> int:
    warn("real mode: embedding-backed semantic search")

    if not args.query.strip():
        warn("empty query; no results")
        return 0

    retriever = _build_retriever()

    # Build filters from CLI args
    filters = {}
    paths = args.path or [DEFAULT_PATH]
    if paths != [DEFAULT_PATH]:
        filters["path_prefix"] = paths

    after_dt = parse_date(args.after, "--after")
    before_dt = parse_date(args.before, "--before")
    if after_dt:
        filters["mtime_after"] = after_dt.timestamp()
    if before_dt:
        filters["mtime_before"] = before_dt.timestamp()

    t0 = time.time()
    results = retriever.query(args.query, top_k=args.top, filters=filters or None)
    elapsed = time.time() - t0
    warn(f"query returned {len(results)} results in {elapsed:.2f}s")

    if args.format == "json":
        payload = [
            {"path": r.path, "score": r.score, "matched_tokens": []}
            for r in results
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"{r.path}\t{r.score:.3f}\t")

    return 0


def real_index(args: argparse.Namespace) -> int:
    retriever = _build_retriever(with_reranker=False)

    if args.rebuild:
        warn("--rebuild: clearing existing index...")
        retriever.store.clear()

    warn(f"scanning markdown files under {DEFAULT_PATH}/ (excluding {INDEX_EXCLUDE})...")
    files = list(walk_markdown([DEFAULT_PATH], after=None, before=None, exclude=INDEX_EXCLUDE))
    warn(f"found {len(files)} files to scan")

    t0 = time.time()
    if args.rebuild:
        total = retriever.index_files(files, REPO_ROOT, append_only=True)
        warn(f"full rebuild: {total} chunks in {time.time() - t0:.1f}s")
    else:
        added, skipped, removed = retriever.index_incremental(files, REPO_ROOT)
        warn(f"incremental: {added} added, {skipped} unchanged, {removed} removed in {time.time() - t0:.1f}s")

    stats = retriever.stats()
    warn(f"index stats: {stats.total_documents} chunks, {stats.embedding_dimension}d, model={stats.model_name}")
    return 0


# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------

def cmd_query(args: argparse.Namespace) -> int:
    if in_real_mode():
        return real_query(args)
    return stub_query(args)


def cmd_index(args: argparse.Namespace) -> int:
    if in_real_mode():
        return real_index(args)

    # Not in real mode yet: create the sentinel dir and index
    warn("no existing index found; creating zk/.semantic/lance/ and building index...")
    LANCE_DIR.mkdir(parents=True, exist_ok=True)
    return real_index(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="semantic.py",
        description=(
            f"Local semantic search for zk/ (current mode: {mode_label()}). "
            "STUB mode uses lexical fallback; results are ranked by token "
            "match count and are NOT semantic. REAL mode activates when "
            "zk/.semantic/lance/ exists."
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
        help="Force full rebuild.",
    )
    i.set_defaults(func=cmd_index)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
