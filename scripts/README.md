# scripts/

Executable tooling for the reflectl knowledge layer. All scripts are stdlib-only (or stdlib + one documented dependency), deterministic, and runnable from the repo root with project-relative paths. No `$ZK_HOME`, no `$RFL_HOME`.

## Inventory

| Script | Purpose | Phase | Deps |
|---|---|---|---|
| `semantic.py` | Local semantic search over `zk/` — BGE-M3 embeddings + LanceDB with tier-aware reranking; lexical fallback when index is absent | B.5 | `lancedb`, `sentence-transformers` (optional; falls back to lexical) |
| `semantic_backends.py` | Backend implementations for semantic.py (LanceDB embedding backend, lexical fallback) | B.5 | `lancedb`, `sentence-transformers` (optional) |
| `trust.py` | TrustRank for `zk/wiki/` — Personalized PageRank with external anchor seeds, claim-level granularity, bi-temporal filtering, floor trust | B | stdlib |
| `lint.py` | Structural + corpus-level lint over `zk/wiki/` and sync manifest — parse errors, duplicate titles, slug drift, orphan entries, graph topology | D | stdlib |
| `staleness.py` | L2 staleness scoring — surfaces dormant, stale, and promotion-candidate notes | D | stdlib |
| `session_log.py` | Session event log skeleton generator — handles late-sleep date rule and collision auto-increment | E | stdlib |
| `review.sh` | External reviewer wrapper (codex + gemini in parallel) for system-evolution diffs | ops | `codex`, `gemini` CLIs |

## `trust.py` — quick reference

Walks `zk/wiki/*.md`, parses each wiki entry into claims and markers, builds a directed trust graph, runs Personalized PageRank, applies the claim-level floor trust of 0.1, and reports per-claim and per-note scores.

```
scripts/trust.py                                   # default table over zk/wiki/
scripts/trust.py --note zk/wiki/<file>.md          # per-claim breakdown
scripts/trust.py --as-of 2025-06-01                # bi-temporal snapshot
scripts/trust.py --json                            # structured output for /lint
```

**Model.** External `@anchor` markers are the only seeds of trust. `@cite` edges propagate trust from cited claims to citing claims. `@pass` markers never accumulate trust; a reviewer-verified pass only enables the claim-level floor of 0.1 on a structurally-valid note.

**Determinism.** Pure Python, stdlib-only. PageRank is a direct power-iteration implementation matching `networkx.pagerank(G, personalization=anchor_dict)` semantics (dangling mass redistributes to the personalization vector, damping 0.85, tolerance 1e-9, max 200 iterations). Zero new dependencies.

**Bi-temporal.** Every marker has `valid_at` (required); optional `invalid_at`. `--as-of` filters markers by the active window. With no active anchors in the snapshot, all claim scores are 0 by design: TrustRank with an empty seed set means no trust has entered the graph.

**Structural integrity.** `trust.py` enforces items 1 to 10 of `protocols/wiki-schema.md` § Structural Integrity Check. A note that fails parse contributes no seeds and no propagation edges, but its claims still appear in the report with score 0 and a `fail` status. Full lint (items 11 to 15) lands with `/lint` in Phase D.

**Exit codes.** `0` on success. `2` on usage error (missing file, invalid date, note outside `zk/wiki/`).

See `protocols/wiki-schema.md` for the schema and `handoffs/2026-04-06-phase-bcd-trust-engine.md` for the Phase B spec and rationale.
