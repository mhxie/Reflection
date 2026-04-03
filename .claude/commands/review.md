# Goal Review

Review progress on near/mid/long-term goals. Surface what's progressing, what's neglected, and what has shifted.

## Prerequisites

1. Check if `index/meta-summary.md` exists. If not, tell the user: "No reflection index found. Run `/project:index` first to build your profile." and stop.
2. Read `index/meta-summary.md`. Check the `Last built:` date. If older than 7 days, warn: "Your reflection index is stale (built on [date]). Consider running `/project:index` to refresh."

## Context Loading

1. **Read index files:**
   - `index/meta-summary.md` — reflection context
   - `index/goals.md` — goals with categories and metrics

2. **Read all reflections from the last 30 days** from the `reflections/` directory. If none exist, note this is the first review.

3. **Query MCP for goal-related updates:**
   - `search_notes(query: "目标", editedAfter: "<30 days ago>", limit: 15)` — recently edited Chinese goal notes
   - `search_notes(query: "goal", editedAfter: "<30 days ago>", limit: 15)` — recently edited English goal notes
   - `search_notes(query: "progress", editedAfter: "<30 days ago>", limit: 10)` — progress-related notes
   - `get_daily_note(date: "<today>")` — today's context

4. **Read key goal notes** via `get_note()` for the most relevant results to get full current content.

## Analysis

For each goal category (#capacity, #learning, #identity, #energy — or whatever categories exist in goals.md):

### Progressing
Which goals have evidence of recent activity? Look for:
- Goal notes edited recently
- Daily notes mentioning goal-related topics
- Reflections that referenced these goals

### Neglected
Which goals appear in goals.md but have NO recent activity? Look for:
- Goals not mentioned in any recent reflection
- Goal notes not edited in 30+ days
- Topics absent from daily notes

### Shifted
Have the user's priorities changed? Look for:
- New topics appearing frequently in recent notes that aren't in goals.md
- Goals that were active 3 months ago but have gone quiet
- Contradictions between stated goals and recent behavior

## Review Output

Present the review interactively, category by category. For each finding, cite the specific source note.

After discussing, write a review file:

**File:** `reflections/YYYY-MM-DD-review.md`
```markdown
# Goal Review — YYYY-MM-DD

## Summary
[One paragraph: overall assessment of goal progress since last review]

## By Category

### #capacity (Financial / Resources)
- **Progressing:** [goals with evidence] — Source: [[Note Title]]
- **Neglected:** [goals with no recent activity] — Source: [[Note Title]]
- **Shifted:** [any changes in direction]

### #learning (Skills / Knowledge)
- **Progressing:** ...
- **Neglected:** ...
- **Shifted:** ...

### #identity (Career / Role)
- **Progressing:** ...
- **Neglected:** ...
- **Shifted:** ...

### #energy (Health / Relationships / Wellbeing)
- **Progressing:** ...
- **Neglected:** ...
- **Shifted:** ...

## Emerging Interests
[Topics appearing in recent notes that aren't captured in any goal — potential new directions]

## Suggested Experiments
[2-3 concrete actions for the next review period, tied to specific neglected goals or emerging interests]

## Notes Referenced
[List of all notes cited during this review]
```

## Write-Back to Reflect

After writing the review file, check if today's daily note already contains `#ai-reflection` content.

- If **no existing AI content**: Before presenting the write-back, dispatch **Reviewer** + **Challenger** in parallel to verify citation accuracy, framing, and tone. Fix any issues they surface. **Write-backs are always in English.** Use `append_to_daily_note` to add:
  ```
  ## [Descriptive Title] #ai-reflection
  [3-4 sentence summary: what's progressing, what's neglected, top suggested experiment]
  ```
  The title should describe the review's findings, not the session type. E.g., `Learning goals stalled, energy direction shifted` or `Q2 goals: shipping beats planning`. Never use generic titles like "Goal Review Summary."

- If **AI content already exists**: Skip write-back. Tell the user about the skip.

## Trend Analysis (if prior reviews exist)

If previous review files exist in `reflections/`, compare:
- Which goals were "Neglected" last time — are they still neglected? (Chronic neglect signal)
- Which goals were "Progressing" — have they continued? (Momentum signal)
- Which "Suggested Experiments" from last review were actually done? (Follow-through signal)

Present trend as:
| Goal | Last Review | This Review | Trend |
|------|------------|-------------|-------|
| [goal] | Progressing | Progressing | Sustained momentum |
| [goal] | Neglected | Neglected | Chronic neglect — needs decision |
| [goal] | Progressing | Neglected | Lost momentum — investigate |

## Wrap Up

Tell the user the review has been saved. Suggest:
- `/project:reflect` for daily check-ins between reviews
- `/project:weekly` for lighter weekly check-ins
- `/project:decision` if any goal needs a decision about continuing/stopping
