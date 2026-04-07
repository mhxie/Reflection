# Energy Audit

Deep assessment of where your energy goes — physical, mental, emotional, and social. Identifies energy drains and sources to optimize for sustainable high performance.

## Prerequisites

1. Read `profile/identity.md` for context.
2. Read `profile/directions.md` for #energy category goals.

## Context Loading

1. **Read the last 14 daily notes from the local mirror** to track energy patterns: `Read zk/daily-notes/<today>.md` back through `Read zk/daily-notes/<14-days-ago>.md` (one `Read` per date). Fall through to `get_daily_note(date)` only for any specific date missing from the local mirror.
2. **Search for energy-related notes:**
   - `Grep(pattern: "累|疲惫|精力", path: "zk/")` — Chinese exhaustion markers (local, exact).
   - `Grep(pattern: "运动|健康|睡眠", path: "zk/")` — Chinese health markers (local, exact).
   - `Grep(pattern: "exercise|health|sleep", path: "zk/")` — English health markers (local, exact).
   - `Bash: scripts/semantic.py query "tired exhausted drained" --top 10` — semantic search for energy *states* that may not use literal "tired/exhausted" language. This is the documented exception where semantic search leads. In stub mode the script lexical-falls-through with a stderr warning; escalate to `search_notes(query: "energy tired exhausted", searchType: "vector", limit: 10)` only when the stub misses a genuinely affective concept.

## The Four Energy Dimensions

### 1. Physical Energy
- Sleep quality and quantity
- Exercise frequency
- Nutrition patterns
- Illness or physical complaints
- Weight/fitness trajectory

### 2. Mental Energy
- Focus and concentration quality
- Learning vs. routine work ratio
- Cognitive load from context-switching
- Creative output vs. administrative tasks

### 3. Emotional Energy
- Relationship quality (energizing vs. draining interactions)
- Stress sources
- Joy sources
- Unresolved conflicts or anxieties

### 4. Social Energy
- Introvert/extrovert battery level
- Quality of professional relationships
- Community connection
- Isolation signals

## Energy Matrix

Present findings as:

| Dimension | Sources (+) | Drains (-) | Net Trend |
|-----------|------------|------------|-----------|
| Physical | [what energizes] | [what drains] | ↑ ↓ → |
| Mental | [what energizes] | [what drains] | ↑ ↓ → |
| Emotional | [what energizes] | [what drains] | ↑ ↓ → |
| Social | [what energizes] | [what drains] | ↑ ↓ → |

## Coaching Questions

1. "Which dimension is most depleted right now?"
2. "What's one energy drain you could eliminate this week?"
3. "What energizes you that you're not doing enough of?"
4. "Is any goal consuming disproportionate energy relative to its importance?" (Apply Pareto)

## Output

**File:** `zk/reflections/YYYY-MM-DD-energy-audit.md`

```markdown
# Energy Audit — YYYY-MM-DD

## Energy Matrix
[Matrix table from above]

## Key Findings
- [Finding 1 with evidence from notes]
- [Finding 2 with evidence from notes]

## Energy Drains to Address
1. [Drain] — Impact: high/medium/low — Action: [specific]
2. [Drain] — Impact: high/medium/low — Action: [specific]

## Energy Sources to Protect
1. [Source] — currently at risk because [reason]
2. [Source] — underutilized, could increase by [how]

## Recommendations
- This week: [one small change]
- This month: [one structural change]

## Notes Referenced
[All [[Note Title]] links]

## Session Meta
- User engagement: high / medium / low
- Surprise factor: yes / no
```

## Write-Back

Check if today's daily note already contains a write-back from today's session. Detect by descriptive heading. As a best-effort fallback, also check for the legacy `#ai-reflection` tag in case earlier content was written with the old convention.

- If none: Before presenting the write-back, dispatch **Reviewer** + **Challenger** in parallel to verify citation accuracy, framing, and tone. Fix any issues they surface. **Write-backs are always in English.** Append energy audit summary using this format:
  ```
  ## [Descriptive Title] #energy-audit
  [2-3 sentence summary of energy findings and one actionable change]
  Related: [[Note Title 1]] [[Note Title 2]]
  ```
  **Title guidelines:** The heading must describe the audit's core finding, not just "Energy Audit." Good examples:
  - `## Physical strong but socially drained #energy-audit`
  - `## Energy dip: mental fatigue from context-switching #energy-audit`
  - `## Sleep deficit dragging overall energy #energy-audit`

  Never use generic titles like "Energy Audit Summary." The descriptive heading is the duplicate-detection signal. The `#energy-audit` topic tag is allowed because it marks subject matter, not provenance. **No provenance tag** (`#ai-reflection` is retired). Write-backs are alloy by default (see `protocols/epistemic-hygiene.md`).

- If exists: skip.
