# /promote — Create L4 wiki entry from L2 source notes

Two-step workflow to promote existing L2 working notes (daily notes, reflections, agent findings, drafts) into a schema-compliant L4 wiki entry under `zk/wiki/`. Inspired by llm_wiki's analyze-then-generate ingest pipeline, adapted for reflectl's claim-level trust architecture.

**Scope:** one wiki entry per invocation. The user names a topic or set of source notes; the command produces a draft wiki entry with pre-populated `@anchor` markers for user review.

## Prerequisites

1. Source notes must already exist under `zk/` (any tier except L4).
2. `protocols/wiki-schema.md` defines the target format.
3. `scripts/trust.py` validates structural integrity after creation.

## Arguments

The user provides one of:
- A **topic** (e.g., "promote distributed locking") and the Researcher finds relevant source notes.
- One or more **file paths** (e.g., `zk/daily-notes/2026-04-08.md`, `zk/agent-findings/lance-brief.md`).

## Process

### Phase 1: Gather and Analyze (Researcher)

Dispatch the **Researcher** agent:

```
Research brief request: identify all notes related to [topic/paths] that contain
claims suitable for L4 promotion. For each candidate:
  - Extract factual claims (not opinions or speculation)
  - Note any external sources referenced (URLs, paper citations, DOIs)
  - Flag claims that overlap with existing wiki entries under zk/wiki/
  - Report the validation depth of each source note (L1 raw, L2 working, L3 external)

Search strategy:
  1. scripts/semantic.py query "[topic]" --top 20  (primary)
  2. Grep for exact terms across zk/ (structural follow-up)
  3. Read candidate files in full
  4. Cross-reference against existing zk/wiki/ entries via trust.py --json

Return a structured brief with:
  - candidate_notes: [{path, title, relevant_claims: [text, source_url?]}]
  - existing_wiki_overlap: [{wiki_entry, overlapping_claims}]
  - suggested_title: proposed H1 for the new wiki entry
  - suggested_claims: [{claim_text, anchor_candidates: [{type, id, url}]}]
```

Present the Researcher's brief to the user. Ask:
1. Confirm or adjust the suggested title
2. Confirm or prune the claim list
3. Flag any claims that should NOT be promoted (too speculative, personal opinion, etc.)

### Phase 2: Generate Draft (Curator)

After user approval of the brief, dispatch the **Curator** agent with the approved claims:

```
Wiki entry draft request.

Target path: zk/wiki/<slugified-title>.md
Schema reference: protocols/wiki-schema.md

Approved claims and anchors:
[paste the user-approved claim list from Phase 1]

Instructions:
  1. Generate a wiki entry following protocols/wiki-schema.md exactly:
     - H1 title
     - ## Summary (prose synthesis, no anchors)
     - ## Claims with [C1], [C2], ... headings
     - Each claim gets a body paragraph and ^cn block ID
     - Each claim gets a fenced ```anchors block with @anchor markers
     - ## Revision Log with today's date and creation context
  2. For @anchor markers:
     - Use the appropriate type (s2, arxiv, doi, isbn, url, gist)
     - Set valid_at to today's date
     - Include the source URL or identifier from the Researcher's brief
  3. Do NOT add @cite markers yet (those require target entries to exist).
     Leave a comment in the Revision Log noting which existing wiki entries
     could be cross-referenced once the entry is created.
  4. Do NOT add @pass markers (those come from post-creation review).
  5. Return the full markdown content as a draft.
```

### Phase 3: Validate and Write

1. **Present the draft** to the user for review. Show the full markdown.
2. On user approval, **write the file** to `zk/wiki/<slug>.md`.
3. Run `scripts/trust.py --note zk/wiki/<slug>.md` to verify structural integrity.
   - If errors: show them, ask the user if they want to fix or abort.
   - If clean: report the initial trust score (will be raw PageRank, no floor until a reviewer pass).
4. Run `scripts/lint.py` to check for corpus-level issues (shared anchors, etc.).
5. Regenerate the wiki index: `scripts/trust.py --index`.

### Phase 4: Post-Creation Suggestions

After successful creation, suggest next steps:

1. **Add @cite edges:** If the lint report shows `shared-anchor-no-cite` findings involving the new entry, suggest specific @cite markers to add.
2. **Request reviewer pass:** "Run a review session to add `@pass: reviewer | status: verified` markers, which unlocks the 0.1 trust floor."
3. **Sync to Reflect:** "Run `/sync` to push the new entry to Reflect for mobile reading."
4. **Update the wiki index:** Already done in Phase 3 step 5.

## Example Invocation

```
User: /promote distributed locking patterns
```

The command finds notes about distributed locking in daily notes, agent findings, and reading notes. Extracts claims about lock granularity, consensus protocols, lease-based mechanisms. Produces a wiki entry like:

```markdown
# Distributed Locking Patterns

## Summary
[synthesis of the key patterns...]

## Claims

### [C1] Lease-based locks with TTL are preferred over indefinite locks in distributed systems

[body with evidence...] ^c1

```anchors
@anchor: url:https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html | valid_at: 2026-04-11
```

## Revision Log

- 2026-04-11: Initial draft promoted from [[2026-04-08]] daily note and [[Lance MVCC deep dive]] agent finding. Candidate @cite edges: [[Lance MVCC Commit Protocol]] (shared S3 locking context), [[Exactly-Once Commit Pattern]] (shared two-phase commit concepts).
```

## Error Handling

- **No relevant source notes found:** "No notes found related to [topic]. Try a different search term, or provide specific file paths."
- **All claims already covered by existing wiki entries:** "The claims in these notes are already covered by [existing entry]. Consider adding @cite markers to the existing entry instead of creating a new one."
- **Structural integrity failure after write:** Show the specific errors from trust.py. Offer to fix in place or delete and retry.
- **Curator unavailable:** The orchestrator can generate the draft directly using the schema as a template, though the Curator's Content Preservation Checklist adds safety.
