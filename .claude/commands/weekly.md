# Weekly Review

Run a structured weekly review covering the past 7 days. Deeper than daily reflection, lighter than a full goal review.

## Prerequisites

1. Check if `profile/identity.md` exists. If not: "Run `/introspect` first to build your self-model." Stop.
2. Check `Last built:` date. If >7 days stale, warn and continue.

## Context Loading

1. **Read profile files:** `profile/identity.md` + `profile/directions.md`

2. **Read all reflections from the past 7 days** from `zk/reflections/` directory.

3. **Read past 7 daily notes via MCP:**
   - `get_daily_note(date: "<today>")` through `get_daily_note(date: "<7 days ago>")`
   - Focus on themes, moods, accomplishments, and struggles

4. **Search for recent activity:**
   - `search_notes(query: "progress", editedAfter: "<7 days ago>", limit: 10)`
   - `search_notes(query: "进展", editedAfter: "<7 days ago>", limit: 10)`

## The Weekly Review Framework

### 1. Energy Audit
Map the week's energy:
- **High-energy days:** What were you doing? What made them good?
- **Low-energy days:** What drained you? Was it avoidable?
- **Pattern:** Is there a day-of-week or activity pattern?

### 2. Win Recognition
Identify 3 wins from the week, however small:
- What went well? (cite specific daily notes)
- What did you complete or make progress on?
- What did you learn?

### 3. Honest Assessment
For each goal category (#capacity, #learning, #identity, #energy):
- Did you make progress this week? Evidence?
- Did you avoid something? Why?
- What surprised you?

### 4. Attention Audit
Where did your attention actually go vs. where you wanted it to go?
- Apply Pareto: What 20% of activities produced 80% of your week's value?
- What consumed time but produced little?

### 5. Next Week's Intention
Based on the review:
- **One thing to continue:** [What's working]
- **One thing to start:** [What's been neglected]
- **One thing to stop:** [What's draining without value]

## Output

**File:** `zk/reflections/YYYY-MM-DD-weekly.md`

```markdown
# Weekly Review — YYYY-MM-DD (Week of MM/DD - MM/DD)

## Energy Map
- High: [days + activities]
- Low: [days + activities]
- Pattern: [observation]

## Wins
1. [Win] — [[Source Note]]
2. [Win] — [[Source Note]]
3. [Win] — [[Source Note]]

## Goal Progress
### #capacity
- [status + evidence]
### #learning
- [status + evidence]
### #identity
- [status + evidence]
### #energy
- [status + evidence]

## Attention Audit
- Time well spent: [activities]
- Time wasted: [activities]
- Pareto insight: [the 20% that mattered]

## Next Week
- Continue: [what's working]
- Start: [what's been neglected]
- Stop: [what's draining]

## Notes Referenced
[List of all [[Note Title]] links]

## Session Meta
- User engagement: high / medium / low
- Surprise factor: yes / no
```

## Write-Back

Check if today's daily note already contains a write-back from today's session. Detect by descriptive heading. As a best-effort fallback, also check for the legacy `#ai-reflection` tag in case earlier content was written with the old convention.

- If none: Before presenting the write-back, dispatch **Reviewer** + **Challenger** in parallel to verify citation accuracy, framing, and tone. Fix any issues they surface. **Write-backs are always in English.** Append weekly review summary using this format:
  ```
  ## [Descriptive Title]
  [2-3 sentence summary of the week's key insights and patterns]
  Related: [[Note Title 1]] [[Note Title 2]]
  ```
  **Title guidelines:** The heading must describe the week's core theme or pattern, not just "Weekly Review." Good examples:
  - `## This week: creation over consumption`
  - `## Week of 03/15: deep work recovery + energy rebalance`
  - `## Attention patterns shifted toward reading`

  Never use generic titles like "Weekly Review Summary." The descriptive heading is the duplicate-detection signal. **No provenance tag.** Write-backs are alloy by default (see `protocols/epistemic-hygiene.md`).

- If exists: skip.
