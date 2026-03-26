# Daily Reflection

Run a reflection session grounded in your Reflect notes and goals.

## Prerequisites

1. Check if `index/meta-summary.md` exists. If not, tell the user: "No reflection index found. Run `/project:index` first to build your profile." and stop.
2. Read `index/meta-summary.md`. Check the `Last built:` date. If older than 7 days, warn: "Your reflection index is stale (built on [date]). Consider running `/project:index` to refresh. Continuing with current index."

## Context Loading

1. **Read index files:**
   - `index/meta-summary.md` — your reflection context
   - `index/goals.md` — your goals and metrics

2. **Read recent reflections** (last 3 files from `reflections/` directory, sorted by date). If none exist, this is the first session — note that.

3. **Query MCP for fresh context:**
   - `get_daily_note(date: "<today>")` — what you've done today
   - `get_daily_note(date: "<yesterday>")` — what you did yesterday
   - `search_notes(query: "<a theme from meta-summary>", searchType: "vector", limit: 5, editedAfter: "<7 days ago>")` — recent activity related to your themes

## Coaching Session

Based on the loaded context, run an interactive reflection:

### 1. Warm-Up: Grounding Observation
Reference something specific from today's daily note or recent activity. Don't ask a question yet — just reflect back.
Example: "I see you wrote about [topic] today in your daily note, which connects to [[goal note title]]."

### 2. Reflective Questions (2-3, one at a time)
Use the Challenger's question taxonomy for depth:

| Question | Purpose |
|----------|---------|
| First question | **Mirror/Surface** — clarify what's on their mind |
| Second question | **Structural** — examine an assumption or connect to a goal |
| Third question | **Paradigmatic/Generative** — open new possibility or challenge a belief |

Each question should:
- Reference a specific note or goal by title in [[brackets]]
- Connect current activity to longer-term patterns or goals
- Be open-ended (not yes/no)
- Match the user's language (Chinese for Chinese goals)

### 3. Forgotten Connection (Semantic Discovery)
Use `search_notes(searchType: "vector")` to find a semantically related note the user may have forgotten.
- Search with a concept from the conversation, not just keywords
- Go back at least 3 months for genuine surprise
- Present as a provocation, not a summary:
  "This reminds me of something you wrote in [[old note title]] — '[brief quote]'. Do you see a connection?"

### 4. Framework Application (Optional)
If a clear pattern emerged during the conversation, briefly reference one framework from `frameworks/`:
- Don't explain the framework — apply it: "This feels like a [framework] situation because..."
- Read the framework file before referencing it

### 5. Close with Concrete Prompt
One specific, actionable next step tied to a goal. Not generic advice — something the user can do today or this week.

## Output

After the interactive session, write a reflection file:

**File:** `reflections/YYYY-MM-DD-reflection.md`
```markdown
# Reflection — YYYY-MM-DD

## Context
[Brief summary of what was discussed, with note citations]

## Key Insights
[Bullet points of insights from the conversation]

## Connections Made
[Notes or themes that were connected during the session]

## Next Action
[The concrete prompt or action suggested]

## Notes Referenced
[List of all notes cited during this session, as [[Note Title]] links]
```

## Write-Back to Reflect

After writing the reflection file, check if today's daily note already contains content tagged `#ai-reflection`.

- If **no existing AI content**: Use `append_to_daily_note` to add a brief summary:
  ```
  ## AI Reflection #ai-reflection
  [2-3 sentence summary of key insights from today's reflection session]
  ```
  Use today's date in YYYY-MM-DD format.

- If **AI content already exists**: Skip write-back to avoid duplicates. Tell the user: "Already wrote to today's daily note earlier — skipping duplicate write-back."

## Wrap Up

Tell the user the reflection has been saved.
