# Agent Handoff Protocol

Defines structured contracts for agent-to-agent communication. Every handoff includes a typed envelope so the receiving agent can parse without guessing.

## Envelope Format

Every agent output that feeds another agent MUST include a metadata block:

```
---handoff---
from: <agent name>
to: <agent name>
type: research-brief | reader-brief | scout-brief | synthesis | review-check | system-review-request | challenge-set | perspective | recommendation | note-operation | meeting-notes | evolution-report
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

Required fields:
- `citations`: `{score: 0-10, issues: []}`
- `goal_coverage`: `{score: 0-10, missing_categories: []}`
- `honesty`: `{score: 0-10, flags: []}`
- `staleness`: `{score: 0-10, warnings: []}`
- `overall`: `{score: 0-10, verdict: "APPROVED" | "APPROVED_WITH_NOTES" | "NEEDS_REVISION" | "REJECTED", summary: ""}`

Score thresholds (aligned with quality-gates.md and reviewer.md):
- 8-10: `APPROVED` — deliver to user
- 6-7.9: `APPROVED_WITH_NOTES` — deliver with caveats
- 4-5.9: `NEEDS_REVISION` — triggers revision loop (max 2 rounds)
- 0-3.9: `REJECTED` — start over or deliver with major caveats

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

When dispatching the Curator for compact or merge operations, the orchestrator MUST:

1. **Fetch all source notes** via `get_note()` before dispatching
2. **Cache each note** to `papers/cache/<operation>-<note-id>.md` (e.g., `compact-abc123.md`, `merge-def456.md`)
3. **Pass cache file paths** to the Curator in the dispatch prompt
4. The Curator works exclusively from cached files — it never fetches from MCP itself

This ensures content is recoverable if the user deletes source notes mid-session.

## Contract: Curator → Orchestrator

**Type:** `note-operation`

Required fields:
- `operation`: compact | merge | create | replace
- `notes_affected`: Array of note titles involved
- `cached_sources`: (required for compact/merge) Array of local cache file paths used as source. Orchestrator verifies these exist before accepting the proposal.
- `media_inventory`: (required for compact/merge, omit for create/replace) `{images: count, tables: count, structured_blocks: count, embeds: count}` — counts from source notes. The orchestrator verifies these counts match the output.
- `media_output_count`: (required for compact/merge) `{images: count, tables: count, structured_blocks: count, embeds: count}` — counts in the proposed output. Must match `media_inventory` or differences must be listed in `changes_summary`.
- `external_content_flagged`: (required for compact/merge, omit for create/replace) boolean — true if any source notes contain content from external sources (forum quotes, others' experiences). If true, those sections must be clearly attributed in `proposed_content`.
- `proposed_content`: The new/merged content (for user approval)
- `estimated_size`: Approximate byte size of `proposed_content`. If >15KB, must include a split plan.
- `content_integrity`: (required for compact/merge, omit for create/replace) `{verbatim_preserved: boolean, structures_preserved: boolean, images_preserved: boolean, checklist_passed: boolean}` — self-assessment that the Content Preservation Checklist was run
- `rationale`: Why this operation was recommended

## Contract: Meeting → Orchestrator

**Type:** `meeting-notes`

Required fields:
- `mode`: Executive
- `source`: Description of the meeting (name, date, participants if known)
- `structured_notes`: The formatted output (markdown)
- `action_items`: Array of `{owner, task, deadline}`
- `unclear_items`: Array of items flagged as ambiguous from the transcript
- `confidence`: How clean/complete the transcript was

The orchestrator presents the structured notes to the user and asks whether to create a Reflect note via Curator.

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
- **MCP connection failure**: Report the failure, continue with cached index data
- **Empty search results**: Try alternative queries (synonym, other language, broader terms) before reporting gap
- **Contradictory evidence**: Flag explicitly — don't resolve silently
- **Token budget exceeded**: Summarize and note truncation

## Revision Loop

When Reviewer returns `NEEDS_REVISION`:
1. Reviewer specifies which checks failed and what would fix them
2. Synthesizer receives revision request with specific issues
3. Synthesizer revises (max 2 revision rounds)
4. If still failing after 2 rounds, deliver with caveats noted
