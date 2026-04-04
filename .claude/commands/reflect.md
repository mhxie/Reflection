# Reflect

Your reflection system. Uses a two-step decision tree with `AskUserQuestion` for native scroll-and-select UI.

## Quick Start

If the user types `/reflect` with additional context, detect intent and route:
- **Paper review intent** (mentions "paper", "arXiv", "review paper", or links to arxiv.org/openreview.net): skip the menu and go to Paper Review using their input as the paper to review.
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
| 5 | **Learn** | Get recommendations or rebuild your context index |

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
| 1 | **Compact Notes** | Find and merge redundant or overlapping notes |
| 2 | **Deep Dive** | Full briefing on a topic — notes + web research + resources + framework, 4 agents in parallel |
| 3 | **Note Triage** | Scan for compaction candidates across your notes |
| 4 | **Process Meeting** | Turn a work meeting transcript into structured notes with action items |

- **Compact Notes:** Dispatch to the **Curator** agent. Ask the user what topic or notes to compact. The Curator searches for related notes, proposes a merged version, and waits for approval before writing.
- **Deep Dive:** Ask the user for a topic, then dispatch **four agents in parallel**:
  1. **Researcher** — search all notes related to this topic (what you've already thought/written)
  2. **Scout** — search the web for recent articles, research, and developments on this topic
  3. **Librarian** — find curated resources to deepen understanding (books, papers, courses)
  4. **Thinker** — select and apply a relevant framework from `frameworks/`
  Once all four return, **Synthesizer** combines their outputs into a unified briefing: your existing thinking, external intelligence, curated resources, and a framework lens — all in one view. Present in Chinese for reading-intensive output.
- **Note Triage:** Ask the user for 3-5 topic areas (or pull from `index/meta-summary.md` themes). Dispatch the **Researcher** to search each topic area in parallel. For each area, identify notes with overlapping content. Present a prioritized compaction plan: which notes to merge, estimated redundancy, and impact. The user picks which to compact, then dispatch to **Curator** for each approved merge.
- **Process Meeting:** Ask the user to paste or provide the meeting transcript. Dispatch the **Meeting** agent (Executive mode — action items, decisions, next steps). Present the structured output. Ask the user if they want to save as a Reflect note — if yes, dispatch **Curator** to create it. For research talks or presentations, use Read instead — Reader handles transcript format with real analytical lenses.

### If Read:

| Option | Label | Description |
|--------|-------|-------------|
| 1 | **Read & Discuss** | Quick read + interactive discussion (default) |
| 2 | **Focused Read** | Pick 1-2 specific lenses to focus on |
| 3 | **Multi-Lens Read** | Read with all 4 lenses in parallel — full analysis |
| 4 | **Paper Review** | Human-steered, AI-accelerated paper review — you lead, AI does the legwork |

- **Read & Discuss:** Ask for the article/note. Dispatch 1 Reader (Critical lens) + 1 Researcher (find related notes). Present the analysis, then enter interactive discussion mode. Before write-back, dispatch **Reviewer** + **Challenger** in parallel to verify accuracy, then create a standalone article note (see Article Note step below). This is the lightweight default — most reading sessions start here.
- **Focused Read:** Ask the user which article/note and which lens(es): Critical, Structural, Practical, or Dialectical. Dispatch 1-2 Reader instances with the chosen lenses. Reader automatically handles transcript format (video/podcast) with preprocessing before applying the lens. Before write-back, dispatch **Reviewer** + **Challenger** in parallel to verify accuracy, then create a standalone article note (see Article Note step below). Use when the user knows what angle they want.
- **Multi-Lens Read:** Ask the user which article or note to read. Then follow the Reading Hub flow below. Use for important articles worth deep multi-angle analysis.
- **Paper Review:** Ask the user which paper to review (URL, title, or [[Note]]). Then follow the Paper Review flow below. Designed for non-peer-reviewed papers (arXiv, blog posts with claims, technical reports) where the user acts as reviewer.

#### Paper Review Flow

A human-steered, AI-augmented review flow. The user leads — setting focus, validating figures, making judgment calls, and owning the verdict. AI agents augment by gathering evidence, surfacing blind spots, and stress-testing the draft. AI never decides — it provides structured input for the user to accept, reject, or reshape.

**Core principles:**
- **Human steers, AI augments.** Every phase has a human checkpoint. AI gathers and organizes; the user judges and decides. When in doubt, ask the user rather than filling in details autonomously.
- Read `personal/research-profile.md` at session start — it defines the user's domain expertise, known biases, research taste, and review calibration. Check the Known Biases table and actively flag when a bias may be influencing the review.
- Non-peer-reviewed papers need extra scrutiny: methodology, reproducibility, overclaims.
- Figures, diagrams, and tables carry critical information that text alone can't validate. Pause for the user.
- Past paper reviews inform the current one — find the user's prior work in this area.
- Papers can be provided as URLs or local PDFs in the `papers/` directory.

**Confidence calibration:**
Before starting the review, ask the user their confidence level with the paper's domain. This is the FIRST thing to establish — it controls everything downstream.

| Confidence | Label | Review stance | Max comments |
|-----------|-------|--------------|-------------|
| 1/4 | No familiarity | Flag obvious issues only. Lean heavily on Scout intelligence. Avoid domain-specific critiques. Preface uncertain comments with "From an outsider's perspective..." | 6 total |
| 2/4 | Some familiarity | Critique methodology and presentation confidently. Soften domain-specific technical claims. Note where you lack expertise to judge. | 8 total |
| 3/4 | Knowledgeable | Full critique. Flag subtle issues. Connect to related work from user's notes. | 10 total |
| 4/4 | Expert | Authoritative review. Challenge novelty claims, compare to state-of-art, question baselines in detail. | 12 total |

The confidence level calibrates **everything**: comment count, specificity, language strength, and reliance on external evidence. Lower confidence = fewer comments, softer language, more Scout-derived evidence.

**Output constraints (hard limits):**
- Strengths: 2-3 bullets max. One sentence per strength.
- Weaknesses: 3-5 bullets max. Each must cite specific evidence (section, figure, table).
- Questions: 2-4 bullets max.
- Total items (strengths + weaknesses + questions): capped by confidence level above.
- Summary: 2-3 sentences. Verdict-oriented, not a paragraph.
- **Citations:** When referencing other papers, use numbered references inline (e.g., "MapReduce [1]") with a References section at the end in APA format. This applies to weaknesses, comments, and any claim that invokes prior work. Scouts should gather full citation metadata (authors, year, venue) during Phase 1.
- **Apply these limits from the start.** Do not produce a long draft and then ask the user to cut — start concise.

##### Phase 1: Gather (parallel)

Dispatch these agents in parallel:

1. **Reader** (Critical lens) — read the paper's text, focusing on:
   - Claims vs. evidence quality
   - Methodology soundness (experimental setup, baselines, ablations)
   - Reproducibility signals (code available? hyperparameters listed? dataset public?)
   - Novelty: what's genuinely new vs. incremental vs. repackaged
2. **Researcher** — two searches:
   - Find the user's existing notes on this paper's topic area (establish expertise baseline)
   - Search for past paper reviews (`#paper-review` tag or "paper review" text) to understand the user's review style and standards
3. **Scout** (2-3 instances, direction-based) — investigate areas the user may not have deep expertise in:
   - **Related work**: key papers cited, are citations fair and complete?
   - **Author/lab context**: track record, prior work, known biases, funding sources
   - **Reception**: community discussion (Twitter/X, HN, Reddit, OpenReview), known rebuttals or replications

##### Phase 2: Figure Checkpoint (interactive, sequential)

Before synthesizing, present a **figure index** — a numbered list of all figures, tables, and diagrams in the paper:

```
Figures in this paper:
1. Figure 1 — [paper's caption/claim]
2. Figure 2 — [paper's caption/claim]
3. Table 1 — [paper's caption/claim]
...
```

Then walk through them using this protocol:

1. **Present the figure** — name it, state what the paper claims it shows
2. **Ask the user to validate** — "Can you describe what you actually see?" or "Does the data support the claim?"
3. **Record the observation** — capture match/mismatch as ground truth for the review
4. **Flag issues found** — truncated axes, missing error bars, cherry-picked ranges, misleading scales. These become weakness candidates.

Rules for figure checkpoints:
- Present the index, then **let the user select** which figures to validate. Don't force a walk-through of every figure — the user knows which ones matter.
- **Suggest a priority order** if the user asks: (1) main evaluation/result figures first, (2) comparison tables, (3) ablation figures, (4) architecture diagrams last (they rarely yield review findings).
- Group related figures (e.g., "Figures 3-5 all show ablation results — let's look at them together").
- For each figure, explicitly check: truncated axes, missing error bars, cherry-picked ranges, misleading scales, log vs. linear scale choices, omitted data points.
- If the paper is text-only (no figures), skip this phase and note it: "No figures to validate."
- If the user can't access a figure, note it as "unvalidated" in the review.
- **Figure issues often become the strongest weaknesses.** Track each finding with a tag (e.g., "Figure 11 → W3") linking it to a specific weakness in Phase 3.

##### Phase 3: Expertise-Aware Synthesis

**Goal: accelerate the user's reading, not replace it.** Combine all agent findings into a structured briefing that lets the user skip the legwork and focus on judgment. Present in the **source language** of the paper (typically English for arXiv).

AI reads and organizes so the user can focus on what matters:
- Summarize contributions, methodology, and key claims — save the user from a cold read
- Surface related work gaps, author context, and community reception (from Scouts)
- Flag potential issues organized by the user's expertise level — so the user knows where to dig deeper vs. where to trust the AI's homework

| Section | What AI provides | What the user does |
|---------|-----------------|-------------------|
| **Your domain** | Concise summary of what's new or suspicious — skip the obvious | Judge independently, challenge novelty claims, connect to your own work |
| **Adjacent domain** | More context + Scout findings — bridge the gap | Evaluate with AI's help, ask for clarification on unfamiliar parts |
| **Outside your domain** | Scout intelligence presented prominently — the AI did the homework | Assess whether the evidence is convincing, but don't fabricate domain expertise |

Present the briefing, then **pause and ask**: "What stands out to you? Where do you want to dig in?" Let the user set the direction for Phase 4.

##### Phase 4: Interactive Review Discussion

**Goal: the user leads, AI accelerates.** The user drives the discussion; AI provides real-time support to make the user faster and more thorough, not to generate opinions.

What the user does:
- Sets focus: which claims, figures, or sections to investigate
- Makes judgment calls on novelty, significance, and technical correctness
- Decides the verdict and confidence level

What AI does to accelerate:
- **On-demand research**: when the user raises a concern, dispatch a Scout to investigate immediately — no need for the user to search themselves
- **Cross-reference**: connect the user's questions to related work, their own papers/notes, and Scout findings already gathered
- **Bias check**: compare the user's emerging critique against the Known Biases table. If a bias may be at play, name it: "Note: this touches your evaluation-harshness bias — is the critique proportional to the venue's bar?"
- **Structured capture**: as the discussion progresses, maintain a running draft of strengths/weaknesses/questions so the user doesn't have to track everything mentally

Rules:
- Don't generate opinions the user didn't ask for. Present evidence and ask questions.
- Don't fill in details autonomously — if something is unclear, ask the user.
- When the user makes a judgment call, record it. Don't second-guess unless a Known Bias is triggered.

##### Phase 5: Paper Review Note (standalone)

After discussion, produce a local review file, gate it, then offer to create a Reflect note.

**Step 1: Save locally.** Write the review to `papers/<slugified-paper-title>-review.md`. This is the canonical version.

**Step 2: Quality gate.** Dispatch **Reviewer** (verify claims are grounded in the paper text) + **Challenger** (check completeness, flag if a Known Bias may have influenced the verdict) in parallel. Apply fixes before proceeding. This is the same gate used in all other reading flows.

**Step 3: Ask before creating Reflect note.** Present the user with: "Ready to create the Reflect note. Want me to create `[Paper Title] — Review` in Reflect?" Wait for explicit approval. Never auto-create.

**Step 3: Identical content.** The Reflect note body MUST be identical to the local markdown file. Do not rewrite, summarize, or reformat. Copy the content verbatim. If the user wants a shorter version in Reflect, they ask explicitly.

Create the note using `create_note`:

**Title:** `[Paper Title] — Review`

**Body structure:**
```markdown
#paper-review #[topic-tags]

**Paper:** [Full title]
**Authors:** [Author list]
**Source:** [URL]
**Date reviewed:** [YYYY-MM-DD]
**Verdict:** [Strong Accept / Accept / Borderline / Weak Reject / Reject] (user confirms)

## Summary
[2-3 sentence summary of the paper's core contribution]

## Strengths
- [Strength 1 — with specific evidence]
- [Strength 2]

## Weaknesses
- [Weakness 1 — with specific evidence]
- [Weakness 2]

## Figure Validation
- Figure N: [Paper's claim] → [User's observation] → [Match/Mismatch]

## Methodology Assessment
- Baselines: [fair / unfair / missing key comparisons]
- Reproducibility: [code available / parameters listed / dataset public]
- Statistical rigor: [appropriate / insufficient / not applicable]

## Key Questions
- [Unresolved questions from the discussion]

## Connections
- [[Related Paper 1]] — [how it connects]
- [[Related Note]] — [how it connects]

## Scout Intelligence
- [Key external findings — community reception, author context, related work gaps]

## References
[1] Author, A., Author, B., & Author, C. (Year). Title. In *Venue* (pp. X-Y).
[2] ...
```

**No daily write-back.** The paper review note is the sole output. Ask user to confirm the verdict before creating the note.

##### Paper Organization

When the Researcher finds existing paper reviews during Phase 1, present a brief overview:
- "You've reviewed N papers in [topic area]. Recent ones: [[Paper A]], [[Paper B]]."
- If the user has many untagged paper notes, suggest: "I found some paper notes without `#paper-review` — want me to flag them for tagging?"

Over time, the `#paper-review` tag becomes the user's personal review index, searchable and browsable in Reflect.

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
   - Tag with `#ai-reflection`

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
| 2 | **Build Index** | Rebuild your reflection context — run this first if new, or monthly to refresh |

- **Recommend Resources:** Dispatch to the **Librarian** agent. Ask the user what topic they want recommendations for. The Librarian searches existing notes for context, then recommends books, papers, articles, and other resources with Chinese summaries.
- **Build Index:** Read and follow `.claude/commands/index.md`

---

# Daily Reflection

Run a reflection session grounded in your Reflect notes and goals.

## Prerequisites

1. Check if `index/meta-summary.md` exists. If not, tell the user: "No reflection index found. Run `/project:index` first to build your profile." and stop.
2. Read `index/meta-summary.md`. Check the `Last built:` date. If older than 7 days, warn: "Your reflection index is stale (built on [date]). Consider running `/project:index` to refresh. Continuing with current index."

**Protocols used in this session:** `protocols/session-continuity.md` (connecting sessions), `protocols/integration.md` (insight → action), `protocols/contradiction-detection.md` (surfacing contradictions in Step 3), `protocols/epistemic-hygiene.md` (write-first nudge in warm-up, provenance tagging in write-back).

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

- If **AI content already exists**: Skip write-back. Tell the user: "Already wrote to today's daily note earlier — skipping duplicate write-back."

- If **no existing AI content**: Before presenting the write-back, dispatch **Reviewer** + **Challenger** in parallel to verify citation accuracy, framing, and tone. Fix any issues they surface. Then **ask the user for approval before writing.** Present the proposed write-back and wait for confirmation. Do not auto-write. **Write-backs are always in English**, even if the session was conducted in Chinese. The write-back should follow this format:
  ```
  ## [Descriptive Title] #ai-reflection
  [2-3 sentence summary of key insights from today's reflection session]
  Related: [[Note Title 1]] [[Note Title 2]]
  ```
  **Title guidelines:** The heading must describe the session's core theme or question — not its source. Titles are in English (same as the write-back body). Good examples:
  - Topic-based: `Constraint creates meaning`
  - Question-based: `Why does unlimited freedom feel empty?`
  - Date+theme: `03/15 Energy dip and recovery patterns`
  - Insight-based: `Delegation as a trust signal`

  Never use generic titles like "AI Reflection" or "Daily Reflection Summary." The `#ai-reflection` tag already marks the content as AI-generated.

  Include [[backlinks]] to all notes referenced during the session so they appear in Reflect's backlink graph. Use today's date in YYYY-MM-DD format.

## Wrap Up

Tell the user the reflection has been saved.
