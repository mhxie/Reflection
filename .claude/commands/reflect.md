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
| 4 | **PRM Audit** | Audit relationship health and support system robustness (monthly) |

- **Goal Review:** Read and follow `.claude/commands/review.md`
- **Decision Journal:** Read and follow `.claude/commands/decision.md`
- **Energy Audit:** Read and follow `.claude/commands/energy-audit.md`
- **PRM Audit:** Read and follow `.claude/commands/prm.md`

### If Act:

| Option | Label | Description |
|--------|-------|-------------|
| 1 | **Curate Inbox** | Goal-aware triage of your Readwise inbox — score, route, and tag |
| 2 | **Compact Notes** | Find and merge redundant or overlapping notes |
| 3 | **Deep Dive** | Full briefing on a topic — notes + web research + resources + framework, 4 agents in parallel |
| 4 | **Note Triage** | Scan for compaction candidates across your notes |
| 5 | **Process Meeting** | Turn a work meeting transcript into structured notes with action items |

- **Curate Inbox:** Read and follow `.claude/commands/curate.md`
- **Compact Notes:** Ask the user what topic or notes to compact. Then run the snapshot-first flow (see `protocols/orchestrator.md` → Note Operations → Compact Notes):
  1. **Researcher** identifies related notes in `zk/` (semantic.py primary, Grep for structural).
  2. **Orchestrator snapshots each source** to `zk/cache/compact-<slug>-<n>.md` — local `cp` for files under `zk/`, `get_note()` fallback only for notes genuinely missing from the local mirror.
  3. Dispatch to **Curator** with `snapshot_paths: [...]` in the handoff. The Curator works exclusively from the snapshot files, runs the Content Preservation Checklist, and returns a draft.
  4. User approves each output note individually before Curator writes.
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

#### Prefetch Step (Readwise podcasts, videos, articles; applies to all three Read modes)

If the source is a Readwise podcast, video, or article (user provides a Readwise URL, `document_id`, or names a podcast), **cache the transcript once before dispatching any Reader**. Independent fetches across parallel Readers are the failure mode this step exists to avoid (same reasoning as the paper cache).

1. Resolve `document_id`. If the user gave a title, find it: `readwise reader-search-documents --query "<keywords>"` → pick the match.
2. Snapshot content: `readwise reader-get-document-details --document-id <id> | jq -r '.content' > zk/cache/rw-<id>.md`
3. Pass `cache_path: zk/cache/rw-<id>.md` to every Reader dispatch. The Reader agent knows this convention (see `.claude/agents/reader.md`, section "Readwise transcript cache").
4. For podcasts specifically: also pass the guest name (parsed from title) and host name (from the `author` field) in the dispatch prompt so Reader doesn't have to re-infer for citation.

- **Read & Discuss:** Ask for the article/note. Run the Prefetch Step above if it's a Readwise source. Dispatch 1 Reader (Critical lens) + 1 Researcher (find related notes). Present the analysis, then enter interactive discussion mode. Before write-back, dispatch **Reviewer** + **Challenger** in parallel to verify accuracy, then create a standalone article note (see Article Note step below). This is the lightweight default — most reading sessions start here.
- **Focused Read:** Ask the user which article/note and which lens(es): Critical, Structural, Practical, or Dialectical. Run the Prefetch Step above if it's a Readwise source. Dispatch 1-2 Reader instances with the chosen lenses. Reader automatically handles transcript format (video/podcast) with preprocessing before applying the lens. Before write-back, dispatch **Reviewer** + **Challenger** in parallel to verify accuracy, then create a standalone article note (see Article Note step below). Use when the user knows what angle they want.
- **Multi-Lens Read:** Ask the user which article or note to read. Run the Prefetch Step above if it's a Readwise source. Then follow the Reading Hub flow below. Use for important articles worth deep multi-angle analysis.

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
   - Before saving, dispatch **Reviewer** + **Challenger** in parallel:
     - Reviewer checks: citation accuracy, grounding, honesty
     - Challenger checks: are we asking the right questions? What did we miss?
   - Fix any issues they surface before writing the reflection file

5. **Save — Phase 5 (local reflection file):**
   - Write the reflection file to `zk/reflections/YYYY-MM-DD-reading-<slug>.md`
   - Include full source text under `### Full Text` (see source-text persistence rule in CLAUDE.md)
   - No write-back to daily notes. The reflection file is the durable output.

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

**Protocols used in this session:** `protocols/session-continuity.md` (connecting sessions), `protocols/epistemic-hygiene.md` (write-first nudge in warm-up, provenance tagging in write-back).

## Context Loading

1. **Read profile files:**
   - `profile/identity.md` — your self-model and intellectual taste
   - `profile/directions.md` — your goals and directions

2. **Read recent reflections** (last 3 files from `zk/reflections/` directory, sorted by date). If none exist, this is the first session — note that.

3. **Pull fresh context from the local mirror:**
   - Determine the **effective date**: if current local time is before 03:00, use yesterday's date; otherwise use today's. This is the user's day boundary (late-sleep rule). All subsequent "today" references in this session use the effective date.
   - `Read zk/daily-notes/<effective-date>.md` — what you've done today. If the file is missing, empty, or visibly truncated, **sync from Reflect first:** call `get_daily_note(date: "<effective-date>")` via MCP, then overwrite the local file. (Orchestrator only.)
   - If effective date differs from the calendar date (late-sleep active), also read `zk/daily-notes/<calendar-date>.md` if it exists — the user may have captured something after midnight.
   - `Read zk/daily-notes/<effective-date - 1>.md` — what you did the day before. Local only; no MCP fallback needed for a sync-complete day.
   - For recent activity related to your themes, run `Bash: uv run scripts/semantic.py query "<theme>" --after "<7 days ago, YYYY-MM-DD>" --top 5` first — this is the primary content lookup. For structural follow-up (exact strings, known tags), list files modified in the last 7 days with `Bash: find zk/daily-notes zk/reflections -type f -name "*.md" -mtime -7 2>/dev/null | sort`, then `Grep` the theme keyword across those paths.

