# Reflect

Your reflection system. Uses a two-step decision tree with `AskUserQuestion` for native scroll-and-select UI.

## Routing & Dispatch

### Intent Routing (when user types `/hi <context>`)

Routing rules live in `harness/intents.toml` (canonical). Read that file at session start to know the dispatch shape per intent: trigger phrases (`patterns`), the dispatch sub-mode (`mode`), the agents the orchestrator is expected to dispatch (`agents`), and the matching priority. Do not duplicate those fields here; when adding or changing a routing rule, edit the TOML and let this file reference it.

Each intent's `mode` field maps to a sub-mode procedure documented below (e.g., `capture-fast-path` → "Capture Fast Path"; `read-and-discuss` and `transcript-read` → the Read & Discuss sub-flow under "If Read"; `meeting-process` → the Meeting flow under "If Act" / "Process Meeting"; `daily-reflection` → the "Daily Reflection" section that begins after the Step menus). Detect the intent from `<context>`, skip the Step 1 menu, and route directly into the matching sub-mode. If no `<context>` is given, fall through to the Weekly Cue Check, then the Step 1 menu.

### Always-on Routing Announcement

Before any agent dispatch under `/hi`, surface a one-line acknowledgment of the routing decision so the user can see the matched intent and the dispatch chain. This is in-band observability: the orchestrator never opts in or out, the user never has to ask. Drift becomes visible because the user reads the announcement on every turn.

Format: `Routing as intents.<name> → <comma-separated agent list>` (use the `agents` list from the matched row in `harness/intents.toml`).

Fallback case. The `intents.reflection` row (priority 0, empty `patterns`) is the catch-all. When it matches because nothing more specific did, mark that explicitly so a "deliberate reflection" (the user said "let's reflect") and a "nothing matched, falling back to reflection" look different to the user:

`No specific intent matched; routing as default reflection → <agents from intents.reflection>`

(Read the agent list from `intents.reflection.agents` — never hardcode it here, or this file drifts from the canonical TOML.)

When the user explicitly invoked the reflection mode (e.g., chose Reflect from the Step 1 menu, or said "let's reflect"), use the standard form (`Routing as intents.reflection → ...`) instead. The fallback marker is only for the implicit-match case.

Semantic match. Some intents fire on user input shape rather than literal phrase — e.g., a date-prefixed factual narrative without analytical question (`/hi 5/4 早上去了 X, 中午吃了 Y`) routes to `intents.capture` even though no literal pattern matches. When the orchestrator decides on shape rather than phrase, the announcement still uses the matched intent name; the matching logic is documented in the per-intent sub-mode section below.

### Capture Fast Path

When the user's input is "just write this down" (factual, no reflection sought), do not run the coaching flow. Dispatch the Scribe directly with the right operation:

| Content shape | Scribe operation | Target tier |
|---|---|---|
| Date-stamped narrative for a day | `daily_note` | under `$OV/daily-notes/` |
| Restaurant + score / 必点 | `dining_row` | the user's dining-log file under `$OV/travel/` |
| New person mentioned with bio context, file does not exist | `people_stub` | under `$OV/archive/people/` |
| Action item with deadline / area | `gtd_entry` (`add`) | most recently modified file under `$OV/gtd/` |
| Anything else "just save this" | `generic` | orchestrator picks an appropriate path under `$OV/drafts/` |

Resolve the exact target file path at dispatch time by inspecting the target directory for the user's existing structural conventions (subdirectory tree, filename style). Do not assume a layout; the user owns these conventions and they are private to `$OV/`. Confirm with the user once when multiple plausible targets exist; if the path is obvious from a quick directory listing, just dispatch.

### Effective Date

Resolve inline before dispatch:
- `<effective-date>`: if local time < 03:00, use yesterday's calendar date; else today.

