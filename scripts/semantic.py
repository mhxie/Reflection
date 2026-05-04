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
    Active when a lance directory exists. Reads prefer
    ~/.cache/atelier/lance/; if absent, fall back to legacy
    ~/.cache/reflectl/lance/ (existing installs migrate on next index).

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
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from _paths import vault_root  # type: ignore[import-not-found]  # noqa: E402

# Lance index is machine-local (rebuild is ~7s on MPS, not worth syncing binaries).
_LANCE_NEW = Path.home() / ".cache" / "atelier" / "lance"
# Reads fall back to the pre-rename location so existing installs keep
# semantic search without a forced rebuild. Writes always go to _LANCE_NEW.
_LANCE_OLD = Path.home() / ".cache" / "reflectl" / "lance"


def _resolve_lance_dir(prefer_new: bool = False) -> Path:
    """Resolve the active lance index directory.

    Reads prefer ~/.cache/atelier/lance/ and fall back to the legacy
    ~/.cache/reflectl/lance/ if present. Writes (prefer_new=True) always
    return the new path so a rebuild migrates the user.
    """
    if prefer_new:
        return _LANCE_NEW
    if _LANCE_NEW.exists():
        return _LANCE_NEW
    if _LANCE_OLD.exists():
        return _LANCE_OLD
    return _LANCE_NEW


# Module-level binding kept for backwards-compat with callers that read it
# directly (e.g. db_path string interpolation). For read-side code paths.
LANCE_DIR = _resolve_lance_dir()
# Default scan root is the vault ($OV). Resolved lazily at use sites
# via vault_root() so `--help` and other no-vault probes work without
# $OV set; only commands that actually walk the vault (query, index)
# require $OV.
DEFAULT_PATH: str | None = None
# Subdirectories under the vault excluded from indexing (ephemeral caches,
# not worth embedding). Trailing slash constrains matching to directories
# (e.g., excludes `$OV/cache/**` but not `$OV/cached_*.md` siblings).
INDEX_EXCLUDE = {"cache/"}


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
    """Yield .md files under the given paths, filtered by mtime window.

    Path resolution: absolute paths are used as-is; relative paths are
    resolved against the vault root ($OV), not the repo root, so a bare
    `--path wiki` scans `$OV/wiki/`.

    Exclusion: each `exclude` entry is matched as a path-prefix against
    the file's path relative to its walk root (e.g., `INDEX_EXCLUDE =
    {"cache"}` excludes `$OV/cache/**`).
    """
    vault = vault_root()
    seen: set = set()
    for p in paths:
        root = Path(p) if Path(p).is_absolute() else (vault / p)
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
            if exclude:
                try:
                    rel = str(f.relative_to(root))
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

    # Resolve $OV early; fail fast before any walk work.
    default_path = str(vault_root())

    paths = args.path or [default_path]
    after = parse_date(args.after, "--after")
    before = parse_date(args.before, "--before")

    if args.lang != "auto":
        warn(f"--lang {args.lang} is a no-op in stub mode")

    vault = vault_root()
    results: List[Tuple[str, float, List[str]]] = []
    for md in walk_markdown(paths, after, before):
        score, matched = lexical_score(md, tokens)
        if score > 0:
            try:
                rel = md.relative_to(vault)
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

    # Resolve $OV early; fail fast before loading the embedder.
    default_path = str(vault_root())

    sources = set(args.sources.split(","))
    retriever = _build_retriever()

    # Build filters from CLI args
    filters = {}
    paths = args.path or [default_path]
    if paths != [default_path]:
        filters["path_prefix"] = paths

    after_dt = parse_date(args.after, "--after")
    before_dt = parse_date(args.before, "--before")
    if after_dt:
        filters["mtime_after"] = after_dt.timestamp()
    if before_dt:
        filters["mtime_before"] = before_dt.timestamp()

    t0 = time.time()
    results = []

    # Local search
    if "local" in sources:
        local_results = retriever.query(args.query, top_k=args.top, filters=filters or None)
        results.extend(local_results)
        warn(f"local: {len(local_results)} results")

    # Readwise federated search
    if "readwise" in sources:
        from semantic_backends import ReadwiseSearcher
        if ReadwiseSearcher.available():
            rw_results = ReadwiseSearcher.search(args.query, top_k=args.top)
            results.extend(rw_results)
            warn(f"readwise: {len(rw_results)} results")
        else:
            warn("readwise: CLI not installed, skipping")

    # Merge by score, take top_k
    results.sort(key=lambda r: -r.score)
    results = results[:args.top]

    elapsed = time.time() - t0
    warn(f"total: {len(results)} results in {elapsed:.2f}s")

    if args.format == "json":
        payload = [
            {"path": r.path, "score": r.score, "source": r.source, "matched_tokens": []}
            for r in results
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"{r.path}\t{r.score:.3f}\t{r.source}")

    return 0


