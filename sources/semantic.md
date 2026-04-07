# Local Semantic Search (`scripts/semantic.py`)

Teaching doc for the `semantic.py` CLI. Agents and command files call this script to find notes by meaning rather than exact string match.

**This doc describes the contract, not the implementation.** The backend swaps across three stages (stub, BGE-M3, corpus-tuned local model) without changing anything below.

## Current mode: STUB

Today, `semantic.py` runs in **stub mode**: it uses lexical token matching (substring `count`) over the Markdown corpus under `zk/`. Stub mode will:

- Return results when the query shares literal tokens with a file.
- Return nothing when the concept uses different words (that is the whole point of semantic search, and the whole limitation of the stub).
- Print a warning to stderr on every invocation so callers never mistake "empty result" for "no conceptual neighbor exists."

Real mode activates when `zk/.semantic/index.sqlite` exists (sentinel). No caller code changes across the swap.

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

When stub limitations hurt a specific session, the documented escape hatch is Reflect's vector search (`mcp__reflect__search_notes` with `searchType: "vector"`). Use it sparingly and note the fallback in the session record. The escape hatch goes away when real mode ships.

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
4. **Sentinel mode detection.** `zk/.semantic/index.sqlite` present → real mode. Absent → stub. Nothing else.
5. **Encoder-agnostic interface.** BGE, local model encoder, or any future backend all produce `(path, score)` pairs with the same semantics.
6. **Stdlib-only in stub mode.** No dependencies shipped with the interface commit. Real mode adds `sentence-transformers` and `sqlite-vec` in its own commit.

## References

- Design decision record: `handoffs/2026-04-06-phase-bcd-trust-engine.md` (Addendum: Phase B.5)
- Local-first architecture: `protocols/local-first-architecture.md`
- Sibling teaching docs: `sources/scholar.md`, `sources/local-papers.md`, `sources/readwise.md`
