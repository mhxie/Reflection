# Decision Journal

Structured decision-making session for important choices. Uses thinking frameworks to analyze a decision from multiple angles.

## Trigger

User says something like:
- "I need to decide..."
- "Should I..."
- "Help me think through..."
- "I'm torn between..."

## Prerequisites

1. Read `profile/identity.md` and `profile/directions.md` for context.
2. Read `frameworks/cross-validation.md` for framework selection.

## The Decision Process

### Step 1: Frame the Decision

Ask the user:
- "What's the decision you're facing?"
- "What are the options?" (push for at least 3 — binary choices often hide a better third option)
- "What's the timeline? When must you decide?"
- "What makes this hard? What are you afraid of?"

### Step 2: Classify the Decision (Cynefin)

Read `frameworks/cynefin.md`. Determine the domain:
- **Clear**: Best practice exists → just follow it
- **Complicated**: Analyzable → gather expert input
- **Complex**: Unknowable in advance → design experiments
- **Chaotic**: Urgent → act now, analyze later

This determines how much analysis is appropriate.

### Step 3: Search for Relevant History

Pull prior thinking from the local vault. No Reflect MCP.
- `Bash: uv run scripts/semantic.py query "<decision topic>" --top 10` — **primary**: has the user thought about adjacent versions of this before? Reframe and retry if thin.
- `Grep(pattern: "<key terms>", path: "zk/")` — exact-match related notes for structural follow-up. Try both languages.
- `Grep(pattern: "<goal keyword>", path: "zk/gtd/")` AND `Grep(pattern: "<goal keyword>", path: "zk/wiki/")` — two separate calls; `Grep`'s `path` takes a single root, not a space-separated list. Checks which active goals (gtd) and which certified directions (wiki) are affected by this decision.

### Step 4: Apply Two Frameworks (Cross-Validation)

Based on the decision type, select the right pairing from `frameworks/cross-validation.md`:

| Decision Type | Primary Framework | Cross-Validation |
|--------------|-------------------|------------------|
| Career/direction | Ikigai | Regret Minimization |
| Risk assessment | Pre-Mortem | Inversion |
| Resource allocation | Pareto Principle | Eisenhower Matrix |
| Stuck/blocked | Immunity to Change | Five Whys |
| Build/invest | First Principles | Wardley Mapping |
| Binary choice | Dialectical Thinking | Second-Order Thinking |

Read the framework files. Apply them specifically (not generically).

### Step 5: Decision Matrix (if applicable)

For decisions with clear criteria:

| Criteria (weighted) | Option A | Option B | Option C |
|--------------------|----------|----------|----------|
| [Criterion 1] (weight) | Score | Score | Score |
| [Criterion 2] (weight) | Score | Score | Score |
| Weighted total | X | X | X |

### Step 6: The Hard Questions

After analysis, ask:
1. "If you woke up tomorrow and this was decided for you as [Option X], how would you feel?" (Gut check)
2. "What would you advise your best friend in this situation?" (Distance)
3. "What will you regret NOT doing in 10 years?" (Regret minimization)
4. "What are you most afraid of? Is that fear based on evidence?" (Fear audit)

### Step 7: Decision Record

Don't push for a decision. If the user is ready, capture it. If not, capture the analysis.

## Output

**File:** `zk/reflections/YYYY-MM-DD-decision-<slugified-topic>.md`

Note: Slugify the topic for the filename — lowercase, replace spaces with hyphens, remove special characters (e.g., "SF vs NYC job" → `sf-vs-nyc-job`). Keep the original topic text in the file content.

```markdown
# Decision Journal — YYYY-MM-DD
## Topic: [Decision description]

## Options Considered
1. [Option A]: [description]
2. [Option B]: [description]
3. [Option C]: [description]

## Domain Classification
[Cynefin domain] — [implication for approach]

## Framework Analysis
### [Framework 1 Name]
- Applied insight: [specific to this decision]

### [Framework 2 Name] (Cross-validation)
- Applied insight: [specific to this decision]
- Agreement/Tension with Framework 1: [what the tension reveals]

## Decision Matrix
[If applicable]

## Key Questions & Answers
- [Question]: [User's response or open]

## Related Notes
- [[Note Title]] — [relevance]

## Decision
[If made]: [The decision + rationale]
[If not made]: [What needs to happen before deciding]

## Review Date
[When to revisit this decision — 30/60/90 days]

## Session Meta
- User engagement: high / medium / low
- Surprise factor: yes / no
```

## Session Log

After writing the decision file, emit a session log:
1. `Bash: uv run scripts/session_log.py --type decision --duration <minutes>`
2. `Edit` the created file to populate sections from session data (agents dispatched, searches, questions, frameworks, anomalies). See `reflect.md` Session Log for the full fill-in guide. Leave empty sections with headers only. If the write fails, warn and continue.

## Wrap Up

The decision file in `zk/reflections/` is the durable session output. No write-back to daily notes — daily notes are the user's capture stream, read-only from the system's perspective. Tell the user the decision journal has been saved and where to find it.

- If **a write-back already exists**: Skip to avoid duplicates. Tell the user about the skip.