def real_index(args: argparse.Namespace) -> int:
    retriever = _build_retriever(with_reranker=False)

    if args.rebuild:
        warn("--rebuild: clearing existing index...")
        retriever.store.clear()

    vault = vault_root()
    warn(f"scanning markdown files under {vault}/ (excluding {INDEX_EXCLUDE})...")
    files = list(walk_markdown([str(vault)], after=None, before=None, exclude=INDEX_EXCLUDE))
    warn(f"found {len(files)} files to scan")

    t0 = time.time()
    if args.rebuild:
        total = retriever.index_files(files, vault, append_only=True)
        warn(f"full rebuild: {total} chunks in {time.time() - t0:.1f}s")
    else:
        added, skipped, removed = retriever.index_incremental(files, vault)
        warn(f"incremental: {added} added, {skipped} unchanged, {removed} removed in {time.time() - t0:.1f}s")

    stats = retriever.stats()
    warn(f"index stats: {stats.total_documents} chunks, {stats.embedding_dimension}d, model={stats.model_name}")
    return 0


# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------

def cmd_query(args: argparse.Namespace) -> int:
    if in_real_mode() and LANCE_DIR == _LANCE_OLD:
        warn(
            "querying legacy index at ~/.cache/reflectl/lance/; run "
            "`uv run scripts/semantic.py index` once to migrate to "
            "~/.cache/atelier/lance/, then `rm -rf ~/.cache/reflectl/lance` to clean up."
        )
    if in_real_mode():
        return real_query(args)
    return stub_query(args)


def cmd_index(args: argparse.Namespace) -> int:
    # Index always writes to the new path. If a legacy ~/.cache/reflectl/lance/
    # exists, we deliberately do NOT rebuild into it — that would silently keep
    # the user on the old location forever. Force migration here.
    global LANCE_DIR
    LANCE_DIR = _resolve_lance_dir(prefer_new=True)
    if _LANCE_OLD.exists() and not _LANCE_NEW.exists():
        warn(
            "legacy index exists at ~/.cache/reflectl/lance/; rebuilding at "
            "~/.cache/atelier/lance/ to migrate. The old path can be deleted "
            "after this run completes."
        )
    elif not LANCE_DIR.exists():
        warn("no existing index found; creating ~/.cache/atelier/lance/ and building index...")
    LANCE_DIR.mkdir(parents=True, exist_ok=True)
    return real_index(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="semantic.py",
        description=(
            f"Local semantic search for zk/ (current mode: {mode_label()}). "
            "STUB mode uses lexical fallback; results are ranked by token "
            "match count and are NOT semantic. REAL mode activates when "
            "~/.cache/atelier/lance/ exists, with a legacy fallback to "
            "~/.cache/reflectl/lance/ for pre-rename installs."
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
    q.add_argument(
        "--sources",
        default="local,readwise",
        help="Comma-separated search sources. Options: local, readwise. "
        "Default: local,readwise (federated).",
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
