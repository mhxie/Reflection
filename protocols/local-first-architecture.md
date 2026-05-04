# Local-First Architecture

The user's knowledge layer is plain-text Markdown files under `$OV/`. `$OV` is an environment variable that each user sets to their own vault root. The system reads and writes these files directly; there is no remote note-store mirror.

This is the prerequisite for everything in `wiki-schema.md` and `epistemic-hygiene.md`. Trust propagation, claim-level granularity, bi-temporal anchors, and structural-integrity linting all require deterministic Python access to plain-text files, which this layout provides.

## The Layers

The model has **five layers (L1–L5), numbered by depth of crystallization.** Higher number = higher trust. The axis is not provenance (human vs AI) but storage/certification depth: how much structural work, anchoring, and peer verification a note has accumulated by virtue of where it lives.

(Note: "Layer" here refers to the L1–L5 knowledge-storage axis. A separate orthogonal axis — the **validation-depth taxonomy** in `epistemic-hygiene.md` — uses the names *alloy* / *wiki entry* / `#solo-flight` for what a note *is*. Do not conflate the two: L1–L5 is *where*, alloy/wiki/solo-flight is *what*.)

```
    L5 — Foundation                   (reserved — textbook-level, universally certified)
    ────────────────────────────
    L4 — Locally certified            $OV/wiki/
          authoritative knowledge     anchored, schema-validated, TrustRank-scored
    ────────────────────────────
    L3 — Externally certified         $OV/papers/ + Readwise (curated)
          peer-reviewed or high-citation receipts
    ────────────────────────────
    L2 — Working / half-baked         $OV/daily-notes/, $OV/reflections/,
          alloy by default            $OV/research/, $OV/preprints/,
                                      $OV/agent-findings/, $OV/drafts/, $OV/gtd/
    ────────────────────────────
    L1 — Raw capture                  Readwise inbox,
          fast, sloppy, ephemeral     $OV/cache/, $OV/readwise/ inbox
```

Promotion is **opportunistic and upward:** L1 capture crystallizes into an L2 draft or reflection; a recurring L2 thought earns an L4 wiki entry once it has anchors and claims; L3 receipts flow in from scout fetches and Readwise curation. There is no demotion workflow — invalidation is additive (bi-temporal markers in wiki entries), not destructive.

### L1 — Raw capture

The fast, sloppy, ephemeral layer. Readwise's inbox holds external content (articles, podcasts, papers); `$OV/cache/` holds web fetches and other transient artifacts. No guarantees about structure or durability. Promotion upward is opportunistic.

### L2 — Working / half-baked

The alloy layer. Most of the user's active thinking lives here: daily free-writes (`$OV/daily-notes/`), session reflections (`$OV/reflections/`), user-initiated research reports (`$OV/research/`), arxiv preprints and paper reviews (`$OV/preprints/`), promoted agent synthesis briefs (`$OV/agent-findings/`), working drafts (`$OV/drafts/`), and active planning (`$OV/gtd/`). Alloy by default — see `epistemic-hygiene.md`. Fully searchable, citable, but not certified. The substrate from which wiki entries are distilled.

Older topic directories (career, research, people, etc.) carried over from earlier knowledge systems are parked in `$OV/archive/` and stay there until individual notes are surfaced upward.

### L3 — Externally certified

Peer-reviewed papers, high-citation work, and curated reading corpus. Lives in `$OV/papers/` (local PDFs and reading artifacts) plus the Readwise-curated side of `$OV/readwise/`. The canonical id for papers is `s2:` / `arxiv:` / `doi:`; for articles, `url:` or a Readwise document id. L3 receipts are the anchor points for L4 wiki claims — an `@anchor` marker in a wiki entry points at an L3 receipt.

The teaching doc that explains how agents query the papers directory lives at `sources/local-papers.md` (an execution-layer doc in the atelier repo).

### L4 — Locally certified (wiki)

The slow, structured, authoritative layer. Lives in plain Markdown files under `$OV/wiki/`. Each file follows `wiki-schema.md`. Each file is parseable by `scripts/trust.py` and produces a per-note trust score. Cross-references between wiki entries are `@cite` markers, which become edges in the trust graph.

**Directory is the certification.** A note is a wiki entry by virtue of living under `$OV/wiki/`. There is no `#compiled-truth` or `#wiki` tag; the trust engine walks the directory and treats every file inside it as a wiki entry. The rest of `$OV/` stays alloy by default — the trust engine does not touch it. This gives the trust engine a single, fast directory traversal as its working set and avoids tag-collision with the user's existing tagging conventions.

L4 is the only tier where:

- Trust propagation runs.
- Bi-temporal anchors are tracked.
- Structural-integrity lint applies.

### L5 — Foundation (reserved)

Universally certified knowledge — textbook-level material that the user considers settled. No folder yet; the tier exists for future use when there is enough material to warrant one.

## Project Layout

Two roots:

- **System layer** — the `atelier/` repo (this directory). Orchestrator config, agents, protocols, scripts, source-handling teaching docs, and `sources/cite.py`. Version-controlled; no personal data.
- **Vault layer** — the user's note root, addressed as `$OV/`. A flat set of tier-labeled directories: `wiki/` (L4), `papers/` / `preprints/` (L3), `readwise/` (L1→L3 mirror), `daily-notes/` / `reflections/` / `research/` / `agent-findings/` / `drafts/` / `gtd/` / `travel/` / `health/` / `work/` / `immigration/` / `finance/` (L2), `cache/` (L1), and `archive/` (parked notes).

