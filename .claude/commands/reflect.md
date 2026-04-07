# Reflect

Your reflection system. Uses a two-step decision tree with `AskUserQuestion` for native scroll-and-select UI.

## Quick Start

If the user types `/reflect` with additional context, detect intent and route:
- **Reading intent** (mentions an article, URL, [[Note Title]], or "read/discuss"): skip the menu and go to Read & Discuss using their input as the article to read.
- **Meeting intent** (mentions "meeting", "standup", "1:1", or "meeting notes"): skip the menu and dispatch the **Meeting** agent directly.
- **Talk/transcript intent** (mentions "seminar", "talk", "transcript", "podcast", "video" or pastes a large block of transcript text): skip the menu and go to Read & Discuss, with Reader preprocessing the transcript format.
- **Reflection intent** (everything else, e.g., "/reflect I had a tough day"): skip the menu and go straight to Daily Reflection using their input as context.

## Step 1: Choose Mode

Use `AskUserQuestion` with these options:

| Option | Label | Description |
|--------|-------|-------------|
| 1 | **Reflect** | Think about what's happening — daily reflection, weekly review, or explore connections |
| 2 | **Plan** | Make decisions and set direction — goal review, decision journal, or energy audit |
| 3 | **Act** | Do something with your notes — compact, deep dive, or triage |
| 4 | **Read** | Read and discuss an article or note with structured reading lenses |
| 5 | **Learn** | Get recommendations or introspect to rebuild your self-model |

## Step 2: Choose Action

Based on Step 1, use a second `AskUserQuestion`:

### If Reflect:

| Option | Label | Description |
|--------|-------|-------------|
| 1 | **Daily Reflection** | Reflect on today's notes and recent thinking |
| 2 | **Weekly Review** | Energy + attention audit for the past week |
| 3 | **Explore** | Surface forgotten connections and open threads |

- **Daily Reflection:** Continue with the Daily Reflection flow below
- **Weekly Review:** Read and follow `.claude/commands/weekly.md`
- **Explore:** Read and follow `.claude/commands/explore.md`

### If Plan:

| Option | Label | Description |
|--------|-------|-------------|
| 1 | **Goal Review** | Check progress on goals — progressing, neglected, or shifted |
| 2 | **Decision Journal** | Structured decision-making with framework cross-validation |
| 3 | **Energy Audit** | Four-dimension energy assessment (physical, mental, emotional, social) |

- **Goal Review:** Read and follow `.claude/commands/review.md`
- **Decision Journal:** Read and follow `.claude/commands/decision.md`
- **Energy Audit:** Read and follow `.claude/commands/energy-audit.md`

### If Act:

| Option | Label | Description |
|--------|-------|-------------|
| 1 | **Curate Inbox** | Goal-aware triage of your Readwise inbox — score, route, and tag |
| 2 | **Compact Notes** | Find and merge redundant or overlapping notes |
| 3 | **Deep Dive** | Full briefing on a topic — notes + web research + resources + framework, 4 agents in parallel |
| 4 | **Note Triage** | Scan for compaction candidates across your notes |
| 5 | **Process Meeting** | Turn a work meeting transcript into structured notes with action items |

