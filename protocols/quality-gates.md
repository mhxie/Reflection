# Quality Gates

Defines checkpoints that must pass before output reaches the user. Each gate has clear pass/fail criteria and a remediation path.

## Gate Architecture

```
[Research] → Gate 1 → [Synthesis] → Gate 2 → [Review] → Gate 3 → [User]
                                       ↑                    |
                                       └── Revision Loop ←──┘

[Curator Proposal] → Gate 4 → [User Approval] → [Orchestrator Write/Edit]
```

## Gate 1: Research Completeness

**When:** After Researcher finishes, before Synthesizer starts.

| Check | Pass Criteria | Fail Action |
|-------|--------------|-------------|
| Source count | >= 5 relevant notes found | Try alternative search queries |
| Language coverage | Both Chinese and English searched | Run missing language queries |
| Recency | At least 2 notes from last 30 days | Expand time range, note staleness |
| Gap acknowledgment | Gaps explicitly listed | Researcher must document gaps |
| Handoff format | Valid `---handoff---` block present | Researcher must format output |

**Gate keeper:** Orchestrator (main agent)
**Max retries:** 1 (if fail, proceed with degraded flag)

## Gate 2: Synthesis Quality

**When:** After Synthesizer finishes, before Reviewer starts.

| Check | Pass Criteria | Fail Action |
|-------|--------------|-------------|
| Citation density | >= 80% of claims have [[citations]] | Flag unsourced claims for review |
| Insight level | At least 1 Pattern/Tension/Implication level insight | Synthesizer must deepen |
| Goal coverage | All active categories mentioned or explained | Address missing categories |
| Language matching | Chinese sources → Chinese sections | Fix language mismatches |
| Source audit | Source audit block present at end | Synthesizer must add it |

**Gate keeper:** Orchestrator (main agent)
**Max retries:** 1

## Gate 3: Review Pass

**When:** After Reviewer scores, before presenting to user.

**Verdict thresholds (canonical):** `.claude/agents/reviewer.md` → Scoring. Both Session Review and System Review verdict tables (the score bands and the artifact-presence floor) live there. Do not restate the numbers in this file: when reviewer.md changes, this gate inherits automatically.

Mode invariants enforced here (not in reviewer.md):

- The privacy gate (`/system-review` Phase 1b, mirrored from `/lint` Phase 0c) precedes scoring. Non-empty `scripts/privacy_check.py` hits force `NEEDS_REVISION` before dispatch, regardless of any score the reviewers would otherwise emit.
- **Gate keeper:** Reviewer.
- **Max revision rounds:** Session = 2 (after 2 failed revisions, deliver with all caveats). System = unlimited (Evolver may escalate to user after 2 rounds without progress).

## Gate 4: Note Operations (Compact/Merge)

**When:** After Curator produces a proposal, before presenting to user.

The `note-operation` envelope (canonical fields: `protocols/agent-handoff.md` → Curator → Orchestrator) carries a `content_integrity` self-assessment plus the underlying invariants (`snapshot_paths` exist, `media_inventory == media_output_count`, `estimated_size < 15KB`, `external_content_flagged` attribution). This gate verifies those invariants; it does not redefine them.

| Verification | How | Fail action |
|---|---|---|
| Snapshot existence | Stat each `snapshot_paths` entry on disk | Abort: do not draft from un-snapshotted sources |
| Media count parity | Compare `media_inventory` vs `media_output_count`; require reconciliation in `changes_summary` if they differ | Block: re-scan snapshot files, restore missing media |
| Size limit | If `estimated_size >= 15KB`, require a split plan before user-facing presentation | Block: split into numbered parts before presenting |
| Content integrity attestation | Spot-check `content_integrity.verbatim_preserved` against snapshot diff (Chinese text, memos, raw observations); confirm external voices are attributed; confirm structured blocks (tables, pipelines, timelines) are byte-equal to source | Block: diff against snapshot to find paraphrased content; add attribution markers; copy structured blocks from snapshot |

**Gate keeper:** Orchestrator (verifies Curator's `content_integrity` self-assessment; Curator does not self-clear).
**Max retries:** 1 (if still failing, present to user with explicit warnings about what is missing).

## Gate 5: Profile Validation (/introspect)

**When:** After profile files are drafted, before writing to disk.

| Check | Pass Criteria | Fail Action |
|-------|--------------|-------------|
| Citation accuracy | Claims about user's taste/goals backed by real notes | Fix unsourced claims |
| Curiosity vector validity | Each vector has 3+ note references, not noise | Remove weak vectors |
| Completeness | No major life areas silently omitted | Add missing areas or explain gap |
| Profile consistency | No contradictions between identity, directions, and expertise | Resolve or flag as tension |

**Gate keeper:** Reviewer (Citation Accuracy + Honesty dimensions) + Challenger (blind spots)
**Max retries:** 1 (present to user with caveats if still failing)

## Gate 6: Deep Dive & Meeting Transcripts

**When:** Before write-back (Deep Dive) or before creating a local note (Meeting).

| Check | Pass Criteria | Fail Action |
|-------|--------------|-------------|
| Scout claims verified | External facts have source URLs | Remove or flag unverified claims |
| Action item attribution (Meeting) | Each action item has an owner | Challenger flags ambiguous items |
| No fabricated connections | Synthesizer didn't invent links between notes | Reviewer spot-checks |

**Gate keeper:** Reviewer + Challenger (Deep Dive), Challenger only (Meeting)
**Max retries:** 1

## Bypass Conditions

Gates can be bypassed when:
- User explicitly asks for a quick/rough reflection
- Session is interactive and user is actively participating (lower bar for completeness)

## Gate Metrics

Track over time (stored in session output):
- Gate 1 pass rate
- Gate 2 pass rate
- Gate 3 average score
- Revision loop frequency
- Bypass frequency
