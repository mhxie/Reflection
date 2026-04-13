"""
semantic_backends.py: Abstraction layer for semantic search components.

Three Protocol interfaces define the seams:
  - Embedder: text -> vector
  - Store: upsert / search / delete over indexed documents
  - Reranker: reorder candidates (optional, future)

Concrete implementations live in this file alongside the protocols.
Swapping a component (new model, new DB, new ranker) means writing a new
class that satisfies the Protocol, not touching the CLI or other components.

Day-one stack: BGE_M3_Embedder + LanceStore + no reranker.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Sequence, runtime_checkable

import numpy as np
from numpy.typing import NDArray


# ---------------------------------------------------------------------------
# Data types shared across all backends
# ---------------------------------------------------------------------------

@dataclass
class Document:
    """A unit of indexable content."""
    id: str            # "{path}:{chunk_id}"
    path: str          # relative to repo root
    chunk_id: int      # 0 = whole file, 1..N for chunks
    chunk_text: str    # the actual text (stored for re-embedding)
    tier: str          # L1-L5, derived from path prefix
    mtime: float       # file mtime at index time


@dataclass
class SearchResult:
    """A single search hit."""
    path: str
    score: float       # higher is better, [0.0, 1.0] for cosine
    chunk_id: int = 0
    chunk_text: str = ""
    tier: str = ""
    mtime: float = 0.0


@dataclass
class IndexStats:
    """Summary of what's in the index."""
    total_documents: int
    total_chunks: int
    embedding_dimension: int
    model_name: str
    index_path: str


# ---------------------------------------------------------------------------
# Protocol: Embedder
# ---------------------------------------------------------------------------

@runtime_checkable
class Embedder(Protocol):
    """Turns text into vectors. Swappable independently of Store."""

    def encode(self, texts: List[str]) -> NDArray[np.float32]:
        """Encode a batch of texts. Returns (N, D) array."""
        ...

    def dimension(self) -> int:
        """Embedding dimensionality."""
        ...

    def model_name(self) -> str:
        """Human-readable model identifier for index metadata."""
        ...


# ---------------------------------------------------------------------------
# Protocol: Store
# ---------------------------------------------------------------------------