- **Curate Inbox:** Read and follow `.claude/commands/curate.md`
- **Compact Notes:** Dispatch to the **Curator** agent. Ask the user what topic or notes to compact. The Curator searches for related notes, proposes a merged version, and waits for approval before writing.
- **Deep Dive:** Ask the user for a topic, then dispatch **four agents in parallel**:
  1. **Researcher** — search all notes related to this topic (what you've already thought/written)
  2. **Scout** — search the web for recent articles, research, and developments on this topic
  3. **Librarian** — find curated resources to deepen understanding (books, papers, courses)
  4. **Thinker** — select and apply a relevant framework from `frameworks/`
  Once all four return, **Synthesizer** combines their outputs into a unified briefing: your existing thinking, external intelligence, curated resources, and a framework lens — all in one view. Present in Chinese for reading-intensive output. Before write-back (if any), dispatch **Reviewer** + **Challenger** in parallel to verify citation accuracy and Scout-sourced claims.
- **Note Triage:** Ask the user for 3-5 topic areas (or pull from `profile/identity.md` themes). Dispatch the **Researcher** to search each topic area in parallel. For each area, identify notes with overlapping content. Present a prioritized compaction plan: which notes to merge, estimated redundancy, and impact. The user picks which to compact, then dispatch to **Curator** for each approved merge.
- **Process Meeting:** Ask the user to paste or provide the meeting transcript. Dispatch the **Meeting** agent (Executive mode — action items, decisions, next steps). Present the structured output. Before saving, dispatch **Challenger** to check: are action items attributed correctly? Are any decisions ambiguous or missing owners? Ask the user if they want to save as a Reflect note — if yes, dispatch **Curator** to create it. For research talks or presentations, use Read instead — Reader handles transcript format with real analytical lenses.

### If Read:

| Option | Label | Description |
|--------|-------|-------------|
| 1 | **Read & Discuss** | Quick read + interactive discussion (default) |
| 2 | **Focused Read** | Pick 1-2 specific lenses to focus on |
| 3 | **Multi-Lens Read** | Read with all 4 lenses in parallel — full analysis |

- **Read & Discuss:** Ask for the article/note. Dispatch 1 Reader (Critical lens) + 1 Researcher (find related notes). Present the analysis, then enter interactive discussion mode. Before write-back, dispatch **Reviewer** + **Challenger** in parallel to verify accuracy, then create a standalone article note (see Article Note step below). This is the lightweight default — most reading sessions start here.
- **Focused Read:** Ask the user which article/note and which lens(es): Critical, Structural, Practical, or Dialectical. Dispatch 1-2 Reader instances with the chosen lenses. Reader automatically handles transcript format (video/podcast) with preprocessing before applying the lens. Before write-back, dispatch **Reviewer** + **Challenger** in parallel to verify accuracy, then create a standalone article note (see Article Note step below). Use when the user knows what angle they want.
- **Multi-Lens Read:** Ask the user which article or note to read. Then follow the Reading Hub flow below. Use for important articles worth deep multi-angle analysis.

#### Reading Hub Flow (Multi-Lens Read)

1. **Parallel dispatch — Phase 1 (gather + read):**
   - 2-4x **Reader** instances, each with a different lens. Always include Critical + Structural. Add by content type:
     - Opinion/journalism/essays → + Dialectical (find the tensions)
     - How-to/research/strategy → + Practical (extract takeaways)
     - Philosophy/argument/debate → + Dialectical + Practical
     - Video/podcast transcripts → Critical + Practical (Reader auto-preprocesses transcript format)
   - **Researcher** — find user's existing notes related to the topic
   - **Scout** (1-2 instances) — gather external context on the topic
   - **Thinker** — select and apply a relevant framework

2. **Convergence — Phase 2 (synthesize):**
   - **Synthesizer** combines all Reader briefs + Researcher + Scout + Thinker into a unified reading report
   - Present the report in Chinese (reading-intensive)

3. **Discussion — Phase 3 (interact):**
   - Enter interactive discussion mode
   - User and orchestrator discuss the article, guided by the multi-lens analysis
   - Dispatch additional Reader instances with specific lenses if the user wants to go deeper on an aspect

4. **Quality gate — Phase 4 (review + challenge):**
   - Before write-back, dispatch **Reviewer** + **Challenger** in parallel:
     - Reviewer checks: citation accuracy, grounding, honesty
     - Challenger checks: are we asking the right questions? What did we miss?
   - Fix any issues they surface before presenting the write-back

5. **Article note — Phase 5 (create standalone note):**
   - Before write-back, create a standalone article note in Reflect using `create_note` with:
     - Title: the article's title
     - Body: source URL, author, publication date, and key data points / takeaways from the reading analysis
     - Tags: `#article` and relevant topic tags
   - This note becomes the canonical reference for this article in the user's knowledge graph.

6. **Write-back — Phase 6 (with approval):**
   - Present proposed write-back to user for approval
   - Include [[backlinks]] to the article note created in Phase 5 and any related notes discussed
   - No provenance tag. Write-backs are alloy by default (see `protocols/epistemic-hygiene.md`). Topic tags are fine. The descriptive heading is the duplicate-detection signal, not a tag.

#### Article Note (all reading flows)

For **all** reading session types (Read & Discuss, Focused Read, Multi-Lens Read), create a standalone article note before the write-back:

1. Use `create_note` with the article's title as the note title
2. Include in the body: source URL, author, publication date, and key data points / takeaways
3. Tag with `#article` and relevant topic tags (e.g., `#ai`, `#career`, `#systems`)
4. Backlink to this note from the daily note write-back using [[Article Title]]

This ensures every article read has a permanent, searchable reference in Reflect's knowledge graph.

### If Learn:

| Option | Label | Description |
|--------|-------|-------------|
| 1 | **Recommend Resources** | Get reading/learning recommendations on a topic (Chinese summaries) |
| 2 | **Introspect** | Rebuild your self-model — discover identity, taste, curiosity, and directions from your notes |

- **Recommend Resources:** Dispatch to the **Librarian** agent. Ask the user what topic they want recommendations for. The Librarian searches existing notes for context, then recommends books, papers, articles, and other resources with Chinese summaries.
- **Introspect:** Read and follow `.claude/commands/introspect.md`

---

# Daily Reflection

Run a reflection session grounded in your Reflect notes and goals.

## Prerequisites

1. Check if `profile/identity.md` exists. If not, tell the user: "No profile found. Run `/introspect` first to build your self-model." and stop.
2. Read `profile/identity.md`. Check the `Last built:` date. If older than 7 days, warn: "Your profile is stale (built on [date]). Consider running `/introspect` to refresh. Continuing with current profile."

**Protocols used in this session:** `protocols/session-continuity.md` (connecting sessions), `protocols/integration.md` (insight → action), `protocols/contradiction-detection.md` (surfacing contradictions in Step 3), `protocols/epistemic-hygiene.md` (write-first nudge in warm-up, provenance tagging in write-back).

## Context Loading

1. **Read profile files:**
   - `profile/identity.md` — your self-model and intellectual taste
   - `profile/directions.md` — your goals and directions

2. **Read recent reflections** (last 3 files from `zk/reflections/` directory, sorted by date). If none exist, this is the first session — note that.

3. **Query MCP for fresh context:**
   - `get_daily_note(date: "<today>")` — what you've done today
   - `get_daily_note(date: "<yesterday>")` — what you did yesterday
   - `search_notes(query: "<a theme from meta-summary>", searchType: "vector", limit: 5, editedAfter: "<7 days ago>")` — recent activity related to your themes

## Coaching Session

Based on the loaded context, run an interactive reflection:

### 0. Continuity Check (if not the first session)
If a previous reflection exists in `zk/reflections/`, read the most recent one. Follow `protocols/session-continuity.md` — one brief callback, then move forward:
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

**File:** `zk/reflections/YYYY-MM-DD-reflection.md`
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

After writing the reflection file, check if today's daily note already contains a write-back from today's session. Detect by descriptive heading (the heading is the signal, not a tag). As a best-effort fallback, also check for the legacy `#ai-reflection` tag in case earlier in the day something pre-Phase-A wrote using the old convention.

- If **a write-back already exists**: Skip. Tell the user: "Already wrote to today's daily note earlier. Skipping duplicate write-back."

- If **no write-back exists yet**: Before presenting the write-back, dispatch **Reviewer** + **Challenger** in parallel to verify citation accuracy, framing, and tone. Fix any issues they surface. Then **ask the user for approval before writing.** Present the proposed write-back and wait for confirmation. Do not auto-write. **Write-backs are always in English**, even if the session was conducted in Chinese. The write-back should follow this format:
  ```
  ## [Descriptive Title]
  [2-3 sentence summary of key insights from today's reflection session]
  Related: [[Note Title 1]] [[Note Title 2]]
  ```
  **Title guidelines:** The heading must describe the session's core theme or question, not its source. Titles are in English (same as the write-back body). Good examples:
  - Topic-based: `Constraint creates meaning`
  - Question-based: `Why does unlimited freedom feel empty?`
  - Date+theme: `03/15 Energy dip and recovery patterns`
  - Insight-based: `Delegation as a trust signal`

  Never use generic titles like "AI Reflection" or "Daily Reflection Summary." The descriptive heading is load-bearing: it is the duplicate-detection signal and the only visible marker of a session write-back in the daily note. **No provenance tag.** Write-backs are alloy by default (see `protocols/epistemic-hygiene.md`). Topic tags are fine when they describe subject matter.

  Include [[backlinks]] to all notes referenced during the session so they appear in Reflect's backlink graph. Use today's date in YYYY-MM-DD format.

## Wrap Up

Tell the user the reflection has been saved.
