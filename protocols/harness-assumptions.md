# Harness Assumptions Protocol

Identifies and tracks rules in the reflectl system that depend on model capabilities, API limits, or temporal context. These assumptions go stale across model upgrades and API changes. This protocol is the registry and audit checklist; the assumptions themselves stay in their original files.

## Why This Exists

Rules like "use Opus for creative tasks, Sonnet for mechanical tasks" or "load last 3 reflections" encode a snapshot of model capabilities at a point in time. When capabilities change (new model release, context window expansion, cost reduction, new API features), these rules may become wrong, suboptimal, or unnecessary. Without a registry, they are invisible until they cause a problem.

Inspired by the "context anxiety" example from Anthropic's Managed Agents architecture: a behavioral workaround for Sonnet 4.5 became dead weight when Opus 4.5 shipped. The harness encoded a stale assumption about the model.

## Assumption Classification

| Class | Definition | Example | Staleness Signal |
|-------|-----------|---------|-----------------|
| **Model Assignment** | Which model runs which agent | Researcher=Opus | New model release, benchmark shift, cost change |
| **Token/Context Budget** | Context window sizing, loading limits | "last 3 reflections" | Context window expansion |
| **Temporal Threshold** | Time-based triggers and warnings | "7 days stale" for profile | User behavior data |
| **API Constraint** | Limits imposed by external APIs | "20KB per create_note" | API changelog |
| **Turn Budget** | maxTurns per agent | Evolver=25 | Model efficiency changes |
| **Search Strategy** | Query patterns tuned to current capability | semantic.py stub fallback | semantic.py mode change |

## Assumption Registry

### Model Assignments

| Agent | Current Model | Rationale | Re-test When |
|-------|--------------|-----------|-------------|
| Researcher | Opus | Deep reading comprehension over large note sets | Sonnet matches Opus on reading comprehension benchmarks |
| Synthesizer | Opus | Pattern recognition across multiple sources | Sonnet matches Opus on synthesis quality |
| Reviewer | Sonnet | Mechanical checklist work, cost efficiency | Haiku becomes capable enough for rubric scoring |
| Challenger | Opus | Nuance for question taxonomy and emotional register | Sonnet improves on open-ended question quality |
| Thinker | Opus | Independent framework application, meta-cognitive checks | Sonnet matches on framework reasoning |
| Evolver | Opus | System-level reasoning across many files | Sonnet matches on multi-file coherence |
| Curator | Sonnet | Structured note operations, checklist execution | Haiku becomes capable for preservation checks |
| Scout | Sonnet | Web search aggregation, structured output | Haiku becomes capable for search + format |
| Reader | Opus | Deep analytical reading with 4 lenses | Sonnet matches on analytical reading quality |
| Meeting | Sonnet | Transcript extraction, structured output | Haiku becomes capable for transcript processing |
| Librarian | Sonnet | Resource recommendation, structured Chinese output | Haiku becomes capable for bilingual recommendations |

### Token/Context Budgets

| Rule | Location | Current Value | Re-test When |
|------|----------|--------------|-------------|
| Reflections loaded at session start | session-continuity.md, reflect.md | Last 3 | Context window doubles |
| Daily notes loaded | reflect.md, session-continuity.md | Last 3-7 | Context window doubles |
| Profile token estimate | reflect.md, session-continuity.md | 3-5K identity, 5-10K directions | Profile format changes significantly |
| Agent prompt + protocols budget | reflect.md, session-continuity.md | ~2K | Agent definitions grow beyond budget |
| Session log excerpt budget | reflect.md, session-continuity.md | ~500-1K | Session logs grow in scope |

### Temporal Thresholds

| Rule | Location | Current Value | Re-test When |
|------|----------|--------------|-------------|
| Profile staleness warning | CLAUDE.md, reflect.md, review.md | 7 days | User data shows profiles change faster/slower |
| Semantic search recency window | reflect.md | 7 days for recent, 3+ months for forgotten | Embedding index makes recency less important |
| L2 staleness thresholds | staleness.py | dormant=45d, stale=90d, promote=180d+2refs | First real corpus ages past 90 days; tune with actual archival decisions |
| Meta-reflection trigger | evolver.md (principle 8 pruning trigger) | Every 5 sessions | Session volume data |

### API Constraints

| Rule | Location | Current Value | Re-test When |
|------|----------|--------------|-------------|
| create_note size limit | CLAUDE.md, curator.md | ~20KB (15KB working) | Reflect API changelog |
| No update/delete operations | CLAUDE.md | Hard constraint | Reflect API changelog |
| create_note parameter names | CLAUDE.md | contentMarkdown, subject | Reflect API changelog |
| No markdown tables in create_note | CLAUDE.md | Hard constraint | Reflect API changelog |
| Silent empty note on wrong params | CLAUDE.md | Known bug | Reflect API fix |

### Turn Budgets

| Agent | Location | Current maxTurns | Re-test When |
|-------|----------|-----------------|-------------|
| Evolver | evolver.md | 25 | Model efficiency improves |
| Researcher | researcher.md | 15 | Search strategy changes |
| Synthesizer | synthesizer.md | 15 | Model gets faster at synthesis |
| Reviewer | reviewer.md | 15 | Checklist execution speed |
| Curator | curator.md | 15 | Note operation complexity |
| Scout | scout.md | 15 | Web search patterns change |
| Librarian | librarian.md | 15 | Recommendation patterns |
| Challenger | challenger.md | 10 | Question generation needs |
| Thinker | thinker.md | 15 | Framework application depth |
| Meeting | meeting.md | 10 | Transcript complexity |
| Reader | reader.md | 15 | Reading depth needs |

### Search Strategy

| Rule | Location | Current Value | Re-test When |
|------|----------|--------------|-------------|
| semantic.py is primary for content queries | CLAUDE.md | Real embedding mode | Index is machine-local at `~/.cache/reflectl/lance/`; rebuild with `uv run scripts/semantic.py index` |
| Grep for structural queries only | CLAUDE.md | Always | semantic.py covers structural queries too |
| Retry with synonyms on empty results | error-handling.md | Manual retry | semantic.py handles synonyms natively |

## Audit Checklist

Run this checklist when any of these events occur:

- [ ] New Claude model release (Opus, Sonnet, Haiku generation change)
- [ ] Reflect API update
- [ ] Context window size change
- [ ] semantic.py mode change (stub to real)
- [ ] Cost structure change (model pricing)
- [ ] Quarterly system review

**Audit procedure:**

1. Identify which registry sections the event affects (use the "Re-test When" column)
2. For each triggered assumption, test whether the current value is still optimal
3. If stale, propose a change via the Evolver's OODA cycle
4. Log the audit result in the next session log under "Harness Assumptions Exercised"
5. Update this registry with new values and rationale after changes land

## Integration

- **Session logs** record which assumptions were load-bearing each session (the "Harness Assumptions Exercised" section in `protocols/session-log.md`)
- **Evolver** checks this registry during its Observe phase for triggered re-test conditions
- **Evolver** aggregates assumption-exercise data across session logs to spot assumptions that are never tested or always active