Vault paths use `$OV/` (e.g., `$OV/wiki/`, `$OV/papers/`); each user sets `$OV` to their note root (typical: `export OV="$HOME/notes"`). Repo-internal paths (`scripts/`, `protocols/`, `sources/cite.py`, `frameworks/`) stay project-relative and require no env var. The vault may live anywhere on disk (Google Drive, iCloud, a plain local folder); the system only needs `$OV` to point at it.

## Directory Layout (canonical)

```
atelier/                           (system root — the agent code)
├── CLAUDE.md                       # orchestrator instructions
├── .claude/agents/                 # team definitions
├── .claude/commands/               # slash commands
├── protocols/                      # system protocols (this directory)
├── frameworks/                     # thinking frameworks
├── profile/                        # gitignored config: self-model + private preferences (identity, directions, expertise, diet, reader_persona, credentials-index, private_slugs, examples, research-profile)
├── scripts/                        # Python tooling (trust.py, lint.py, semantic.py, ...)
└── sources/                        # source-handling teaching docs and helpers
    ├── cite.py                     # academic citation helper
    ├── readwise.md                 # Readwise CLI teaching doc
    ├── scholar.md                  # Semantic Scholar teaching doc
    └── local-papers.md             # local papers teaching doc

$OV/                                (vault root — set via env var)
├── wiki/                           # L4 — locally certified (authoritative)
│   ├── <topic-1>.md                # each file follows wiki-schema.md
│   └── <topic-2>.md
├── papers/                         # L3 — peer-reviewed / high-citation papers
├── preprints/                      # L3 — arxiv + paper reviews
├── readwise/                       # L1 inbox → L3 curated (Readwise mirror)
├── daily-notes/                    # L2 — daily free-writes (user-authored)
├── reflections/                    # L2 — session reflection files
├── research/                       # L2 — user-initiated research reports
├── agent-findings/                 # L2 — promoted scout briefs and agent synthesis
├── drafts/                         # L2 — working drafts
├── gtd/                            # L2 — active planning (year goals, trackers)
├── travel/, health/, work/         # L2 — domain-specific working notes
├── cache/                          # L1 — ephemeral raw web fetches and snapshots
└── archive/                        # parked notes (surfaced opportunistically)
```

The trust engine and the wiki schema only see the `$OV/wiki/` subtree. Everything else is alloy or receipts and the trust engine does not touch it.

## Source of Truth

`$OV/` is the only copy of the user's knowledge layer. There is no remote mirror, no two-way sync, no idempotency ledger. The filesystem may sync devices (Google Drive, iCloud, etc.); that is outside the system's concern.

Daily notes (under `$OV/daily-notes/`) are user-authored. By default the system reads them; it does not write to them. Curator dispatches that target a daily-note path are refused. **Exception (cloud-native capture):** when the user dictates raw daily-note content through chat, the Scribe agent (`daily_note` operation) records it verbatim. This is the only path by which the system writes to a daily note; the orchestrator does not transcribe directly.

All other tiers can be written by the orchestrator after user approval. The Curator drafts proposals; the orchestrator owns `Write` and `Edit` and applies them to a `target_path` under `$OV/`.

## Migration Strategy: Opportunistic, Not Big-Bang

There is no bulk migration of existing notes into the wiki layer. Older topic directories that are no longer active sit in `$OV/archive/`. The wiki layer grows organically:

- New wiki entries are written to `$OV/wiki/` directly (Curator drafts; orchestrator writes after approval).
- Existing notes (`$OV/archive/` or anywhere else in L1/L2) are surfaced to L4 **only when they are about to become anchors for a new wiki claim** — at that point the user (or Curator) extracts the relevant claims, structures them per the schema, writes the wiki entry, and the original note remains in place as an L1/L2 capture record (untouched).
- There is no goal to hoist the entire vault into the wiki layer. L1 and L2 remain the home for daily notes, session reflections, drafts, and most thinking. Most notes will never be in L4 — that is correct, not a failure.

The expected steady-state ratio is roughly: hundreds of L1/L2 notes for every L4 wiki entry. L4 is the slow, careful, anchored kernel. L1 and L2 are the fast surface.

## Per-Agent Contract

| Agent | L1/L2 working layer | L4 wiki (`$OV/wiki/`) | L3 receipts |
|---|---|---|---|
| **Researcher** | Local-only, semantic-primary. `Bash: uv run scripts/semantic.py query` for content queries; `Grep` + `Read` for structural queries. | Reads `$OV/wiki/` with grep directly. | Reads `$OV/readwise/`, `$OV/papers/` directly. |
| **Curator** | Drafts note proposals (compactions, merges, new notes, rewrites); the orchestrator writes after user approval (Curator has no `Write` tool). | Drafts wiki entries with `target_path: $OV/wiki/<slug>.md`. The orchestrator writes the file after approval, then runs `scripts/trust.py --note <path>` to verify structural integrity and report initial scores. | Unchanged. |
| **Synthesizer** | Reads capture-layer briefs from Researcher; produces drafts the orchestrator writes to `$OV/reflections/`. | Reads wiki trust scores when available to weight evidence. | Unchanged. |
| **Reviewer** | Continues to gate write-backs. Gates wiki writes as well. A `@pass: reviewer | status: verified` marker is added to a claim only after Reviewer signs off. | Unchanged. |
| **Scout** | Unchanged. | Unchanged. | Writes promoted briefs to `$OV/agent-findings/` (not the ephemeral `$OV/cache/`). |

## Cross-References

- Tag taxonomy and validation-depth principle: `epistemic-hygiene.md`
- Wiki entry format and trust propagation rule: `wiki-schema.md`
- Trust engine implementation (Phase B): `scripts/trust.py` (deferred)
- Lint integration (Phase D): `.claude/commands/lint.md` (deferred)
