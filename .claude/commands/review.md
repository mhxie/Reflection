# Goal Review

Review progress on near/mid/long-term goals. Surface what's progressing, what's neglected, and what has shifted.

## Prerequisites

1. Check if `profile/identity.md` exists. If not, tell the user: "No profile found. Run `/introspect` first to build your self-model." and stop.
2. Read `profile/identity.md`. Check the `Last built:` date. If older than 7 days, warn: "Your profile is stale (built on [date]). Consider running `/introspect` to refresh."

## Context Loading

1. **Read profile files:**
   - `profile/identity.md` — reflection context
   - `profile/directions.md` — goals with categories and metrics

2. **Read all reflections from the last 30 days** from the `zk/reflections/` directory. If none exist, note this is the first review.

3. **Pull goal-related updates from the local mirror, bounded to the last 30 days.** Do NOT issue an unbounded `Grep(path: "zk/")` — the old `editedAfter`-bounded MCP query was recency-scoped on purpose, and an unbounded grep will pull stale historical matches that skew the review. Use `find -print0 | xargs -0 grep` so recency actually binds:
   - `Bash: find zk/daily-notes zk/reflections zk/gtd zk/wiki -type f -name "*.md" -mtime -30 -print0 2>/dev/null | xargs -0 grep -HnE "目标|goal|progress|进展|milestone" 2>/dev/null` — recency-bounded goal and progress mentions across both languages in one pass. Safe with an empty working set (xargs does nothing if stdin is empty).
   - `Read zk/daily-notes/<today>.md` for today's context (fall through to `get_daily_note(date: "<today>")` only if today's file hasn't synced yet).

4. **Read key goal notes in full** by `Read`-ing the matching files directly. The files are already on disk — no `get_note()` needed except for notes genuinely missing from the local mirror.

## Analysis

For each goal category (#capacity, #learning, #identity, #energy — or whatever categories exist in directions.md):

### Progressing
Which goals have evidence of recent activity? Look for:
- Goal notes edited recently
- Daily notes mentioning goal-related topics
- Reflections that referenced these goals

### Neglected
Which goals appear in directions.md but have NO recent activity? Look for:
- Goals not mentioned in any recent reflection
- Goal notes not edited in 30+ days
- Topics absent from daily notes

### Shifted
Have the user's priorities changed? Look for:
- New topics appearing frequently in recent notes that aren't in directions.md
- Goals that were active 3 months ago but have gone quiet
- Contradictions between stated goals and recent behavior

## Review Output

Present the review interactively, category by category. For each finding, cite the specific source note.

After discussing, write a review file:

**File:** `zk/reflections/YYYY-MM-DD-review.md`
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

After writing the review file, check if today's daily note already contains a write-back from today's session. Detect by descriptive heading. As a best-effort fallback, also check for the legacy `#ai-reflection` tag in case earlier content was written with the old convention.

- If **no write-back exists yet**: Before presenting the write-back, dispatch **Reviewer** + **Challenger** in parallel to verify citation accuracy, framing, and tone. Fix any issues they surface. **Write-backs are always in English.** Use `append_to_daily_note` to add:
  ```
  ## [Descriptive Title]
  [3-4 sentence summary: what's progressing, what's neglected, top suggested experiment]
  ```
  The title should describe the review's findings, not the session type. E.g., `Learning goals stalled, energy direction shifted` or `Q2 goals: shipping beats planning`. Never use generic titles like "Goal Review Summary." **No provenance tag.** Write-backs are alloy by default (see `protocols/epistemic-hygiene.md`); the descriptive heading is the duplicate-detection signal.

- If **a write-back already exists**: Skip. Tell the user about the skip.

## Trend Analysis (if prior reviews exist)

If previous review files exist in `zk/reflections/`, compare:
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