## Coaching Session

Based on the loaded context, run an interactive reflection:

### 0. Continuity Check (if not the first session)
If a previous reflection exists in `zk/reflections/`, read the most recent one. Follow `protocols/session-continuity.md` — one brief callback, then move forward:
- If the previous session has a "Next Action" and it was from a different day: check in gently. Ask "Last time, you intended to [action]. How did that go?" Accept any answer without judgment -- missed actions are data points, not failures.
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
Use `Bash: uv run scripts/semantic.py query "<concept>" --before "<3 months ago, YYYY-MM-DD>" --top 10` to find a semantically related note the user may have forgotten. Reframe and retry if thin — Phase C removed the `search_notes` escape hatch.
- Search with a concept from the conversation, not just keywords
- Go back at least 3 months for genuine surprise
- Present as a provocation, not a summary:
  "This reminds me of something you wrote in [[old note title]] — '[brief quote]'. Do you see a connection?"

### 4. Framework Application (Optional — delegate to Thinker)
If a clear pattern emerged during the conversation, dispatch to the **Thinker** agent:
- The Thinker selects and applies a framework from `frameworks/` using its decision tree
- Present the Thinker's insight as an "orient" perspective: "Looking at this through [framework]..."
- This is the Orient phase — contextualizing raw observations against mental models

### 5. Support System Pulse (brief, every session)
A lightweight check-in on the user's interpersonal interactions and support system health. Not a deep conversation topic; a structured micro-review logged for longitudinal tracking.

**Data gathering:** Scan today's daily note for people mentioned and interaction types. If the user brought up relationships during the session, use that context too.

**Ask one question** (rotate across sessions):
- "今天和谁有过有意义的互动？是哪种类型的？"（mapping interactions）
- "这周有没有在核心圈之外和谁有过连接？"（weak tie check）
- "最近有没有某段关系让你觉得能量被消耗？"（boundary check）

**Observe and log** (silently, for the output file):

| Indicator | What to track |
|-----------|---------------|
| Interactions today | Names, relationship type, Dunbar layer (DL0-DL5, per PRM template) |
| Support type exchanged | Emotional / Instrumental / Informational / Appraisal (House model) |
| Diversity flags | All same domain? Any cross-industry/cross-generational? Any new connections this week? |
| Concentration warning | Multiple support types pointing to same person? |
| Energy direction | Net giver or receiver today? Any draining interactions? |

**Offer one observation or suggestion** based on patterns:
- If interactions are concentrated: note it without judgment, suggest one low-cost diversification action
- If a new connection appeared: acknowledge it
- If no meaningful interactions logged: flag gently as a data point, not a problem
- Compare against prior sessions' logs if available for trend detection

Keep this step under 2 minutes of conversation time. The value is in the longitudinal record, not the daily depth.

### 6. Close with Concrete Prompt
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

## Support System Log
| Person | Dunbar Layer | Support Type | Domain | Direction |
|--------|-------------|-------------|--------|-----------|
| [Name] | DL0-DL5 | emotional/instrumental/informational/appraisal | work/family/friend/community | gave/received/mutual |

- Diversity score: [how many distinct domains represented today]
- Concentration flag: [any person carrying 3+ support types?]
- New connection this week: yes / no
- Observation: [one-line pattern note for longitudinal tracking]

## Session Meta
- User engagement: high / medium / low
- Questions that landed: [which questions got thoughtful responses]
- Surprise factor: yes / no [did we surface something genuinely new?]
```

## Session Log

After writing the reflection file, emit a session log. Two steps:

**Step 1: Create skeleton.**
```
Bash: uv run scripts/session_log.py --type reflection --duration <minutes>
```
The script prints the file path (e.g., `zk/sessions/2026-04-11-reflection.md`). It handles the late-sleep date rule and collision auto-increment.

**Step 2: Fill the skeleton.**
Use `Edit` to populate each section of the skeleton from data you accumulated during the session:

- **Agents Dispatched:** One row per agent you dispatched. Include agent name, task summary, success/failure, and approximate turns.
- **Search Log:** Every `semantic.py query` and notable `Grep` you or agents issued. Mark whether results were useful (yes/no).
- **Questions & Engagement:** Each question you asked the user. Note depth level (surface/structural/paradigmatic) and whether it landed (got substantive response).
- **Frameworks Applied:** Any framework the Thinker applied. Include fit score if available.
- **Continuity:** Which previous session you referenced (from step 0), and the seed/next-action from step 5.
- **Decisions & Branches:** Non-obvious routing decisions (e.g., "skipped framework; user in a rush").
- **Anomalies:** MCP failures, empty searches, user course corrections, degraded mode.
- **Harness Assumptions Exercised:** Any assumption from `protocols/harness-assumptions.md` that was load-bearing (e.g., "Profile stale >7d warning triggered").

If a section has no data, leave the table headers but add no rows. Do not invent data. If the write fails, warn and continue; session logs never block a session.

## Wrap Up

The reflection file in `zk/reflections/` is the durable session output. No write-back to daily notes — the user's daily note is their capture stream, read-only from the system's perspective. Tell the user the reflection has been saved and where to find it.
