# Agent Handoff Protocol

Defines structured contracts for agent-to-agent communication. Every handoff includes a typed envelope so the receiving agent can parse without guessing.

## Envelope Format

Every agent output that feeds another agent MUST include a metadata block:

```
---handoff---
from: <agent name>
to: <agent name>
type: research-brief | reader-brief | scout-brief | synthesis | review-check | system-review-request | challenge-set | perspective | recommendation | note-operation | meeting-notes | evolution-report | decay-report
confidence: high | medium | low
gaps: <comma-separated list of what's missing>
context_tokens: <approximate token count of payload>
---end-handoff---
```

## Contract: Researcher → Synthesizer

**Type:** `research-brief`

Required fields:
- `query`: What was searched for
- `sources`: Array of `{title, id, edited, relevance_sentence}`
- `excerpts`: Array of `{source_title, quote, language}`
- `gaps`: What was searched for but not found
- `search_strategy`: Which queries were run (text/vector, languages)
- `confidence`: How complete the coverage feels

The Synthesizer MUST NOT re-search. If gaps are critical, escalate to orchestrator.

## Contract: Reader → Synthesizer

**Type:** `reader-brief`

Required fields:
- `lens`: Which reading lens was applied (Critical | Structural | Practical | Dialectical)
- `source`: Article/note title being analyzed
- `findings`: Array of `{finding, supporting_quote, commentary}`
- `cross_signals`: Array of observations for other lenses to investigate
- `verdict`: One-sentence judgment through this lens
- `confidence`: How well the lens fit this content

When the Synthesizer receives multiple `reader-brief` handoffs (from parallel Reader instances), it should:
1. Look for convergence across lenses (multiple lenses reaching the same conclusion)
2. Surface divergence (lenses disagreeing — this is the most interesting output)
3. Combine with Researcher/Scout/Thinker outputs into a unified reading report

## Contract: Synthesizer → Reviewer

**Type:** `synthesis`

Required fields:
- `output_type`: reflection | review | exploration | reading-report
- `claims`: Array of `{claim, source_title, source_quote}`
- `unsourced_claims`: Array of claims made without direct source (should be empty)
- `goals_referenced`: Which goal categories were covered
- `goals_missing`: Which goal categories were not addressed
- `language_distribution`: % English vs Chinese content

## Contract: Reviewer → Orchestrator

**Type:** `review-check`

Required fields (envelope shape only; numeric thresholds are canonical in `.claude/agents/reviewer.md` → Scoring, do not duplicate here):

- `mode`: `"session"` | `"system"` (selects which dimension set + verdict enum applies)
- `overall`: `{score: 0-10, verdict: <see mode>, summary: ""}`
  - `mode: "session"` verdicts: `"APPROVED" | "APPROVED_WITH_NOTES" | "NEEDS_REVISION" | "REJECTED"`
  - `mode: "system"` verdicts: `"APPROVED" | "NEEDS_REVISION" | "REJECTED"` (no notes-only verdict; the artifact-presence floor in reviewer.md routes single-dim flaws into the fix path instead)

Dimension fields by mode:

- **Session mode** (4 dims): `citations`, `goal_coverage`, `honesty`, `staleness`. Each `{score: 0-10, issues: []}` (or `missing_categories` / `flags` / `warnings` respectively).
- **System mode** (4 dims, replacing the session set): `contract_integrity`, `wiring_correctness`, `bug_absence`, `claim_fidelity`. Each `{score: 0-10, issues: []}`.

Score-to-verdict mapping and the artifact-presence floor are defined in `.claude/agents/reviewer.md` § Scoring. Privacy-gate precedence and revision-round policy live in `protocols/quality-gates.md` § Gate 3.

## Contract: Challenger → User

**Type:** `challenge-set`

Required fields:
- `grounding`: What the user seems to be thinking/feeling (evidence-based)
- `affirming`: Question that validates a strength
- `probing`: Question about an assumption
- `challenging`: The uncomfortable question
- `the_one_question`: Single most important question
- `framework_used`: Which framework informed the challenge (if any)
- `emotional_register`: detected mood (excited | neutral | anxious | uncertain | overwhelmed)

## Contract: Thinker → Orchestrator

**Type:** `perspective`

Required fields:
- `reframe`: The situation stripped of the user's framing
- `frameworks_applied`: Array of `{name, insight, applicability: 0-10}`
- `cross_validation`: Where frameworks agree/disagree
- `contrarian_take`: The perspective against the grain
- `external_sources`: Any web research cited

## Contract: Scout → Orchestrator

**Type:** `scout-brief`

Required fields:
- `topic`: What was researched
- `direction`: Which search direction was assigned (Mainstream, Contrarian, Adjacent, etc.)
- `findings`: Array of `{finding, source_url, date, relevance}`
- `contrarian_signal`: At least one perspective challenging the user's view
- `knowledge_gap`: What the user's notes don't cover that the web suggests is important
- `confidence`: How reliable the sources are

## Contract: Librarian → Orchestrator

**Type:** `recommendation`

Required fields:
- `topic`: What recommendations are for
- `resources`: Array of `{title, author, type, core_insight, relevance_to_user}`
- `already_read`: Resources the user already has notes on (excluded from recommendations)
- `contrarian_pick`: At least one recommendation that challenges current thinking

## Contract: Orchestrator → Curator (Compact/Merge Dispatch)

When dispatching the Curator for compact or merge operations, the orchestrator MUST take a **snapshot of each source note at dispatch time** under `<paths.cache>/<operation>-<slug>.md`. The snapshot protects against mid-session mutation: the user may edit a note in their editor while the Curator is drafting. The Curator then works exclusively from those snapshots.

