# Local-First Architecture

The shift: **Reflect is no longer the authoritative knowledge store.** It is demoted to a capture source, alongside Readwise and the local papers folder. The authoritative knowledge layer is local plain-text files under `zk/` — a real Obsidian vault the user already maintains, mounted into the repo as a subdirectory. Python tools operate on the local layer. Reflect receives a one-way display push from the local layer when the user wants to read or share the result on mobile.

This is the prerequisite for everything in `wiki-schema.md` and `epistemic-hygiene.md`. Trust propagation, claim-level granularity, bi-temporal anchors, and structural-integrity linting all require deterministic Python access to plain-text files. The Reflect MCP API does not support the operations the design needs (no edit, no delete, no in-place mutation, no path-level access). Working around those limits while pretending Reflect is authoritative was the friction that motivated the shift.

## The Layers

The model has **five layers (L1–L5), numbered by depth of crystallization.** Higher number = higher trust. The axis is not provenance (human vs AI) but storage/certification depth: how much structural work, anchoring, and peer verification a note has accumulated by virtue of where it lives.

(Note: "Layer" here refers to the L1–L5 knowledge-storage axis. A separate orthogonal axis — the **validation-depth taxonomy** in `epistemic-hygiene.md` — uses the names *alloy* / *wiki entry* / `#solo-flight` for what a note *is*. Do not conflate the two: L1–L5 is *where*, alloy/wiki/solo-flight is *what*.)

```
    L5 — Foundation                   (reserved — textbook-level, universally certified)
    ────────────────────────────
    L4 — Locally certified            zk/wiki/
          authoritative knowledge     anchored, schema-validated, TrustRank-scored
    ────────────────────────────
    L3 — Externally certified         zk/papers/ + Readwise (curated)
          peer-reviewed or high-citation receipts
    ────────────────────────────
    L2 — Working / half-baked         zk/daily-notes/, zk/reflections/,
          alloy by default            zk/research/, zk/preprints/,
                                      zk/agent-findings/, zk/drafts/, zk/gtd/
    ────────────────────────────
    L1 — Raw capture                  Reflect UI, Readwise inbox,
          fast, sloppy, ephemeral     zk/cache/, zk/readwise/ inbox
```

Promotion is **opportunistic and upward:** L1 capture crystallizes into an L2 draft or reflection; a recurring L2 thought earns an L4 wiki entry once it has anchors and claims; L3 receipts flow in from scout fetches and Readwise curation. There is no demotion workflow — invalidation is additive (bi-temporal markers in wiki entries), not destructive.

### L1 — Raw capture

The fast, sloppy, mobile-friendly layer. Reflect's strengths (voice transcription, daily notes, mobile capture, decent search) anchor one side of this layer; Readwise's inbox and `zk/cache/`'s ephemeral fetches anchor the other. No guarantees about structure or durability. Reflect is **demoted to one capture source among many** — equal to Readwise, not privileged.

Reflect's corpus is continuously mirrored to `zk/daily-notes/` (YYYY-MM-DD.md files) by the user's existing sync, so the **default read path for read-capable agents (Researcher, orchestrator, Reader, and any agent whose frontmatter includes `Grep` / `Read`) is `Grep` + `Read` over `zk/`, not the Reflect MCP.** MCP reads are the fallback for today's fresh capture (when the sync lags), for semantic-only queries, and for notes genuinely missing from the local mirror. MCP writes (`append_to_daily_note`, `create_note`) stay in use for the capture-layer write path until a local-first write tool replaces them.

### L2 — Working / half-baked

The alloy layer. Most of the user's active thinking lives here: daily free-writes (`zk/daily-notes/`, synced from Reflect), session reflections (`zk/reflections/`), user-initiated research reports (`zk/research/`), arxiv preprints and paper reviews (`zk/preprints/`), promoted agent synthesis briefs (`zk/agent-findings/`, formerly `research-briefs`), working drafts (`zk/drafts/`), and active planning (`zk/gtd/`). Alloy by default — see `epistemic-hygiene.md`. Fully searchable, citable, but not certified. The substrate from which wiki entries are distilled.

Pre-2026 topic directories (career, research, people, etc.) that were carried over from the user's Obsidian vault are parked in `zk/archive/` and stay there until individual notes are surfaced upward.

### L3 — Externally certified

Peer-reviewed papers, high-citation work, and curated reading corpus. Lives in `zk/papers/` (local PDFs and reading artifacts) plus the Readwise-curated side of `zk/readwise/`. The canonical id for papers is `s2:` / `arxiv:` / `doi:`; for articles, `url:` or a Readwise document id. L3 receipts are the anchor points for L4 wiki claims — an `@anchor` marker in a wiki entry points at an L3 receipt.

