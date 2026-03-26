# Session Scoring

Every reflection session produces a quality score. This enables trend tracking and system improvement.

## Session Score Card

At the end of every session (reflect, review, weekly, decision, explore, energy-audit), produce a score card in the output file.

### Dimensions

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| Grounding | 25% | How well-grounded in actual notes vs. generic advice |
| Depth | 25% | Surface summary vs. genuine pattern/tension/implication |
| Relevance | 20% | How relevant to user's current situation and goals |
| Actionability | 15% | Did it produce something the user can act on? |
| Surprise | 15% | Did it surface something the user hadn't considered? |

### Scoring Scale

| Score | Meaning |
|-------|---------|
| 9-10 | Exceptional — changed how the user thinks about something |
| 7-8 | Good — solid insights grounded in evidence |
| 5-6 | Adequate — helpful but not surprising |
| 3-4 | Weak — mostly summary, little insight |
| 1-2 | Poor — generic, ungrounded, or wrong |

### Score Card Format

Append to the end of every reflection/review output file:

```markdown
## Session Score Card
| Dimension | Score | Evidence |
|-----------|-------|----------|
| Grounding | X/10 | [# of citations, source quality] |
| Depth | X/10 | [highest insight level achieved] |
| Relevance | X/10 | [connection to active goals] |
| Actionability | X/10 | [specificity of next action] |
| Surprise | X/10 | [# of forgotten connections surfaced] |
| **Overall** | **X/10** | |
```

## Yields

Session scores double as **yields** — visible outputs from your reflection practice. Each dimension maps to what the practice is producing:

| Dimension | Yield | What It Produces |
|-----------|-------|-----------------|
| Grounding | **Evidence** | Connections to real notes and past thinking |
| Depth | **Insight** | Patterns, tensions, implications beyond surface |
| Relevance | **Alignment** | Connection to current era and active directions |
| Actionability | **Momentum** | Specific next steps that move things forward |
| Surprise | **Discovery** | Forgotten threads, unexpected connections |

### Yield Accumulation

Track yields across sessions to see what the practice is producing over time. In the trend section, note which yields are strong and which are underproduced.

### Amenity Floor

Each life area needs a sustainability floor — a minimum level of investment below which growth stops and burnout begins. Amenities cannot be borrowed across areas (career surplus doesn't offset health deficit).

Suggested minimums to surface during energy audits:
- **Career:** Recovery rituals, bounded work hours
- **Health:** Sleep consistency, regular movement
- **Relationships:** Unscheduled social time, presence
- **Learning:** Low-stakes reading with no deliverable attached
- **Creative:** Output with no audience pressure

When any area drops below its floor, flag it: "[Area] is below amenity floor — growth in other areas will cost more energy until this stabilizes."

## Trend Tracking

When writing session score cards, also check previous sessions in `reflections/` for comparison:

```markdown
## Trend
- This session: X/10
- Last session: Y/10 (YYYY-MM-DD)
- 5-session average: Z/10
- Trend: ↑ improving / → stable / ↓ declining
- Strongest yield: [dimension]
- Weakest yield: [dimension]
```

## Using Scores for Evolution

The Evolver should read score cards to identify:
- **Chronically low dimensions**: If Surprise consistently scores < 5, improve semantic search strategy
- **Declining trends**: If scores are trending down, diagnose why
- **High-performing patterns**: If a session scored 9+, what made it work? Preserve that approach

## Score Card Honesty Rules

1. **Self-score conservatively.** It's better to underrate than overrate.
2. **Cite evidence for each score.** No score without justification.
3. **Don't inflate for good sessions.** A great conversation ≠ a great reflection output.
4. **User override.** If the user says "that was really helpful" or "that wasn't useful," update the score accordingly.