@runtime_checkable
class Store(Protocol):
    """Persists and searches document embeddings. Swappable independently."""

    def add(self, docs: List[Document], vectors: NDArray[np.float32]) -> int:
        """Append-only insert (fast path for initial builds). Returns count."""
        ...

    def upsert(self, docs: List[Document], vectors: NDArray[np.float32]) -> int:
        """Insert or update documents. Returns count of upserted rows."""
        ...

    def search(
        self,
        vector: NDArray[np.float32],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Find nearest neighbors. filters keys: path_prefix, tier, mtime_after, mtime_before."""
        ...

    def delete(self, ids: List[str]) -> int:
        """Delete documents by id. Returns count deleted."""
        ...

    def count(self) -> int:
        """Total indexed rows."""
        ...

    def stats(self) -> IndexStats:
        """Index summary."""
        ...

    def clear(self) -> None:
        """Drop all data (for --rebuild)."""
        ...


# ---------------------------------------------------------------------------
# Protocol: Reranker (future seam, not implemented day-one)
# ---------------------------------------------------------------------------

@runtime_checkable
class Reranker(Protocol):
    """Reorders search candidates. Optional pipeline stage."""

    def rerank(
        self,
        query: str,
        candidates: List[SearchResult],
        top_k: int = 10,
    ) -> List[SearchResult]:
        ...


# ---------------------------------------------------------------------------
# Concrete: TierRecencyReranker
# ---------------------------------------------------------------------------

# Tier boosts: higher tiers get a relevance bonus
TIER_BOOST = {
    "L4": 1.20,   # wiki: certified knowledge
    "L3": 1.10,   # papers/readwise: externally certified
    "L2": 1.00,   # working notes: baseline
    "L1": 0.70,   # raw capture/cache: low signal
}

# Recency half-life in days, by tier. None = no decay (knowledge is durable).
TIER_HALF_LIFE = {
    "L4": None,    # wiki entries don't stale
    "L3": None,    # papers don't stale
    "L2": 90,      # working notes: 90-day half-life
    "L1": 30,      # raw capture: 30-day half-life
}


class TierRecencyReranker:
    """
    Reranks search results by combining cosine similarity with:
    1. Tier boost (L4 > L3 > L2 > L1)
    2. Recency decay (exponential half-life, L2/L1 only)
    3. TrustRank score (wiki entries, loaded lazily from trust.py)

    Final score = cosine * tier_boost * recency_factor + trust_bonus
    """

    def __init__(self, trust_scores: Optional[Dict[str, float]] = None) -> None:
        self._trust_scores = trust_scores or {}

    @staticmethod
    def _recency_factor(mtime: float, tier: str) -> float:
        """Exponential decay based on tier-specific half-life."""
        import time as _time
        import math

        half_life = TIER_HALF_LIFE.get(tier)
        if half_life is None:
            return 1.0

        age_days = (_time.time() - mtime) / 86400
        if age_days <= 0:
            return 1.0

        return math.pow(0.5, age_days / half_life)

    def rerank(
        self,
        query: str,
        candidates: List[SearchResult],
        top_k: int = 10,
    ) -> List[SearchResult]:
        scored = []
        for r in candidates:
            tier = r.tier or "L2"
            boost = TIER_BOOST.get(tier, 1.0)
            recency = self._recency_factor(r.mtime, tier)
            trust_bonus = self._trust_scores.get(r.path, 0.0) * 0.1  # scale trust to ~0-0.1
            final = r.score * boost * recency + trust_bonus
            scored.append((final, r))

        scored.sort(key=lambda x: -x[0])
        results = []
        for final_score, r in scored[:top_k]:
            results.append(SearchResult(
                path=r.path,
                score=round(final_score, 4),
                chunk_id=r.chunk_id,
                chunk_text=r.chunk_text,
                tier=r.tier,
            ))
        return results


# ---------------------------------------------------------------------------
# Retriever: orchestrates the pipeline
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,4})\s", re.MULTILINE)
CHUNK_TARGET = 2000   # chars; BGE-M3 handles up to ~8K tokens but shorter chunks retrieve better
CHUNK_MAX = 4000      # hard cap; chunks above this are split on paragraph boundaries
CHUNK_MIN = 200       # don't create tiny fragments


def _split_long(text: str, limit: int) -> List[str]:
    """Split text that exceeds limit on double-newline (paragraph) boundaries.
    Falls back to single-newline, then hard truncation."""
    # Try double-newline first
    paragraphs = re.split(r"\n\n+", text)
    if len(paragraphs) == 1:
        # No double newlines; try single newlines
        paragraphs = text.split("\n")

    chunks: List[str] = []
    buf = ""
    for para in paragraphs:
        if buf and len(buf) + len(para) + 2 > limit:
            chunks.append(buf)
            buf = para
        else:
            buf = buf + "\n\n" + para if buf else para
    if buf:
        chunks.append(buf)

    # Hard truncation: split any still-oversized chunks by character
    final: List[str] = []
    for chunk in (chunks or [text]):
        while len(chunk) > limit:
            final.append(chunk[:limit])
            chunk = chunk[limit:]
        if chunk:
            final.append(chunk)
    return final


def chunk_markdown(text: str) -> List[str]:
    """
    Split markdown into chunks on heading boundaries.

    Strategy: split at ## / ### / #### headings, then merge small sections
    until each chunk is near CHUNK_TARGET chars. Chunks that still exceed
    CHUNK_MAX are further split on paragraph boundaries. Files under
    CHUNK_TARGET are returned as a single chunk.
    """
    if len(text) <= CHUNK_TARGET:
        return [text]

    # Split at headings, keeping the heading with its section
    splits: List[str] = []
    last = 0
    for m in _HEADING_RE.finditer(text):
        if m.start() > last:
            splits.append(text[last:m.start()])
        last = m.start()
    if last < len(text):
        splits.append(text[last:])

    # Merge small consecutive sections to approach CHUNK_TARGET
    merged: List[str] = []
    buf = ""
    for section in splits:
        if buf and len(buf) + len(section) > CHUNK_TARGET:
            merged.append(buf)
            buf = section
        else:
            buf += section
    if buf:
        if merged and len(buf) < CHUNK_MIN:
            merged[-1] += buf
        else:
            merged.append(buf)

    # Hard-cap: split any oversized chunks on paragraph boundaries
    chunks: List[str] = []
    for chunk in merged:
        if len(chunk) > CHUNK_MAX:
            chunks.extend(_split_long(chunk, CHUNK_MAX))
        else:
            chunks.append(chunk)

    return chunks


# ---------------------------------------------------------------------------
# Tier derivation
# ---------------------------------------------------------------------------

def _derive_tier(path: str) -> str:
    """Derive knowledge tier from path prefix."""
    parts = path.split("/")
    if len(parts) < 2:
        return "L2"
    subdir = parts[1] if parts[0] == "zk" else parts[0]
    tier_map = {
        "wiki": "L4",
        "papers": "L3",
        "readwise": "L1",
        "daily-notes": "L2",
        "reflections": "L2",
        "research": "L2",
        "preprints": "L2",
        "agent-findings": "L2",
        "drafts": "L2",
        "gtd": "L2",
        "health": "L2",
        "cache": "L1",
        "archive": "L2",
        "sessions": "L2",
    }
    return tier_map.get(subdir, "L2")


class Retriever:
    """
    Orchestrates Embedder + Store + optional Reranker.

    This is the single entry point that semantic.py calls. The retriever
    does NOT know which embedder, store, or reranker it's using. It just
    calls their Protocol methods.
    """

    def __init__(
        self,
        embedder: Embedder,
        store: Store,
        reranker: Optional[Reranker] = None,
    ) -> None:
        self.embedder = embedder
        self.store = store
        self.reranker = reranker

    def index_files(
        self,
        files: Sequence[Path],
        repo_root: Path,
        batch_size: int = 64,
        show_progress: bool = True,
        append_only: bool = False,
    ) -> int:
        """
        Chunk, embed, and index a sequence of markdown files.
        Returns total chunks indexed.

        append_only=True uses fast add() instead of merge_insert upsert.
        Use after clear() for full rebuilds.
        """
        import sys

        write_fn = self.store.add if append_only else self.store.upsert
        total = 0
        batch_docs: List[Document] = []
        batch_texts: List[str] = []
        file_list = list(files)
        n_files = len(file_list)

        for i, fpath in enumerate(file_list):
            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            if not text.strip():
                continue

            try:
                rel = str(fpath.relative_to(repo_root))
            except ValueError:
                rel = str(fpath)

            tier = _derive_tier(rel)
            mtime = fpath.stat().st_mtime
            chunks = chunk_markdown(text)

            for ci, chunk_text in enumerate(chunks):
                doc = Document(
                    id=f"{rel}:{ci}",
                    path=rel,
                    chunk_id=ci,
                    chunk_text=chunk_text,
                    tier=tier,
                    mtime=mtime,
                )
                batch_docs.append(doc)
                batch_texts.append(chunk_text)

            if len(batch_docs) >= batch_size:
                vectors = self.embedder.encode(batch_texts)
                total += write_fn(batch_docs, vectors)
                if show_progress:
                    print(
                        f"\r  [{i + 1}/{n_files}] indexed {total} chunks",
                        end="",
                        file=sys.stderr,
                        flush=True,
                    )
                batch_docs.clear()
                batch_texts.clear()

        # flush remaining
        if batch_docs:
            vectors = self.embedder.encode(batch_texts)
            total += write_fn(batch_docs, vectors)

        if show_progress:
            print(
                f"\r  [{n_files}/{n_files}] indexed {total} chunks",
                file=sys.stderr,
            )

        return total

    def index_incremental(
        self,
        files: Sequence[Path],
        repo_root: Path,
        batch_size: int = 64,
        show_progress: bool = True,
    ) -> tuple[int, int, int]:
        """
        Incremental index: only process files whose mtime changed.
        Removes stale entries for deleted files.
        Returns (added, skipped, removed).
        """
        import sys

        indexed = self.store.get_indexed_mtimes()
        file_list = list(files)

        # Determine which files need re-indexing
        current_paths = set()
        to_index: List[Path] = []
        for fpath in file_list:
            try:
                rel = str(fpath.relative_to(repo_root))
            except ValueError:
                rel = str(fpath)
            current_paths.add(rel)
            current_mtime = fpath.stat().st_mtime
            indexed_mtime = indexed.get(rel, 0.0)
            # Epsilon of 1s avoids false positives from Drive sync touching mtimes
            if current_mtime - indexed_mtime > 1.0:
                to_index.append(fpath)

        # Remove entries for deleted files
        stale = [p for p in indexed if p not in current_paths]
        removed = 0
        if stale:
            removed = self.store.delete_by_path(stale)
            if show_progress:
                print(f"  removed {removed} stale entries", file=sys.stderr)

        skipped = len(file_list) - len(to_index)
        if not to_index:
            if show_progress:
                print(f"  index is up to date ({skipped} files unchanged)", file=sys.stderr)
            return 0, skipped, removed

        if show_progress:
            print(
                f"  {len(to_index)} files changed, {skipped} unchanged",
                file=sys.stderr,
            )

        added = self.index_files(to_index, repo_root, batch_size, show_progress)
        return added, skipped, removed

    def query(
        self,
        text: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Embed query, search store, optionally rerank."""
        vector = self.embedder.encode([text])[0]
        results = self.store.search(vector, top_k=top_k * 3 if self.reranker else top_k, filters=filters)

        if self.reranker:
            results = self.reranker.rerank(text, results, top_k=top_k)

        return results[:top_k]

    def stats(self) -> IndexStats:
        return self.store.stats()


# ---------------------------------------------------------------------------
# Concrete: BGE-M3 Embedder
# ---------------------------------------------------------------------------

class BGEM3Embedder:
    """
    Embedder backed by BAAI/bge-m3 via sentence-transformers.

    BGE-M3 is multilingual (100+ languages including Chinese and English),
    produces 1024-dim dense vectors, and supports up to 8192 tokens.

    Device-dependent parameters (max_tokens, encode_batch_size, device)
    are loaded from semantic.toml. See scripts/config.py for defaults.
    """

    MODEL_ID = "BAAI/bge-m3"
    DIMENSION = 1024

    def __init__(self, device: Optional[str] = None, max_tokens: Optional[int] = None, batch_size: Optional[int] = None) -> None:
        from sentence_transformers import SentenceTransformer
        from config import load, resolve_device

        cfg = load()
        resolved_device = device or resolve_device(cfg["device"])
        self._max_tokens = max_tokens or cfg["max_tokens"]
        self._batch_size = batch_size or cfg["encode_batch_size"]
        self._device = resolved_device
        self._model = SentenceTransformer(self.MODEL_ID, device=resolved_device)
        self._model.max_seq_length = self._max_tokens

    def encode(self, texts: List[str]) -> NDArray[np.float32]:
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=self._batch_size,
        )
        return np.asarray(embeddings, dtype=np.float32)

    def dimension(self) -> int:
        return self.DIMENSION

    def model_name(self) -> str:
        return self.MODEL_ID


