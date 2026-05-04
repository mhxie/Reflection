# Harness Assumptions Protocol

Identifies and tracks rules in the atelier system that depend on model capabilities, API limits, or temporal context. These assumptions go stale across model upgrades and API changes. This protocol is the registry and audit checklist; the assumptions themselves stay in their original files.

## Why This Exists

Rules like "use the high tier for creative tasks, the cheap tier for mechanical tasks" or "load last 3 reflections" encode a snapshot of model capabilities at a point in time. When capabilities change (new model release, context window expansion, cost reduction, new API features), these rules may become wrong, suboptimal, or unnecessary. Without a registry, they are invisible until they cause a problem.

Inspired by the general lesson: a behavioral workaround for an older model in a tier becomes dead weight when a stronger model ships in that tier. The harness encoded a stale assumption about the model.

## Assumption Classification

| Class | Definition | Example | Staleness Signal |
|-------|-----------|---------|-----------------|
| **Model Assignment** | Which tier runs which agent | Researcher=core_intelligence | New model release, benchmark shift, cost change |
| **Token/Context Budget** | Context window sizing, loading limits | "last 3 reflections" | Context window expansion |
| **Temporal Threshold** | Time-based triggers and warnings | "7 days stale" for profile | User behavior data |
| **Turn Budget** | maxTurns per agent | Evolver=25 | Model efficiency changes |
| **Search Strategy** | Query patterns tuned to current capability | semantic.py stub fallback | semantic.py mode change |

## Assumption Registry

### Model Assignments

`harness/models.toml` is the source of truth for **profile schema, invocation pattern, and agent assignments**. The actual provider/model **bindings** (model id, endpoint URL, env var, request extras) live in the gitignored `profile/models.toml`; loaders merge the two at runtime. See the `[profiles.*.rationale]` fields in the schema file for *why* a profile was chosen. `harness_lint.py` (`models-claude-drift`) catches frontmatter↔toml drift. The table below is the audit-trigger registry only: which profile each agent uses, and what staleness signal would force a re-evaluation.

| Agent | Profile (see `harness/models.toml`) | Re-test When |
|-------|-------------------------------------|-------------|
| Researcher | `core_intelligence` | A cheaper tier matches the primary on reading comprehension benchmarks |
| Synthesizer | `core_intelligence` | A cheaper tier matches the primary on synthesis quality |
| Challenger | `core_intelligence` | A cheaper tier improves on open-ended question quality |
| Thinker | `core_intelligence` | A cheaper tier matches the primary on framework reasoning |
| Evolver | `core_intelligence` | A cheaper tier matches the primary on multi-file coherence |
| Reader | `core_intelligence` | A cheaper tier matches the primary on analytical reading quality |
| Reviewer | `cross_validation` | Cross-provider agreement rate drops on rubric scoring; cost shifts in either binding |
| Curator | `cross_validation` | Cross-provider agreement rate drops on note preservation |
| Scout | `cross_validation` | Cross-provider agreement rate drops on web triage |
| Meeting | `cross_validation` | Cross-provider agreement rate drops on transcript extraction |
| Librarian | `cross_validation` | Cross-provider agreement rate drops on bilingual recommendations |
| Privacy Reviewer | `cross_validation` | Cross-provider agreement rate drops on semantic privacy scan; either binding deprecates |

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
| semantic.py is primary for content queries | CLAUDE.md | Real embedding mode | Index is machine-local at `~/.cache/atelier/lance/`; rebuild with `uv run scripts/semantic.py index` |
| Grep for structural queries only | CLAUDE.md | Always | semantic.py covers structural queries too |
| Retry with synonyms on empty results | error-handling.md | Manual retry | semantic.py handles synonyms natively |

## Audit Checklist

Run this checklist when any of these events occur:

- [ ] New model release in any tier (any provider used in `profile/models.toml` bindings)
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