To produce each snapshot: copy the local source file under `$OV/` to `<paths.cache>/<operation>-<slug>.md`. Use the relative path slug (e.g., `compact-daily-notes-2026-04-05.md`) so the origin is obvious.

Dispatch prompt MUST include:
- `snapshot_paths`: array of `<paths.cache>/<operation>-<slug>.md` paths the orchestrator just created

The Curator works exclusively from `snapshot_paths` — it never re-reads the originals. This preserves the "content recoverable even if the user deletes mid-session" property that makes the cache step load-bearing.

## Contract: Curator → Orchestrator

**Type:** `note-operation`

Required fields:
- `operation`: compact | merge | create | replace | wiki-entry
- `target_path`: (required for `wiki-entry`, optional otherwise) Local file path under `<paths.wiki>/<slug>.md` where the orchestrator will write the draft after user approval. Curator cannot Write — it only proposes the path and body.
- `notes_affected`: Array of note titles involved
- `snapshot_paths`: (required for compact/merge) Array of `<paths.cache>/<operation>-<slug>.md` snapshot file paths used as source. Orchestrator verifies these exist before accepting the proposal.
- `media_inventory`: (required for compact/merge, omit for create/replace) `{images: count, tables: count, structured_blocks: count, embeds: count}` — counts from source notes. The orchestrator verifies these counts match the output.
- `media_output_count`: (required for compact/merge) `{images: count, tables: count, structured_blocks: count, embeds: count}` — counts in the proposed output. Must match `media_inventory` or differences must be listed in `changes_summary`.
- `external_content_flagged`: (required for compact/merge, omit for create/replace) boolean — true if any source notes contain content from external sources (forum quotes, others' experiences). If true, those sections must be clearly attributed in `proposed_content`.
- `proposed_content`: The new/merged content (for user approval)
- `estimated_size`: Approximate byte size of `proposed_content`. If >15KB, must include a split plan.
- `content_integrity`: (required for compact/merge, omit for create/replace) `{verbatim_preserved: boolean, structures_preserved: boolean, images_preserved: boolean, checklist_passed: boolean}` — self-assessment that the Content Preservation Checklist was run
- `rationale`: Why this operation was recommended

## Contract: Forgetter → Orchestrator

**Type:** `decay-report`

Forgetter writes a decay report to disk and returns only the path on success; on Write failure it returns the full categorized findings inline so a completed sweep is never lost. Two envelope shapes apply by `mode`:

**Success envelope** (`mode: full | partial`):

Required fields:
- `from`: `forgetter`
- `to`: `orchestrator`
- `type`: `decay-report`
- `report_path`: absolute path under `<paths.agent_findings>/decay-<YYYYMMDD-HHMMSS>.md` (where the agent wrote the report)
- `mode`: `full` (sweep ran to completion) | `partial` (sweep early-terminated on `max_candidates` or `time_budget_s`)
- `summary`: `{redundant: N, time_stale: N, contradicted: N, low_signal: N}` — counts per category

The orchestrator surfaces `report_path` to the user; the user reads the report directly. Forgetter does NOT echo report contents inline in the success case — filesystem-output is the contract.

**Failed-write envelope** (`mode: failed-write`):

When the report `Write` to `<paths.agent_findings>/decay-<TS>.md` fails (disk full, permission denied, parent directory unwritable), Forgetter MUST return the accumulated findings inline rather than silently dropping the sweep:

Required fields:
- `from`: `forgetter`
- `to`: `orchestrator`
- `type`: `decay-report`
- `mode`: `failed-write`
- `write_error`: short string describing the failure
- `summary`: same shape as success envelope
- `findings_inline`: full categorized findings with the same per-category fields as the on-disk report, structured by category. The orchestrator surfaces these to the user even though no path was written, and may attempt a retry.

`report_path` is omitted in the failed-write case (no file exists).

**Cross-reference:** the agent-side spec is `.claude/agents/forgetter.md` → "Return Value" and "Failure Modes to Avoid".

## Contract: Meeting → Orchestrator

**Type:** `meeting-notes`

Required fields:
- `mode`: Executive
- `source`: Description of the meeting (name, date, participants if known)
- `structured_notes`: The formatted output (markdown)
- `action_items`: Array of `{owner, task, deadline}`
- `unclear_items`: Array of items flagged as ambiguous from the transcript
- `confidence`: How clean/complete the transcript was

The orchestrator presents the structured notes to the user and asks whether to create a local note via Curator.

## Contract: Evolver → Orchestrator (System Review Request)

**Type:** `system-review-request`

The orchestrator receives this and dispatches the Reviewer at the specified tier.

Required fields:
- `review_tier`: 1-4 (determines which reviewers the orchestrator dispatches)
- `review_mode`: holistic | diff | both
- `change_scope`: description of what changed
- `files_changed`: Array of file paths
- `status`: uncommitted (Evolver does not commit — orchestrator commits after review)
- `staged_files`: list of files with staged changes

## Escalation Protocol

If any agent encounters:
- **Empty search results**: Try alternative queries (synonym, other language, broader terms) before reporting gap
- **Contradictory evidence**: Flag explicitly — don't resolve silently
- **Token budget exceeded**: Summarize and note truncation

## Revision Loop

When Reviewer returns `NEEDS_REVISION`:
1. Reviewer specifies which checks failed and what would fix them
2. Synthesizer receives revision request with specific issues
3. Synthesizer revises (max 2 revision rounds)
4. If still failing after 2 rounds, deliver with caveats noted