The teaching doc that explains how agents query the papers directory lives at `sources/local-papers.md` (an execution-layer doc in the reflectl repo).

### L4 — Locally certified (wiki)

The slow, structured, authoritative layer. Lives in plain Markdown files under `zk/wiki/`. Each file follows `wiki-schema.md`. Each file is parseable by `scripts/trust.py` and produces a per-note trust score. Cross-references between wiki entries are `@cite` markers, which become edges in the trust graph.

**Directory is the certification.** A note is a wiki entry by virtue of living under `zk/wiki/`. There is no `#compiled-truth` or `#wiki` tag; the trust engine walks the directory and treats every file inside it as a wiki entry. The rest of `zk/` stays alloy by default — the trust engine does not touch it. This gives the trust engine a single, fast directory traversal as its working set and avoids tag-collision with the user's existing tagging conventions.

L4 is the only tier where:

- Trust propagation runs.
- Bi-temporal anchors are tracked.
- Structural-integrity lint applies.

Wiki entries are **also displayed in Reflect**, but as a one-way push (see "Sync Direction" below). The Reflect copy is read-only-ish: it exists for mobile reading and visual continuity with daily notes, but the local file is the source of truth. Edits made in the Reflect UI are lost on the next sync.

### L5 — Foundation (reserved)

Universally certified knowledge — textbook-level material that the user considers settled. No folder yet; the tier exists for future use when there is enough material to warrant one.

## Project Layout

The repo has two layers under one root:

- **Execution layer** — everything in `reflectl/` *outside* `zk/`. Orchestrator config, agents, protocols, scripts, source-handling teaching docs, and `sources/cite.py`. Version-controlled, no personal data.
- **Data layer** — everything under `reflectl/zk/`. The user's Obsidian vault, holding a flat set of tier-labeled directories: `wiki/` (L4), `papers/` (L3), `readwise/` (L1→L3 mirror), `daily-notes/` / `reflections/` / `research/` / `preprints/` / `agent-findings/` / `drafts/` / `gtd/` (L2), `cache/` (L1), and `archive/` (parked pre-2026 topic notes). Gitignored.

All paths in protocols, agents, scripts, and wiki entries are **project-relative** (`zk/wiki/`, `zk/papers/`, `sources/cite.py`). There is no `$ZK_HOME` or `$RFL_HOME` reference inside the repo. The user's fish config may still export those variables for shell convenience, but nothing in this repo reads them.

Both `reflectl/` and the underlying Zettelkasten directory live under Google Drive, so the local files sync across devices automatically. This gives the wiki layer the same cross-device reach as Reflect without coupling to the Reflect API.

## Directory Layout (canonical)

```
reflectl/                           (the repo root — the only root)
├── CLAUDE.md                       # orchestrator instructions
├── .claude/agents/                 # team definitions
├── .claude/commands/               # slash commands
├── protocols/                      # this directory — the system protocols
├── frameworks/                     # thinking frameworks
├── profile/                        # self-model (identity, directions, expertise)
├── scripts/                        # Python tooling (trust.py — Phase B, lint.py — Phase D; directory not yet created)
├── sources/                        # execution layer for source handling (committed)
│   ├── cite.py                     # academic citation helper (already exists)
│   ├── readwise.md                 # CLI teaching doc
│   ├── scholar.md                  # Semantic Scholar teaching doc
│   └── local-papers.md             # local papers teaching doc
├── personal/                       # gitignored sensitive material
└── zk/                             # data layer (gitignored), flat by tier
    ├── .obsidian/                  # Obsidian vault config (read-only viewer)
    ├── wiki/                       # L4 — locally certified (authoritative)
    │   ├── <topic-1>.md            # each file follows wiki-schema.md
    │   └── <topic-2>.md
    ├── papers/                     # L3 — peer-reviewed / high-citation papers
    ├── readwise/                   # L1 inbox → L3 curated (Readwise mirror)
    ├── daily-notes/                # L2 — daily free-writes synced from Reflect
    ├── reflections/                # L2 — session reflection files
    ├── research/                   # L2 — user-initiated research reports
    ├── preprints/                  # L2 — arxiv + paper reviews
    ├── agent-findings/             # L2 — promoted scout briefs and agent synthesis
    ├── drafts/                     # L2 — working drafts
    ├── gtd/                        # L2 — active planning (year goals, trackers)
    ├── cache/                      # L1 — ephemeral raw web fetches and snapshots
    └── archive/                    # parked pre-2026 topic notes (surfaced opportunistically)
```

