# Energy Audit

Deep assessment of where your energy goes — physical, mental, emotional, and social. Identifies energy drains and sources to optimize for sustainable high performance.

## Prerequisites

1. Read `index/meta-summary.md` for context.
2. Read `index/goals.md` for #energy category goals.

## Context Loading

1. **Read last 14 daily notes via MCP** to track energy patterns
2. **Search for energy-related notes:**
   - `search_notes(query: "energy tired exhausted", searchType: "vector", limit: 10)`
   - `search_notes(query: "累 疲惫 精力", limit: 10)`
   - `search_notes(query: "exercise health sleep", limit: 10)`
   - `search_notes(query: "运动 健康 睡眠", limit: 10)`

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

**File:** `reflections/YYYY-MM-DD-energy-audit.md`

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

Append energy audit summary to daily note with `#ai-reflection #energy-audit` tags.
