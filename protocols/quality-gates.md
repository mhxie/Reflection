# Quality Gates

Defines checkpoints that must pass before output reaches the user. Each gate has clear pass/fail criteria and a remediation path.

## Gate Architecture

```
[Research] → Gate 1 → [Synthesis] → Gate 2 → [Review] → Gate 3 → [User]
                                       ↑                    |
                                       └── Revision Loop ←──┘

[Curator Proposal] → Gate 4 → [User Approval] → [create_note]
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

| Overall Score | Action |
|--------------|--------|
| 8-10 | APPROVED — deliver to user |
| 6-7.9 | APPROVED_WITH_NOTES — deliver with caveats |
| 4-5.9 | NEEDS_REVISION — send back to Synthesizer with specific fixes (max 2 rounds) |
| 0-3.9 | REJECTED — start over or deliver with major caveats |

**Gate keeper:** Reviewer
**Max revision rounds:** 2 (after 2 failed revisions, deliver with all caveats noted)

## Gate 4: Note Operations (Compact/Merge)

**When:** After Curator produces a proposal, before presenting to user.

| Check | Pass Criteria | Fail Action |
|-------|--------------|-------------|
| Source caching | All source notes cached locally in `zk/cache/` | Abort — do not draft from uncached sources |
| Media count match | Output image count = source image count | Block — re-scan sources, restore missing media |
| Size limit | Each output note < 15KB | Split into numbered parts before presenting |
| Verbatim preservation | Chinese text, interview memos, raw observations preserved word-for-word | Block — diff against cached sources to find paraphrased content |
| Voice separation | External quotes (forum posts, others' experiences) clearly attributed | Block — add attribution markers |
| Factual accuracy | No conflation of different people's experiences or event sequences | Block — cross-check against cached sources |
| Structured data | Pipelines, timelines, tracking tables preserved exactly | Block — copy from cached source |

**Gate keeper:** Orchestrator (verifies Curator's self-assessment in `content_integrity` field)
**Max retries:** 1 (if still failing, present to user with explicit warnings about what's missing)

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

## Gate 6: Deep Dive & Meeting Notes

**When:** Before write-back (Deep Dive) or before creating Reflect note (Meeting).

| Check | Pass Criteria | Fail Action |
|-------|--------------|-------------|
| Scout claims verified | External facts have source URLs | Remove or flag unverified claims |
| Action item attribution (Meeting) | Each action item has an owner | Challenger flags ambiguous items |
| No fabricated connections | Synthesizer didn't invent links between notes | Reviewer spot-checks |

**Gate keeper:** Reviewer + Challenger (Deep Dive), Challenger only (Meeting)
**Max retries:** 1

## Bypass Conditions

Gates can be bypassed when:
- MCP is unavailable (degraded mode — skip Gates 1 and portions of Gate 3)
- User explicitly asks for a quick/rough reflection
- Session is interactive and user is actively participating (lower bar for completeness)

## Gate Metrics

Track over time (stored in session output):
- Gate 1 pass rate
- Gate 2 pass rate
- Gate 3 average score
- Revision loop frequency
- Bypass frequency
