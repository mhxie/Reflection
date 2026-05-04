# scripts/

Executable tooling for the Atelier knowledge layer. All scripts are stdlib-only (or stdlib + one documented dependency), deterministic, and runnable from the repo root with project-relative paths.

## Inventory

| Script | Purpose | Phase | Deps |
|---|---|---|---|
| `semantic.py` | Local semantic search over `$OV/` — BGE-M3 embeddings + LanceDB with tier-aware reranking; lexical fallback when index is absent | B.5 | `lancedb`, `sentence-transformers` (optional; falls back to lexical) |
| `semantic_backends.py` | Backend implementations for semantic.py (LanceDB embedding backend, lexical fallback) | B.5 | `lancedb`, `sentence-transformers` (optional) |
| `trust.py` | TrustRank for `$OV/wiki/` — Personalized PageRank with external anchor seeds, claim-level granularity, bi-temporal filtering, floor trust | B | stdlib |
| `lint.py` | Structural + corpus-level lint over `$OV/wiki/` — parse errors, duplicate titles, slug drift, orphan entries, graph topology | D | stdlib |
| `harness_lint.py` | Claude Code and Codex portability lint — root instructions, model profiles, capability mappings, command and agent registries | ops | stdlib |
| `harness_smoke.py` | Smoke test for the portable harness helper and lint JSON surfaces | ops | stdlib |
| `atelier.py` | Portable command/agent discovery and Codex prompt generation from `harness/*.toml` | ops | stdlib |
| `privacy_check.py` | Scans tracked files for private-vault filename-stem leaks; opt-outs live in `privacy_allowlist.txt`; wired into `/lint` Phase 0c | ops | stdlib |
| `zk_audit.py` | Post-ingestion hygiene audit for `$OV/`: missing READMEs, raw-without-digest, archive↔working overlap, root orphans, suspicious dirs; wired into `/lint` Phase 0b | ops | stdlib |
| `staleness.py` | L2 staleness scoring — surfaces dormant, stale, and promotion-candidate notes | D | stdlib |
| `todos.py` | Aggregate open TODOs from `$OV/gtd/` and reflection Next Action sections; computes priority from `due:` / `priority:` / age; flags closure candidates from daily-note language; powers `/reflect` Step 0 digest | ops | stdlib |
| `session_log.py` | Session event log skeleton generator — handles late-sleep date rule and collision auto-increment | E | stdlib |
| `review.sh` | External reviewer wrapper (codex + gemini in parallel) for system-evolution diffs | ops | `codex`, `gemini` CLIs |
| `chat_completion.py` | Stdlib-only OpenAI-compatible chat completion invoker. Stateless (one-shot) by default; `--session FILE` for multi-turn (history replayed each call). Reads provider config from a profile (schema in `harness/models.toml`, bindings in gitignored `profile/models.toml`) or direct flags. Backs the cross_validation and external_review tiers; switching providers is a binding edit, not a script change. Every call (success and error) logs one JSONL line to `~/.cache/atelier/llm_calls/<date>.jsonl` for after-the-fact quality / latency / reasoning audit; pass `--no-log` to skip on sensitive prompts | ops | stdlib |
| `shadow.sh` | Fires a sampled, backgrounded shadow `chat_completion.py` call for the `core_intelligence` tier. Sample rate via `$ATELIER_SHADOW_RATE` (default 10%). Returns immediately; the shadow leg is logged for quality comparison without blocking the primary path | ops | stdlib |
| `pricing.py` | Provider pricing catalog reader + cost calculator. Reads `scripts/pricing.toml` (flagship + standard per provider, USD per 1M tokens). Subcommands: `list` (sorted blended-cost table), `blended <provider> <class>`, `cost <provider> <class> --input N --output N`, `cost-from-log` (retrospective cost from `~/.cache/atelier/llm_calls/`). Used to drive future Pareto-optimal model selection (perf/cost) | ops | stdlib |

## Portable Harness

`scripts/atelier.py status` summarizes the Claude/Codex registry state.
Use `commands`, `agents`, `prompt`, and `agent-prompt` subcommands to discover
portable workflows without scraping `harness/*.toml` directly.
Run `scripts/harness_smoke.py` after harness edits to verify the helper and JSON
surfaces end to end without touching `$OV/`.

## `trust.py` — quick reference

Walks `$OV/wiki/*.md`, parses each wiki entry into claims and markers, builds a directed trust graph, runs Personalized PageRank, applies the claim-level floor trust of 0.1, and reports per-claim and per-note scores.

```
scripts/trust.py                                   # default table over $OV/wiki/
scripts/trust.py --note "$OV"/wiki/<file>.md       # per-claim breakdown
scripts/trust.py --as-of 2025-06-01                # bi-temporal snapshot
scripts/trust.py --json                            # structured output for /lint
```

**Model.** External `@anchor` markers are the only seeds of trust. `@cite` edges propagate trust from cited claims to citing claims. `@pass` markers never accumulate trust; a reviewer-verified pass only enables the claim-level floor of 0.1 on a structurally-valid note.

**Determinism.** Pure Python, stdlib-only. PageRank is a direct power-iteration implementation matching `networkx.pagerank(G, personalization=anchor_dict)` semantics (dangling mass redistributes to the personalization vector, damping 0.85, tolerance 1e-9, max 200 iterations). Zero new dependencies.

**Bi-temporal.** Every marker has `valid_at` (required); optional `invalid_at`. `--as-of` filters markers by the active window. With no active anchors in the snapshot, all claim scores are 0 by design: TrustRank with an empty seed set means no trust has entered the graph.

**Structural integrity.** `trust.py` enforces items 1 to 10 of `protocols/wiki-schema.md` § Structural Integrity Check. A note that fails parse contributes no seeds and no propagation edges, but its claims still appear in the report with score 0 and a `fail` status. Full lint (items 11 to 15) lands with `/lint` in Phase D.

**Exit codes.** `0` on success. `2` on usage error (missing file, invalid date, note outside `$OV/wiki/`).

See `protocols/wiki-schema.md` for the schema and `handoffs/2026-04-06-phase-bcd-trust-engine.md` for the Phase B spec and rationale.
