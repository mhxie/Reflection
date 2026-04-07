# Context Management

Defines how agents manage their context windows efficiently, especially when dealing with large amounts of note content.

## Context Budget

Each agent has a finite context window. Manage it deliberately.

### Priority Ordering

When loading context, prioritize in this order:

1. **System instructions** (agent prompt, protocols) — always loaded
2. **Profile files** (identity.md, directions.md) — always loaded for reflect/review
3. **Today's context** (daily note, current reflection) — always loaded
4. **Recent context** (last 3-7 daily notes, recent reflections) — loaded if space permits
5. **Searched context** (MCP search results, full note reads) — loaded on demand
6. **Historical context** (older notes, old reflections) — loaded only if specifically relevant

### Token Budget Guidelines

| Content Type | Approximate Tokens | Priority |
|---|---|---|
| Agent prompt + protocols | ~2K | Always |
| profile/identity.md | ~3-5K | Always |
| profile/directions.md | ~5-10K | Always for review, optional for reflect |
| Today's daily note | ~1-3K | Always |
| Each additional note (full) | ~1-5K | On demand |
| Each search result (excerpt) | ~200-500 | On demand |
| Previous reflections | ~2-5K each | Last 1-3 |

### When Context Gets Tight

1. **Summarize, don't drop.** If a note is too long, read and summarize the key points rather than skipping it entirely.
2. **Excerpts over full notes.** Use search result excerpts when full note content isn't needed.
3. **Recency over completeness.** If you can only read 10 notes, read the 10 most recent.
4. **Goal notes over daily notes.** Goal notes are denser with relevant information.

## Agent-Specific Context Strategy

### Researcher
- **Read broadly, excerpt narrowly.** Search many notes, read top 10-15 in full, excerpt key quotes for the brief.
- **Don't pass full note content to Synthesizer.** Pass excerpts and citations — the Synthesizer can `get_note()` if needed.

### Synthesizer
- **Start with the research brief, not raw notes.** The brief is pre-filtered.
- **Read full notes only for claims you're making.** Don't read every source — only verify what you cite.

### Reviewer
- **Spot-check, don't re-read everything.** Check 3-5 citations, not all of them.
- **Read profile/directions.md for coverage check.** Don't re-search MCP for goals.

### Challenger
- **Focus on recent daily notes.** Your job is about the present, not comprehensive history.
- **Search for contradictions specifically.** Targeted searches, not broad sweeps.

### Thinker
- **Read frameworks, not notes.** Your value is external perspective, not internal data.
- **One framework deeply > three superficially.**

## Cross-Agent Context Sharing

Agents don't share context windows. All inter-agent communication happens through:
1. **Handoff blocks** (structured output passed via orchestrator)
2. **Files** (zk/reflections/ directory, profile files)
3. **MCP** (each agent can independently query Reflect)

**Rule:** Never assume another agent has context you didn't explicitly pass in the handoff.
