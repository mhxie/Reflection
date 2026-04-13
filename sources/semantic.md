# Local Semantic Search (`scripts/semantic.py`)

Teaching doc for the `semantic.py` CLI. Agents and command files call this script to find notes by meaning rather than exact string match.

**This doc describes the contract, not the implementation.** The backend swaps across three stages (stub, BGE-M3, corpus-tuned local model) without changing anything below.

## Modes

**Stub mode** (lexical fallback): active when `~/.cache/reflectl/lance/` does not exist. Uses lexical token matching (substring `count`) over the Markdown corpus under `zk/`. Prints a warning to stderr on every invocation so callers never mistake "empty result" for "no conceptual neighbor exists."

**Real mode** (embedding-backed): active when `~/.cache/reflectl/lance/` exists (sentinel). Day-one stack: BGE-M3 (1024-dim, multilingual, 8K-token context) + LanceDB (embedded columnar store, cosine distance). Documents are chunked at markdown heading boundaries (~2K chars per chunk). Index is machine-local; rebuild with `uv run scripts/semantic.py index` on each machine (~7s on MPS). No caller code changes across the swap.

## CLI

```
scripts/semantic.py query "<text>" [OPTIONS]
scripts/semantic.py index [--rebuild]
scripts/semantic.py --help
```

### `query` options

| Flag | Meaning | Default |
|---|---|---|
| `--path DIR` | Restrict to a subdirectory (repeatable). | `zk/` |
| `--after YYYY-MM-DD` | Files with mtime >= date. | none |
| `--before YYYY-MM-DD` | Files with mtime <= date. | none |
| `--top N` | Max results. | 10 |
| `--lang {zh,en,auto}` | Query language hint. No-op in stub mode. | `auto` |
| `--format {tsv,json}` | Output format. | `tsv` |

### Output

TSV (default): one result per line.

```
<path>\t<score>\t<matched_tokens>
```

- `path` is relative to the repo root.
- `score` is in `[0.0, 1.0]`. Higher is better. Stable sort direction across stub and real modes.
  - **Stub:** `min(total_token_hits, 10) / 10`.
  - **Real:** cosine similarity between query embedding and file embedding.
- `matched_tokens` is a comma-separated list (stub) or always present in real mode.

JSON (`--format json`): a list of objects with `path`, `score`, `matched_tokens`.

### Exit codes

- `0` — success (including zero results).
- `2` — usage error (bad flag, unparseable date).

### Streams

- **stdout:** results only. Parseable by `xargs`, `awk`, etc.
- **stderr:** mode banner, warnings, diagnostics. Always emitted; callers should not silence stderr.

## When to call this script

| Situation | Call |
|---|---|
| Searching for a specific keyword or title | Use `Grep`, not this script. |
| Searching for a concept that might be phrased many ways | `semantic.py query "<concept>"` |
| `/explore` — surfacing forgotten connections | `semantic.py query` with a broad concept from today's context |
| `/introspect` — finding curiosity vectors that aren't named as goals | `semantic.py query` after lexical grep passes |
| `/reflect` forgotten-connection step | `semantic.py query` with a concept from the current conversation |
| `/energy-audit` — searching for affective states | `semantic.py query "tired exhausted drained"` |
| `/decision` — adjacent prior thinking | `semantic.py query` alongside lexical grep |

## Stub-mode caveats

- **Lexical-only.** Queries that require understanding paraphrase, synonymy, or conceptual adjacency will underperform. A query for "what am I avoiding?" returns nothing useful in stub mode.
- **Case-insensitive.** Matching is lowercased.
- **CJK-tolerant.** Chinese characters are preserved through tokenization, so queries like `"目标 精力"` work for exact-phrase matches but not conceptual ones.
- **No ranking beyond token frequency.** A daily note that mentions the query word five times in passing will outrank a wiki entry that discusses the concept in depth using different words. Real mode fixes this.

To exit stub mode, run `uv run python scripts/semantic.py index` to build the lance index.

## Examples

Basic query:
```
scripts/semantic.py query "curiosity vectors"
```

Restricted to reflections in the last 30 days, JSON output:
```
scripts/semantic.py query "energy drain" \
    --path zk/reflections \
    --after 2026-03-07 \
    --format json
```

Multiple paths, top 20 hits:
```
scripts/semantic.py query "研究 方向" \
    --path zk/daily-notes \
    --path zk/reflections \
    --top 20
```

Piping into `Read` (for an agent workflow):
```
scripts/semantic.py query "contradiction" --top 5 | \
    cut -f1 | \
    while read path; do echo "--- $path ---"; cat "$path"; done
```

## Design principles (frozen)

1. **Contract-first.** The CLI flags and output schema will not change when the backend swaps.
2. **Transparent degradation.** Stub mode always warns on stderr. Callers treat the stream as authoritative.
3. **Unix-composable.** stdout for data, stderr for meta, exit codes for control flow.
4. **Sentinel mode detection.** `~/.cache/reflectl/lance/` present → real mode. Absent → stub. Nothing else.
5. **Encoder-agnostic interface.** BGE, local model encoder, or any future backend all produce `(path, score)` pairs with the same semantics.
6. **Stdlib-only in stub mode.** No dependencies shipped with the interface commit. Real mode deps managed via `pyproject.toml` + `uv`.

## Setup

```bash
uv sync                                    # install deps (venv at ~/.cache/reflectl/.venv)
uv run python scripts/semantic.py index    # build index (~4K files, takes a few minutes)
uv run python scripts/semantic.py query "curiosity vectors"  # search
```

## References

- Backend implementations: `scripts/semantic_backends.py`
- Local-first architecture: `protocols/local-first-architecture.md`
- Sibling teaching docs: `sources/scholar.md`, `sources/local-papers.md`, `sources/readwise.md`