Daily notes are user-authored under `$OV/daily-notes/`. The system reads them as-is; nothing pulls or mirrors them from anywhere else. The exact subdirectory layout and filename pattern are user-private; resolve them at runtime by listing the target directory. **Exception (cloud-native mode):** when the user provides daily-note-style narrative through `/hi <args>` or chat, the orchestrator dispatches the `scribe` agent to record it verbatim before writing the reflection file. See "Pre-Output: Raw Capture" below. The user is still the author; the scribe is the typewriter.

### Weekly Cue Check (before Step 1 menu, only when no `<context>` routed away)

```
# macOS/BSD `date -j -f`. Linux: replace with `date -d "$latest_date" +%s`
Bash: latest_weekly=$(ls "$OV"/reflections/*-weekly.md 2>/dev/null | sort | tail -1)
if [ -n "$latest_weekly" ]; then
  latest_date=$(basename "$latest_weekly" | cut -c1-10)
  days_since=$(( ($(date +%s) - $(date -j -f '%Y-%m-%d' "$latest_date" +%s)) / 86400 ))
else
  days_since=999  # no weekly ever; treat as far past hard floor
fi
echo "days_since=$days_since latest=$latest_weekly"
```

| Condition | Branch | Action |
|---|---|---|
| `days_since` >10, or no weekly ever | Hard floor | "上次 weekly 是 N 天前 (or 还没跑过). 这周已经积累了 Apple Health / 信号 / 健康 cadence checks 没补齐. 建议先跑 `/weekly`. 现在跑吗?" Yes: route to `weekly.md`. No: proceed to Step 1. |
| `days_since` >6 AND today is Sun or Mon | Soft cue | "提示: 上次 weekly 是 N 天前. 想现在跑 `/weekly` 把这周补齐吗?" Yes: route to `weekly.md`. No: proceed to Step 1. |
| Otherwise | Fresh | Skip silently. Proceed to Step 1. |

Surface at most once per `/hi` invocation. Do not nag. This is the only non-user-typed reason the orchestrator may suggest a different mode than the user implicitly chose.

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
  1. **Researcher** identifies related notes in `$OV/` (semantic.py primary, Grep for structural).
  2. **Orchestrator snapshots each source** to `$OV/cache/compact-<slug>-<n>.md` (local `cp`).
  3. Dispatch to **Curator** with `snapshot_paths: [...]` in the handoff. The Curator works exclusively from the snapshot files, runs the Content Preservation Checklist, and returns a draft.
  4. User approves each output note individually; the orchestrator writes the file after approval.
