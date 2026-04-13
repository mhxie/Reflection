# Contradiction Detection

Surfaces contradictions between the user's past and present thinking. Contradictions are the highest-value material for reflection — they reveal growth, blind spots, or unresolved tensions.

## Why This Matters

Five Whys root cause: Sessions feel generic when questions aren't grounded in the user's own contradictions. Generic questions get generic answers. Contradictions are personal, specific, and impossible to ignore.

## Detection Strategies

### Strategy 1: Temporal Contradiction
Search for the same topic across time:
1. Identify a strong current belief from today's/recent notes
2. Search for the same topic in older daily notes: `Bash: uv run scripts/semantic.py query "<topic>" --before "<3 months ago, YYYY-MM-DD>" --top 5` — the semantic script supports date filters and walks `zk/daily-notes/` + `zk/reflections/` directly. For exact-string follow-ups, `Grep(pattern: "<term>", path: "zk/daily-notes/")` and filter by filename date.
3. Compare: has the user's position changed? If yes, that's a contradiction worth surfacing.

**Example:** "Today you're excited about ML infra. But 6 months ago in [[Note]], you wrote 'I want to stay close to distributed systems fundamentals.' What shifted?"

### Strategy 2: Cross-Domain Contradiction
The user applies different rules to different life areas:
1. Search for a principle in one domain (e.g., "career: take risks")
2. Search for the same principle in another domain (e.g., "finance: play it safe")
3. Surface the tension: "You advocate risk in career but caution in finances. Is that deliberate?"

### Strategy 3: Say-Do Contradiction
Compare stated goals with actual behavior:
1. Read goals from `profile/directions.md`
2. Search recent daily notes for evidence of action on those goals
3. Surface gaps: "You list [[Goal X]] as high priority, but it hasn't appeared in your daily notes for 6 weeks."

### Strategy 4: Value Contradiction
The user holds two values that compete:
1. Identify values from `protocols/values-clarification.md` analysis
2. Find notes where each value was prioritized
3. Surface: "In [[Note A]] you prioritized X. In [[Note B]] you prioritized Y. When they conflict, which wins?"

## Integration

### Researcher
Add contradiction search as Phase 4 (after gap filling):
- Run at least 1 temporal contradiction search per session
- Include in research brief under "Contradictions Found"

### Challenger
Contradictions are your best material:
- Frame as curiosity, not accusation: "I noticed something interesting..."
- Always cite both sides: [[Old Note]] vs [[Recent Note]]
- The question is "what changed?" not "you're inconsistent"

### Synthesizer
When patterns include contradictions:
- Classify as Oscillation pattern (see pattern-library.md)
- Note whether the contradiction is resolved or ongoing

## Rules

1. **Contradictions are gifts, not attacks.** Frame them as opportunities for insight.
2. **Both sides must be cited.** Never claim a contradiction without [[Note]] evidence for each position.
3. **Growth is a valid resolution.** "I changed my mind" is a perfectly good answer.
4. **One per session is enough.** Don't overwhelm with contradictions.
5. **Skip if the user is already in tension.** Don't pile on during difficult moments.
