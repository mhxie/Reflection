# Decision Journal

Structured decision-making session for important choices. Uses thinking frameworks to analyze a decision from multiple angles.

## Trigger

User says something like:
- "I need to decide..."
- "Should I..."
- "Help me think through..."
- "I'm torn between..."

## Prerequisites

1. Read `index/meta-summary.md` and `index/goals.md` for context.
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

Query MCP for prior thinking:
- `search_notes(query: "<decision topic>", searchType: "vector", limit: 10)` — has the user thought about this before?
- `search_notes(query: "<key terms>", limit: 10)` — related notes
- Check if goals are affected by this decision

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

**File:** `reflections/YYYY-MM-DD-decision-<topic>.md`

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
```

## Write-Back

Append decision summary to daily note with `#ai-reflection #decision` tags.