- **Deep Dive:** Ask the user for a topic, then dispatch **four agents in parallel**:
  1. **Researcher** — search all notes related to this topic (what you've already thought/written)
  2. **Scout** — search the web for recent articles, research, and developments on this topic
  3. **Librarian** — find curated resources to deepen understanding (books, papers, courses)
  4. **Thinker** — select and apply a relevant framework from `frameworks/`
  Once all four return, **Synthesizer** combines their outputs into a unified briefing: your existing thinking, external intelligence, curated resources, and a framework lens — all in one view. Present in Chinese for reading-intensive output. Before write-back (if any), dispatch **Reviewer** + **Challenger** in parallel to verify citation accuracy and Scout-sourced claims.
- **Note Triage:** Ask the user for 3-5 topic areas (or pull from `profile/identity.md` themes). Dispatch the **Researcher** to search each topic area in parallel. For each area, identify notes with overlapping content. Present a prioritized compaction plan: which notes to merge, estimated redundancy, and impact. The user picks which to compact, then dispatch to **Curator** for each approved merge.
- **Process Meeting:** Ask the user to paste or provide the meeting transcript. Dispatch the **Meeting** agent (Executive mode — action items, decisions, next steps). Present the structured output. Before saving, dispatch **Challenger** to check: are action items attributed correctly? Are any decisions ambiguous or missing owners? Ask the user if they want to save as a local note — if yes, dispatch **Curator** to draft it and the orchestrator writes after approval. For research talks or presentations, use Read instead — Reader handles transcript format with real analytical lenses.

### If Read:

| Option | Label | Description |
|--------|-------|-------------|
| 1 | **Read & Discuss** | Quick read + interactive discussion (default) |
| 2 | **Focused Read** | Pick 1-2 specific lenses to focus on |
| 3 | **Multi-Lens Read** | Read with all 4 lenses in parallel — full analysis |

#### Prefetch Step (Readwise podcasts, videos, articles; applies to all three Read modes)

If the source is a Readwise podcast, video, or article (user provides a Readwise URL, `document_id`, or names a podcast), **cache the transcript once before dispatching any Reader**. Independent fetches across parallel Readers are the failure mode this step exists to avoid (same reasoning as the paper cache).

1. Resolve `document_id`. If the user gave a title, find it: `readwise reader-search-documents --query "<keywords>"` → pick the match.
2. Snapshot content: `readwise reader-get-document-details --document-id <id> | jq -r '.content' > $OV/cache/rw-<id>.md`
3. Pass `cache_path: $OV/cache/rw-<id>.md` to every Reader dispatch. The Reader agent knows this convention (see `.claude/agents/reader.md`, section "Readwise transcript cache").
4. For podcasts specifically: also pass the guest name (parsed from title) and host name (from the `author` field) in the dispatch prompt so Reader doesn't have to re-infer for citation.

#### Backup to Readwise (final step in every Read mode)

After the reflection file is saved, fire one `readwise reader-create-document` call as a last-resort backup of the source. The reflection file in `$OV/reflections/` remains the durable artifact; this is just so the source itself is preserved if its origin URL ever rots.

**Skip conditions (do NOT call the CLI):**
- Input was a Readwise URL or `document_id` (already in Readwise; the Prefetch Step handled it).
- Input was a local `[[Note Title]]` (no source URL exists).
- Input was a transcript paste with no accompanying URL (nothing to back up).
- `readwise` CLI is not installed in the environment (`command -v readwise` returns nothing). Backup is best-effort; absence of the CLI is not a session error.

**When it runs (orchestrator, not a separate agent):**

```bash
readwise reader-create-document \
  --url "<canonical-source-url>" \
  --tags "<comma-list>" \
  --category "<article|pdf|video|podcast>"
```

- `--url`: canonical source URL. For arXiv use the abs page (`/abs/<id>`), not the PDF URL.
- `--tags`: 3-5 tags derived from the paper/article topic. Orchestrator picks them; no user prompt.
- `--category`: default `article`; use `pdf` for arXiv/PDF papers, `video` or `podcast` for transcripts.

Print the resulting Readwise URL or `document_id` to the user as a one-liner confirmation. Do not pre-check for duplicates: if Readwise re-creates a doc, the second `document_id` is fine. Do not loop on errors; if the call fails (network, auth), report the error and continue, since the reflection file is already saved.

- **Read & Discuss:** Ask for the article/note. Run the Prefetch Step above if it's a Readwise source. Dispatch 1 Reader (Critical lens) + 1 Researcher (find related notes). Present the analysis, then enter interactive discussion mode. Before write-back, dispatch **Reviewer** + **Challenger** in parallel to verify accuracy, then create a standalone article note (see Article Note step below). After the article note is saved, run the Backup to Readwise step above. This is the lightweight default — most reading sessions start here.
- **Focused Read:** Ask the user which article/note and which lens(es): Critical, Structural, Practical, or Dialectical. Run the Prefetch Step above if it's a Readwise source. Dispatch 1-2 Reader instances with the chosen lenses. Reader automatically handles transcript format (video/podcast) with preprocessing before applying the lens. Before write-back, dispatch **Reviewer** + **Challenger** in parallel to verify accuracy, then create a standalone article note (see Article Note step below). After the article note is saved, run the Backup to Readwise step above. Use when the user knows what angle they want.
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
   - Write the reflection file to `$OV/reflections/YYYY-MM-DD-reading-<slug>.md`
   - Include full source text under `### Full Text` (see source-text persistence rule in CLAUDE.md)
   - No write-back to daily notes. The reflection file is the durable output.

6. **Backup to Readwise — Phase 6 (source preservation):**
   - Run the Backup to Readwise step above (see Read sub-flows section).
   - Skip if the input was already a Readwise source or a local `[[Note Title]]`.

### If Learn:

| Option | Label | Description |
|--------|-------|-------------|
| 1 | **Recommend Resources** | Get reading/learning recommendations on a topic (Chinese summaries) |
| 2 | **Introspect** | Rebuild your self-model — discover identity, taste, curiosity, and directions from your notes |

- **Recommend Resources:** Dispatch to the **Librarian** agent. Ask the user what topic they want recommendations for. The Librarian searches existing notes for context, then recommends books, papers, articles, and other resources with Chinese summaries.
- **Introspect:** Read and follow `.claude/commands/introspect.md`

---

# Daily Reflection

Run a reflection session grounded in your notes and goals.

## Prerequisites

1. Check if `profile/identity.md` exists. If not, tell the user: "No profile found. Run `/introspect` first to build your self-model." and stop.
2. Read `profile/identity.md`. Check the `Last built:` date. If older than 7 days, warn: "Your profile is stale (built on [date]). Consider running `/introspect` to refresh. Continuing with current profile."

**Protocols used in this session:** `protocols/session-continuity.md` (connecting sessions), `protocols/epistemic-hygiene.md` (write-first nudge in warm-up, provenance tagging in write-back).

## Context Loading

1. **Read profile files:**
   - `profile/identity.md` — your self-model and intellectual taste
   - `profile/directions.md` — your goals and directions

2. **Read recent reflections** (last 3 files from `$OV/reflections/` directory, sorted by date). If none exist, this is the first session — note that.

3. **Pull fresh context from the vault:**
   - Determine the **effective date**: if current local time is before 03:00, use yesterday's date; otherwise use today's. This is the user's day boundary (late-sleep rule). All subsequent "today" references in this session use the effective date.
   - `Read $OV/daily-notes/<effective-date>.md` — what you've done today. If the file is missing or empty, note that and proceed; the user may not have captured anything yet.
   - If effective date differs from the calendar date (late-sleep active), also read `$OV/daily-notes/<calendar-date>.md` if it exists — the user may have captured something after midnight.
   - `Read $OV/daily-notes/<effective-date - 1>.md` — what you did the day before.
   - For recent activity related to your themes, run `Bash: uv run scripts/semantic.py query "<theme>" --after "<7 days ago, YYYY-MM-DD>" --top 5` first — this is the primary content lookup. For structural follow-up (exact strings, known tags), list files modified in the last 7 days with `Bash: find "$OV"/daily-notes "$OV"/reflections -type f -name "*.md" -mtime -7 2>/dev/null | sort`, then `Grep` the theme keyword across those paths.

4. **Load open TODO state (silent — orchestrator working memory):**
   - `Bash: uv run scripts/todos.py list --json` — parse and hold the open list throughout the session. Source files (`source` field) are needed at session end for closure write-back.
   - Don't display this output to the user. It's context for the orchestrator's decisions in Step 0 (digest), mid-conversation (topic matching), and Step 7 (resurface vs generate).
   - **Fallback:** if the command exits non-zero, fails to parse as JSON, or returns `[]`, proceed with empty TODO context for this session and note "TODO context unavailable" under Anomalies in the wrap-up. The TODO Awareness rules below all degrade silently to no-op when the queue is empty.

## Coaching Session

Based on the loaded context, run an interactive reflection.

**Cross-cutting rule: TODO Awareness.** The orchestrator holds the open TODO list loaded in Context Loading step 4 for the entire session.

- **Mid-conversation soft surfacing (max 1 per session):** if the user mentions a topic that strongly matches an open TODO not yet mentioned this session, do **one** soft callback: "顺便,你 [date] 写过 [item] 还 open — 要不要本周 commit?" Confidence threshold is high (phrase or strong-token overlap); do not reach for tenuous matches. If user confirms commitment → mark for closure-pending or promotion at wrap-up. If user declines → do not surface again this session.
- **No proactive list dump.** The TODO list is for *matching*, not narration. Never volunteer "btw here are N open TODOs" outside Step 0 digest or explicit user request.
- **Closure write-back at wrap-up.** When the user explicitly confirms in conversation that a TODO is done or killed (Step 0 closure / stale prompt or mid-session), accumulate the closure into the **pending Scribe operations** list (see "Pre-Output: Raw Capture" below). Do NOT do direct `Edit` from the orchestrator: that bypasses the `mechanical_capture` cost-partition contract and creates duplicate write paths. Two paths, two source types — both dispatched as Scribe `gtd_entry` operations at wrap-up:
  - **Done path (user completed the item):**
    - GTD-source (`source` under `$OV/gtd/`): pending op `gtd_entry` with `operation_kind: toggle_done`, `target_file: <source>`, `line_no: <line>`, `expected_text: <bullet text from list --json>`.
    - Reflection-source (`source` under `$OV/reflections/`): pending op `gtd_entry` with `operation_kind: prefix_line`, `target_file: <source>`, `line_no: <line>`, `expected_text: <bullet text>`, `prefix: "DONE <effective-date>: "`.
  - **Kill path (user abandons the item):**
    - GTD-source: pending op `gtd_entry` with `operation_kind: toggle_killed`. `[~]` is the killed marker per `todos.py` STATE_MAP; preserves the audit distinction from `[x]` (done). Orchestrator passes the marker glyph as a parameter.
    - Reflection-source: pending op `gtd_entry` with `operation_kind: prefix_line`, `prefix: "KILLED <effective-date>: "`. The scanner excludes both `DONE ` and `KILLED ` prefixes from open scans.
  - **Line-drift guard:** the Scribe re-reads the source line at the recorded `line_no` at dispatch time and verifies `expected_text` matches. If it does not match (the user manually edited mid-session), the Scribe aborts that operation with a "line drifted" error; the orchestrator notes the skipped closure under Anomalies in the wrap-up. The orchestrator does NOT do this verification itself.
  - Dispatch all accumulated closures at the Pre-Output stage, not mid-conversation — keeps the dialogue uninterrupted and routes mechanical writes through the cheap tier.

### 0. Continuity Check (if not the first session)

Run `Bash: uv run scripts/todos.py digest` to fetch:
- Last reflection's open Next Actions
- Closure candidates (TODOs mentioned with "已完成 X" / 等 closure language in recent daily notes)
- Top stale items (≥30d, kill-or-promote prompts)

Present **at most one item per category**, woven into the conversation per `protocols/session-continuity.md`. Do not dump the whole digest:

- **Last Next Action callback** (most recent prior session's first item, if from a different day): "Last time, you intended to [action]. How did that go?" Accept any answer without judgment — missed actions are data points, not failures.
- **Closure candidate** (if any): "I noticed you mentioned [X] in [date] — does that mean [TODO Y] is done?" If user confirms → add to closure-pending list (write-back at wrap-up).
- **Stale prompt** (if any): "[Item] has been open ~Nd with no movement. Kill, or promote to GTD with a real deadline?" If user picks "kill" → add to kill-path closures (per the write-back rules above). If "promote" → ask for due date and area, then accumulate a pending Scribe op: `gtd_entry` with `operation_kind: add`, `target_file: <active GTD file>`, `text: <item>`, structured fields `due: <date>`, `area: <#tag>`. The active GTD file is the most recently modified `.md` file in `$OV/gtd/` (`Bash: ls -t "$OV"/gtd/*.md | head -1`); resolve at accumulation time and pass as `target_file`. Dispatch happens at Pre-Output. Do NOT append directly from the orchestrator.

Skip rules:
- Previous session was **today**: skip the Next Action callback.
- Previous session had no Next Action: skip that part.
- No closure candidates: skip silently.
- No stale items: skip silently.
- First session ever: skip everything; introduce the system briefly.

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
Use `Bash: uv run scripts/semantic.py query "<concept>" --before "<3 months ago, YYYY-MM-DD>" --top 10` to find a semantically related note the user may have forgotten. Reframe and retry if thin.
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

### 6. Dining Pulse (brief, every session)

Lightweight capture of dining experiences for personal preference learning + future `/dine` recommendations. Skip silently if user has nothing to share.

**Trigger question** (one shot, only if dining didn't already come up in conversation):

> "今天有没有去新餐厅打卡, 或重访旧餐厅? 如有, 体验如何?"

**If user has dining to share, capture quickly** (do not deep-dive):
- 餐厅名 (中/英文均可)
- 评分 1-10 (8+ = top, 6-7 = good, 4-5 = ok, ≤3 = avoid)
- 再去? (Y / N / Maybe)
- **健康 flags** (per-visit, 依赖所点菜): use the taxonomy enumerated in `profile/diet.md` ("Full health-flag taxonomy" section). Multiple flags joined by `·`, blank = unobserved. Restaurant ordering 是健康管理重要部分, 不能省
- 1-2 句话: 必点菜, 服务/ambiance, 同行
- 推断 from context (else 1-line confirm): City / 类型 / Platform (OT/R/W/DD) / Credit used

**Accumulate as a pending Scribe operation** (do NOT `Edit` directly from the orchestrator):
- Pending op: `dining_row` with `target_file: <user's dining-log file under $OV/travel/>`, structured row fields (date, restaurant, city, type, score, 再去, health flags, platform, credit), `raw_content` for the 必点·备注 free-text column. 评分 + 再去 mandatory; dash placeholder only for missing data the user can't recall. Dispatch happens at Pre-Output. The Scribe reads the file's schema header at dispatch time and formats the row to match exactly.

**Cross-doc sync triggers** (silent unless flagged for user):
- If 评分 ≥ 8 AND 再去 = Y AND restaurant NOT in the regional catalog rotation → flag user: "Add to rotation?"
- If Credit = credit-perks tier (e.g., Resy / OpenTable / partner-network) → also flag: "Update perks ledger cycle subtotal?"
- If restaurant on the credit-perks catalog → mark ✅ + date in Cycle Tracking

**If user has nothing to share**: respond "记下了, 没新餐厅" and move to Close. Don't push.

**Output to reflection file** (new "Dining" section, see Output template below).

Keep this step under 60s of conversation time. Goal is consistent capture, not depth.

### 7. Close with Concrete Prompt

One specific, actionable next step tied to a goal. **Resurface before generating new** — the open queue is the first place to look:

1. Scan the loaded open-TODO list (Context Loading step 4) for items relevant to what was discussed this session — matching topic, area, or framework.
2. **If 1+ items match**: surface the most relevant as the next action. "Already on your list: [item] ([source]:[line]). Make it this week's commitment?" No need to invent.
3. **If no match AND fewer than 5 active items (P0/P1) in the queue**: generate a new concrete next action. The new action goes in the reflection file's `## Next Action` section as a single bullet line (`- <action>` or `1. <action>`). Plain prose under that header is invisible to `todos.py` and will not be resurfaced next session.
4. **If no match AND queue is bloated (≥5 active P0/P1)**: do not add. Say "Open queue is already at [N] active items. Today doesn't need to add — pick one from the list to commit to this week instead?" Surface 2-3 candidates, let user choose.

Not generic advice — something the user can do today or this week. Match user's language (Chinese for Chinese topics).

## Pre-Output: Raw Capture (Cloud-Native Mode)

Before writing the reflection file, dispatch the Scribe agent for every accumulated capture operation from this session. Under the cloud-native architecture, chat is the user's authoring surface; the orchestrator must record raw input rather than only synthesizing it into the reflection. Do this work via the Scribe, not yourself: transcribing chat input on `core_intelligence` is a known cost antipattern.

The orchestrator accumulates pending Scribe operations during the session (it does NOT write directly). Sources of accumulated ops:

| Source step | Scribe operation | When to accumulate |
|---|---|---|
| Step 0 closure write-back (TODO Awareness rule) | `gtd_entry` (`toggle_done` / `toggle_killed` / `prefix_line`) | User confirmed a TODO done or killed (GTD-source toggle; reflection-source prefix) |
| Step 0 stale prompt → promote | `gtd_entry` (`add`) | User picked "promote" with due date and area |
| Step 6 Dining Pulse | `dining_row` | User shared a restaurant visit |
| Any step where user dictates a daily-note-style narrative for a date | `daily_note` | Narrative covers events for a date whose daily-note file is missing or lacks the new content |
| Any step where a person is mentioned with bio context AND no person note exists | `people_stub` | Verify with `uv run scripts/people.py "<name>"` before adding; only accumulate if no match returned |
| User explicitly says "save this" / "记一下" with no typed slot fit | `generic` | Orchestrator picks a `$OV/drafts/` path and confirms with user before adding to pending list |

**Skip condition (per op):** the corresponding file already captures the content, or the user provided only reflection-mode input (questions, feelings, abstract discussion) for that surface. Do not invent content.

**Dispatch all accumulated ops at this stage.** For each pending op, call the Scribe with the operation-specific fields documented in `.claude/agents/scribe.md` ("Operations" section). Do NOT pre-rewrite user text before passing it; the Scribe applies verbatim + light-format rules.

Where pending ops target independent files, dispatch the Scribe calls in parallel (single message, multiple `Agent` tool calls) for latency.

If the Scribe returns a clarification request (missing schema reference, line drift on a closure, ambiguous target file), resolve it: ask the user if needed and re-dispatch, or note the skipped op under Anomalies in the reflection's Session Meta. Do not silently fall back to direct orchestrator writes.

After all Scribes return, proceed to Output.

## Output

After the interactive session, write a reflection file:

**File:** `$OV/reflections/YYYY-MM-DD-reflection.md`
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

## Dining
| Restaurant | Score (/10) | 再去 | 健康 flags | 必点·备注 |
|---|---|---|---|---|
| [Name] | [1-10] | Y/N/Maybe | [flag(s) per profile/diet.md taxonomy] | [必点 + 1 line] |

- Captured to: the dining log (count of new rows appended)
- Cross-doc updates triggered: [regional rotation add? perks ledger update? perk-program ✓?]
- 健康 trend: [if multiple recent entries flag the heavy-load flags from `profile/diet.md` → surface as health observation in Next Action]
- (omit table entirely if no dining captured)

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
The script prints the file path (e.g., `$OV/sessions/2026-04-11-reflection.md`). It handles the late-sleep date rule and collision auto-increment.

**Step 2: Fill the skeleton.**
Use `Edit` to populate each section of the skeleton from data you accumulated during the session:

- **Agents Dispatched:** One row per agent you dispatched. Include agent name, task summary, success/failure, and approximate turns.
- **Search Log:** Every `semantic.py query` and notable `Grep` you or agents issued. Mark whether results were useful (yes/no).
- **Questions & Engagement:** Each question you asked the user. Note depth level (surface/structural/paradigmatic) and whether it landed (got substantive response).
- **Frameworks Applied:** Any framework the Thinker applied. Include fit score if available.
- **Continuity:** Which previous session you referenced (from step 0), and the seed/next-action from step 5.
- **Decisions & Branches:** Non-obvious routing decisions (e.g., "skipped framework; user in a rush").
- **Anomalies:** empty searches, user course corrections, degraded mode (e.g., TODO context unavailable).
- **Harness Assumptions Exercised:** Any assumption from `protocols/harness-assumptions.md` that was load-bearing (e.g., "Profile stale >7d warning triggered").

If a section has no data, leave the table headers but add no rows. Do not invent data. If the write fails, warn and continue; session logs never block a session.

## Wrap Up

The reflection file in `$OV/reflections/` is the durable session output. No write-back to daily notes — the user's daily note is their capture stream, read-only from the system's perspective. Tell the user the reflection has been saved and where to find it.
