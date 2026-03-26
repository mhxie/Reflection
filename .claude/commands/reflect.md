# Reflect

Your reflection system. Choose a session type to begin.

## Session Menu

Present this menu to the user and wait for their choice:

```
What would you like to do?

1) Daily Reflection — reflect on today's notes and recent thinking
2) Goal Review — check progress on goals (progressing/neglected/shifted)
3) Weekly Review — energy + attention audit for the past week
4) Decision Journal — structured decision-making with frameworks
5) Explore — surface forgotten connections and open threads
6) Energy Audit — four-dimension energy assessment
7) Build Index — rebuild your reflection context (run first if new)
```

Based on the user's choice:
- **1 (Daily Reflection):** Continue with the Daily Reflection flow below
- **2 (Goal Review):** Read and follow `.claude/commands/review.md`
- **3 (Weekly Review):** Read and follow `.claude/commands/weekly.md`
- **4 (Decision Journal):** Read and follow `.claude/commands/decision.md`
- **5 (Explore):** Read and follow `.claude/commands/explore.md`
- **6 (Energy Audit):** Read and follow `.claude/commands/energy-audit.md`
- **7 (Build Index):** Read and follow `.claude/commands/index.md`

If the user just types `/reflect` with additional context (e.g., "/reflect I had a tough day"), skip the menu and go straight to Daily Reflection using their input as context.

---

# Daily Reflection

Run a reflection session grounded in your Reflect notes and goals.

## Prerequisites

1. Check if `index/meta-summary.md` exists. If not, tell the user: "No reflection index found. Run `/project:index` first to build your profile." and stop.
2. Read `index/meta-summary.md`. Check the `Last built:` date. If older than 7 days, warn: "Your reflection index is stale (built on [date]). Consider running `/project:index` to refresh. Continuing with current index."

**Protocols used in this session:** `protocols/session-continuity.md` (connecting sessions), `protocols/integration.md` (insight → action), `protocols/contradiction-detection.md` (surfacing contradictions in Step 3).

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

### 0. Continuity Check (if not the first session)
If a previous reflection exists in `reflections/`, read the most recent one. Follow `protocols/session-continuity.md` — one brief callback, then move forward:
- If the previous session has a "Next Action" and it was from a **different day**: check in gently per `protocols/integration.md`.
- If the previous session was **today**: skip the check-in (don't nag on multiple sessions per day).
- If there was no prior action: skip this step entirely.

### 1. Warm-Up: Adaptive Opening
Choose opening style based on what you find in the daily note:

| What you find | Opening style |
|---|---|
| User wrote something specific today | Reflect it back: "I see you wrote about [X]..." |
| User had a big day (many entries) | Acknowledge the energy: "Busy day — what stood out most?" |
| User wrote very little or nothing | Go to yesterday or last session: "Last time we talked about [X]. How has that been sitting?" |
| A contradiction with a past note | Lead with curiosity: "Something interesting — in [[Old Note]] you said X, but today..." |
| A neglected goal is relevant | Gentle nudge: "I notice [[Goal]] hasn't come up recently..." |

Don't ask a question yet in the warm-up — just ground the conversation.

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

### 4. Framework Application (Optional — delegate to Thinker)
If a clear pattern emerged during the conversation, dispatch to the **Thinker** agent:
- The Thinker selects and applies a framework from `frameworks/` using its decision tree
- Present the Thinker's insight as an "orient" perspective: "Looking at this through [framework]..."
- This is the Orient phase — contextualizing raw observations against mental models

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

## Session Meta
- User engagement: high / medium / low
- Questions that landed: [which questions got thoughtful responses]
- Surprise factor: yes / no [did we surface something genuinely new?]
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