The trust engine and the wiki schema only see the `zk/wiki/` subtree. Everything else is alloy or receipts and the trust engine does not touch it. The whole `zk/` directory is opened as an Obsidian vault for visual browsing of the entire knowledge base; the editing flow for wiki entries goes through reflectl agents (Curator), not Obsidian directly. Obsidian is the read-only viewer for wiki entries, not their writer.

## Sync Direction (Local → Reflect Display)

The sync is **one-way, local-to-Reflect, idempotent, and display-only.** Direction matters; pretending it could be bidirectional is what creates the corruption risk.

The flow:

1. Curator (Phase C) writes a wiki entry to `zk/wiki/<title>.md` first.
2. After the local write succeeds and structural integrity passes, Curator pushes a flattened display version to Reflect via `create_note()`. The Reflect copy carries a header line that says: `<!-- mirror of zk/wiki/<title>.md — do not edit in Reflect -->`.
3. The Reflect note's title matches the local file's title. Subsequent edits on the local file produce a new Reflect note with the same title; per the Reflect MCP behavior, `create_note()` with an existing title returns the existing note unchanged. **This is a known limitation:** display updates after the first push are lost until the user manually deletes the Reflect copy and re-syncs. v1 accepts this. v2 may add a delete-and-recreate workflow.
4. Edits made directly in the Reflect UI are not pulled back. They are lost on the next intentional sync (if any). The user is told this in the `/sync` command output.

The `/sync` command (Phase C) is the user-facing entry point: it pushes a single note or all wiki entries. It is opt-in. Wiki entries do not auto-sync — the user decides when an entry is ready for the mobile display copy.

## Migration Strategy: Opportunistic, Not Big-Bang

There is no migration of existing Reflect notes into the wiki layer. The user's existing Reflect corpus stays in Reflect (synced to `zk/daily-notes/`), and pre-2026 topic directories are parked in `zk/archive/`. The wiki layer grows organically:

- New wiki entries are written to `zk/wiki/` directly (Curator + schema).
- Existing notes (Reflect, `zk/archive/`, or anywhere else in L1/L2) are surfaced to L4 **only when they are about to become anchors for a new wiki claim** — at that point the user (or Curator) extracts the relevant claims, structures them per the schema, writes the wiki entry, and the original note remains in place as an L1/L2 capture record (untouched).
- There is no goal to empty Reflect or to hoist the entire vault into the wiki layer. L1 and L2 remain the home for daily notes, voice captures, session reflections, drafts, and most thinking. Most notes will never be in L4 — that is correct, not a failure.

The expected steady-state ratio is roughly: hundreds of L1/L2 notes for every L4 wiki entry. L4 is the slow, careful, anchored kernel. L1 and L2 are the fast surface.

## What Changes for Each Agent

Phase A wired the read path. Phase B shipped `scripts/trust.py`. **Phase C (this milestone) drops Reflect read MCP from every subagent, moves Curator to local-first wiki writes, and adds `/sync` for one-way display push.** Phase D is `/lint`.

| Agent | L1 capture | L4 wiki (`zk/wiki/`) | L3 receipts |
|---|---|---|---|
| **Researcher** | **Local-only, semantic-primary.** `Bash: scripts/semantic.py query` for content queries, `Grep` + `Read` for structural queries. No Reflect MCP tools in frontmatter. If today's daily note is not yet on disk, flags `needs: get_daily_note(today)` and the orchestrator fetches. | Reads `zk/wiki/` with grep directly. | Reads `zk/readwise/`, `zk/papers/` directly. |
| **Curator** | Continues to write to daily notes via `append_to_daily_note` (write-side MCP retained). | **Phase C: drafts wiki entries as markdown proposals with `target_path: zk/wiki/<slug>.md`.** The orchestrator writes the file after user approval (subagents cannot Write). Then `scripts/trust.py --note <path>` verifies structural integrity and reports initial scores. | Unchanged. |
| **Synthesizer** | Reads capture-layer briefs from Researcher; writes session reflections to `zk/reflections/`. | Reads wiki trust scores when available to weight evidence. | Unchanged. |
| **Reviewer** | Continues to gate capture-layer write-backs. | Phase C: gates wiki writes as well. A `@pass: reviewer | status: verified` marker is added to a claim only after Reviewer signs off. | Unchanged. |
| **Scout** | Unchanged. | Unchanged. | Writes promoted briefs to `zk/agent-findings/` (not the ephemeral `zk/cache/`). |

## Cross-References

- Tag taxonomy and validation-depth principle: `epistemic-hygiene.md`
- Wiki entry format and trust propagation rule: `wiki-schema.md`
- Trust engine implementation (Phase B): `scripts/trust.py` (deferred)
- Lint integration (Phase D): `.claude/commands/lint.md` (deferred)