# ---------------------------------------------------------------------------
# Concrete: LanceDB Store
# ---------------------------------------------------------------------------

class LanceStore:
    """
    Store backed by LanceDB (embedded, Lance columnar format).

    Index lives at a directory path (e.g., zk/.semantic/lance/).
    No server process. Files on disk.
    """

    TABLE_NAME = "semantic_index"

    def __init__(self, db_path: str, embedding_dim: int, model_name: str = "") -> None:
        import lancedb

        self._db_path = db_path
        self._embedding_dim = embedding_dim
        self._model_name = model_name
        self._db = lancedb.connect(db_path)

        # Ensure table exists
        self._table = self._ensure_table()

    def _ensure_table(self) -> Any:
        """Create table if it doesn't exist, or open it."""
        import pyarrow as pa

        existing = self._db.table_names()
        if self.TABLE_NAME in existing:
            return self._db.open_table(self.TABLE_NAME)

        schema = pa.schema([
            pa.field("id", pa.utf8()),
            pa.field("path", pa.utf8()),
            pa.field("chunk_id", pa.int32()),
            pa.field("chunk_text", pa.utf8()),
            pa.field("tier", pa.utf8()),
            pa.field("mtime", pa.float64()),
            pa.field("vector", pa.list_(pa.float32(), self._embedding_dim)),
        ])
        return self._db.create_table(self.TABLE_NAME, schema=schema)

    def _to_rows(self, docs: List[Document], vectors: NDArray[np.float32]) -> List[Dict[str, Any]]:
        return [
            {
                "id": doc.id,
                "path": doc.path,
                "chunk_id": doc.chunk_id,
                "chunk_text": doc.chunk_text,
                "tier": doc.tier,
                "mtime": doc.mtime,
                "vector": vec.tolist(),
            }
            for doc, vec in zip(docs, vectors)
        ]

    def add(self, docs: List[Document], vectors: NDArray[np.float32]) -> int:
        """Append-only insert (fast path for initial builds)."""
        if not docs:
            return 0
        self._table.add(self._to_rows(docs, vectors))
        return len(docs)

    def upsert(self, docs: List[Document], vectors: NDArray[np.float32]) -> int:
        """Insert or update documents using LanceDB's native merge_insert."""
        if not docs:
            return 0
        (
            self._table
            .merge_insert("id")
            .when_matched_update_all()
            .when_not_matched_insert_all()
            .execute(self._to_rows(docs, vectors))
        )
        return len(docs)

    def search(
        self,
        vector: NDArray[np.float32],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        query = self._table.search(vector.tolist()).metric("cosine").limit(top_k)

        # Build filter string for LanceDB
        where_clauses = []
        if filters:
            if "path_prefix" in filters:
                prefix = filters["path_prefix"]
                if isinstance(prefix, list):
                    parts = [f'path LIKE "{p}%"' for p in prefix]
                    where_clauses.append(f"({' OR '.join(parts)})")
                else:
                    where_clauses.append(f'path LIKE "{prefix}%"')
            if "tier" in filters:
                where_clauses.append(f'tier = "{filters["tier"]}"')
            if "mtime_after" in filters:
                where_clauses.append(f"mtime >= {filters['mtime_after']}")
            if "mtime_before" in filters:
                where_clauses.append(f"mtime <= {filters['mtime_before']}")

        if where_clauses:
            query = query.where(" AND ".join(where_clauses))

        try:
            results_df = query.to_pandas()
        except Exception:
            return []

        results = []
        for _, row in results_df.iterrows():
            # cosine _distance: 0.0 = identical, 1.0 = orthogonal
            distance = row.get("_distance", 0.0)
            score = max(0.0, 1.0 - distance)
            results.append(SearchResult(
                path=row["path"],
                score=round(score, 4),
                chunk_id=int(row.get("chunk_id", 0)),
                chunk_text=row.get("chunk_text", ""),
                tier=row.get("tier", ""),
                mtime=float(row.get("mtime", 0.0)),
            ))

        return results

    def delete(self, ids: List[str]) -> int:
        if not ids:
            return 0
        id_filter = " OR ".join(f'id = "{doc_id}"' for doc_id in ids)
        try:
            self._table.delete(id_filter)
            return len(ids)
        except Exception:
            return 0

    def get_indexed_mtimes(self) -> Dict[str, float]:
        """Return {path: max_mtime} for all indexed documents."""
        try:
            df = self._table.to_pandas(columns=["path", "mtime"])
            return dict(df.groupby("path")["mtime"].max())
        except Exception:
            return {}

    def delete_by_path(self, paths: List[str]) -> int:
        """Delete all chunks for the given file paths."""
        if not paths:
            return 0
        path_filter = " OR ".join(f'path = "{p}"' for p in paths)
        try:
            self._table.delete(path_filter)
            return len(paths)
        except Exception:
            return 0

    def count(self) -> int:
        try:
            return self._table.count_rows()
        except Exception:
            return 0

    def stats(self) -> IndexStats:
        return IndexStats(
            total_documents=self.count(),
            total_chunks=self.count(),
            embedding_dimension=self._embedding_dim,
            model_name=self._model_name,
            index_path=self._db_path,
        )

    def clear(self) -> None:
        """Drop and recreate the table."""
        try:
            self._db.drop_table(self.TABLE_NAME)
        except Exception:
            pass
        self._table = self._ensure_table()
