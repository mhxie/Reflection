# Harness Assumptions Protocol

Identifies and tracks rules in the atelier system that depend on model capabilities, API limits, or temporal context. These assumptions go stale across model upgrades and API changes. This protocol is the registry and audit checklist; the assumptions themselves stay in their original files.

## Why This Exists

Rules like "use the high tier for creative tasks, the cheap tier for mechanical tasks" or "load last 3 reflections" encode a snapshot of model capabilities at a point in time. When capabilities change (new model release, context window expansion, cost reduction, new API features), these rules may become wrong, suboptimal, or unnecessary. Without a registry, they are invisible until they cause a problem.

Inspired by the general lesson: a behavioral workaround for an older model in a tier becomes dead weight when a stronger model ships in that tier. The harness encoded a stale assumption about the model.

## Assumption Classification

| Class | Definition | Example | Staleness Signal |
|-------|-----------|---------|-----------------|
| **Voice Assignment** | Which voice band each role binds to | Researcher = deep band | New model release, benchmark shift, cost change |
| **Token/Context Budget** | Context window sizing, loading limits | "last 3 reflections" | Context window expansion |
| **Temporal Threshold** | Time-based triggers and warnings | "7 days stale" for profile | User behavior data |
| **Turn Budget** | maxTurns per agent | Evolver=25 | Model efficiency changes |
| **Search Strategy** | Query patterns tuned to current capability | semantic.py stub fallback | semantic.py mode change |

## Assumption Registry

### Voice Assignments

`harness/agents.toml` is the canonical source of truth for the per-agent `voices` keyed inline table (`{native = "X", direct = "Y"}` or single-leg variants). `harness/models.toml` declares model identities (committed; just names + comments). Provider/model **bindings** (model id, endpoint URL, env var, request extras) live in the gitignored `profile/models.toml`; loaders merge schema + bindings at runtime. `harness_lint.py` validates that every agent's voices reference identities that exist in the schema. The table below is the audit-trigger registry only: it does not restate the per-agent voices (read agents.toml for those), it lists what staleness signal would force a re-evaluation per role family.

Voice band vocabulary used in this file:
- **deep** — flagship pair (e.g., highest-cognition Anthropic + highest-cognition direct-api)
- **mid** — mid-tier pair (cross-provider, cheaper than deep but still substantive)
- **cheap** — minimal pair (mechanical I/O, verbatim preservation)
- **external** — cross-provider audit pair (no Anthropic leg by design)

| Agent | Current voice band | Re-test When |
|-------|----|-------------|
| Researcher | deep | A cheaper tier matches the primary on reading comprehension benchmarks |
| Synthesizer | deep | A cheaper tier matches the primary on synthesis quality |
| Challenger | deep | A cheaper tier improves on open-ended question quality |
| Thinker | deep | A cheaper tier matches the primary on framework reasoning |
| Evolver | deep | A cheaper tier matches the primary on multi-file coherence |
| Scholar | deep | A cheaper tier matches the primary on dense-paper reading quality |
| Reader | mid | A cheaper tier matches the primary on routine-article reading quality |
| Reviewer | mid | Cross-provider agreement rate drops on rubric scoring; cost shifts in either binding |
| Curator | mid | Cross-provider agreement rate drops on note preservation |
| Scout | mid | Cross-provider agreement rate drops on web triage |
| Meeting | mid | Cross-provider agreement rate drops on transcript extraction |
| Librarian | mid | Cross-provider agreement rate drops on bilingual recommendations |
| Privacy Reviewer | mid | Cross-provider agreement rate drops on semantic privacy scan; either binding deprecates |
| Scribe | cheap (single-leg, native only) | A cheaper-still verbatim model becomes available; the current native voice fails verbatim-preservation tests |
| External-Reviewer | external | A new external provider becomes worth adding; one of the current legs deprecates |

### Token/Context Budgets

| Rule | Location | Current Value | Re-test When |
|------|----------|--------------|-------------|
| Reflections loaded at session start | session-continuity.md, hi.md | Last 3 | Context window doubles |
| Daily notes loaded | hi.md, session-continuity.md | Last 3-7 | Context window doubles |
| Profile token estimate | hi.md, session-continuity.md | 3-5K identity, 5-10K directions | Profile format changes significantly |
| Agent prompt + protocols budget | hi.md, session-continuity.md | ~2K | Agent definitions grow beyond budget |
| Session log excerpt budget | hi.md, session-continuity.md | ~500-1K | Session logs grow in scope |

### Temporal Thresholds

| Rule | Location | Current Value | Re-test When |
|------|----------|--------------|-------------|
| Profile staleness warning | CLAUDE.md, hi.md, review.md | 7 days | User data shows profiles change faster/slower |
| Semantic search recency window | hi.md | 7 days for recent, 3+ months for forgotten | Embedding index makes recency less important |
| L2 staleness thresholds | staleness.py | dormant=45d, stale=90d, promote=180d+2refs | First real corpus ages past 90 days; tune with actual archival decisions |
| Meta-reflection trigger | evolver.md (principle 8 pruning trigger) | Every 5 sessions | Session volume data |

### Turn Budgets

| Agent | Location | Current maxTurns | Re-test When |
|-------|----------|-----------------|-------------|
| Evolver | evolver.md | 25 | Model efficiency improves |
| Researcher | researcher.md | 15 | Search strategy changes |
| Synthesizer | synthesizer.md | 15 | Model gets faster at synthesis |
| Reviewer | reviewer.md | 100 | Checklist execution speed |
| Privacy Reviewer | privacy-reviewer.md | 100 | Semantic-leak coverage needs |
| Curator | curator.md | 15 | Note operation complexity |
| Scout | scout.md | 15 | Web search patterns change |
| Librarian | librarian.md | 15 | Recommendation patterns |
| Challenger | challenger.md | 10 | Question generation needs |
| Thinker | thinker.md | 15 | Framework application depth |
| Meeting | meeting.md | 10 | Transcript complexity |
| Reader | reader.md | 15 | Reading depth needs |
| Scholar | scholar.md | 15 | Dense-text reading depth needs (matches Reader; voices differ) |
| Scribe | scribe.md | 10 | Mechanical capture pace |

### Search Strategy

| Rule | Location | Current Value | Re-test When |
|------|----------|--------------|-------------|
| semantic.py is primary for content queries | CLAUDE.md | Real embedding mode | Index is machine-local at `~/.cache/atelier/lance/`; rebuild with `uv run scripts/semantic.py index` |
| Grep for structural queries only | CLAUDE.md | Always | semantic.py covers structural queries too |
| Retry with synonyms on empty results | error-handling.md | Manual retry | semantic.py handles synonyms natively |

### Known Runtime Caps

| Assumption | Where it bites | Re-test When |
|---|---|---|
| `maxTurns` frontmatter is the sole turn budget for `Agent`-tool dispatches | Empirically, system reviews (reviewer + evolver) truncate around 25-32 tool uses despite `maxTurns: 100` in their .md frontmatter. The script-driven external-reviewer (chat_completion.py + codex CLI) IS uncapped. The `maxTurns: 100` setting is intent; actual runtime applies an additional ceiling we don't control from agent definitions. | Claude Code releases that change subagent dispatch turn budgets, OR a workaround that routes system reviews through script-driven dispatch (chat_completion.py with the reviewer prompt) instead of `Agent` tool. |

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
