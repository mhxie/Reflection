# Introspect

Build or refresh your self-model by examining your Reflect notes, session history, and reading patterns. Produces three profile files that the rest of the system consults.

Unlike `/index` (mechanical extraction), `/introspect` discovers patterns: what you're drawn to, how your taste is shifting, where your curiosity is orbiting before you've named it as a goal.

## Prerequisites

Verify the local `zk/` mirror is present and non-empty: `Bash: test -d zk/daily-notes && ls zk/daily-notes | head -1`. If the directory is missing or empty, tell the user: "Local `zk/` mirror is missing. Check your Google Drive sync." The Reflect MCP is used only for semantic search fallbacks in this command and is not required to start.

## Output Files

```
profile/
├── identity.md      — who you are + intellectual taste + curiosity vectors
├── directions.md    — era, goals, quarterly focus, active directions
└── expertise.md     — domain knowledge, research taste, known biases
```

`reader_persona.md` (at repo root) is a raw input signal, not a profile output. Built separately by `/build-persona` from Readwise data.

## Pipeline

### Step 1: Gather Raw Material

Run these searches in parallel over the local `zk/` mirror. Local grep is instant, deterministic, and returns full paths you can then `Read` without any MCP round-trip.

**Goals & Directions:**
1. `Grep(pattern: "目标", path: "zk/")` — Chinese goal mentions
2. `Grep(pattern: "goal", path: "zk/", -i: true)` — English goal mentions
3. `Grep(pattern: "小目标", path: "zk/")` — Annual goal notes
4. `Grep(pattern: "objective", path: "zk/", -i: true)` — Additional goal mentions

**Identity & Themes:**
5. Discover tags: `Bash: grep -rohE '#[A-Za-z][A-Za-z0-9_-]*' zk/ | sort -u` (local tag inventory)
6. `Grep(pattern: "career", path: "zk/", -i: true)` — Career trajectory
7. `Grep(pattern: "职业", path: "zk/")` — Chinese career notes
8. `Grep(pattern: "learning", path: "zk/", -i: true)` — Learning interests
9. `Grep(pattern: "学习", path: "zk/")` — Chinese learning notes

**Recent Context:**
10. `Read zk/daily-notes/<today>.md` — today (fall through to `get_daily_note` only if the file hasn't synced)
11. `Read zk/daily-notes/<yesterday>.md` — yesterday
12. Recent planning: `Bash: find zk/daily-notes zk/reflections zk/gtd -type f -name "*.md" -mtime -30 | xargs grep -l -i "plan" 2>/dev/null`

Deduplicate results by file path. Prioritize files with recent mtimes. **Semantic pass:** for conceptual angles grep cannot phrase ("curiosity vectors", "intellectual taste", "what am I drawn to"), run `Bash: uv run scripts/semantic.py query "<concept>" --top 10`. In Phase C this is the only semantic tool — reframe and retry if thin; there is no MCP fallback.

### Step 2: Read Full Content

For the top ~30-40 most relevant notes, `Read` the file paths returned by Step 1 directly. The files are already on disk — no MCP round-trip. Focus on:
- All goal notes (critical for directions.md)
- Recent daily notes (critical for identity.md — taste and curiosity signals)
- Top career/learning notes

### Step 3: Discover Taste & Curiosity (NEW — not in old /index)

This step goes beyond mechanical extraction. Look for:

**Intellectual taste** (what you engage deeply with vs. skim):
- Topics that recur across daily notes without being declared goals
- Articles/papers you chose to deep-read vs. archive (check triage files in `zk/cache/triage-*.md`)
- Discussion tangents that repeatedly surface in reflection sessions
- Aesthetic preferences in how you evaluate ideas (from research-profile patterns)

**Curiosity vectors** (areas orbiting but not yet goals):
- Topics mentioned 3+ times in recent notes that aren't in current goals
- Reading saves that cluster around an unnamed theme
- Questions you keep asking but haven't formalized

**If `reader_persona.md` exists**, read it as a secondary signal — it shows what you save (behavioral), not what you think about (intentional). Note divergences between Readwise patterns and Reflect patterns.

### Step 4: Synthesize Profile Files

Using all gathered content, write three files:

**`profile/identity.md`** — who you are + taste + curiosity:
```markdown
# Identity
Last built: YYYY-MM-DD

## Who You Are
[2-3 sentence summary — role, interests, life stage]

## Active Life Areas
[Bullet points for each major area]

## Major Themes
[Recurring topics — what does this person think about most?]

## Intellectual Taste
[What you find interesting, elegant, and worth your time — independent of goals.
Built from session patterns and reading engagement.]

## Curiosity Vectors
[Areas you're starting to orbit but haven't formalized as goals yet.
Detected from session patterns, reading saves, and discussion tangents.]

## Key People
[Important people referenced frequently]

## Recent Focus (last 30 days)
[What you've been writing about recently]
```

**`profile/directions.md`** — era, goals, focus:
```markdown
# Directions
Last built: YYYY-MM-DD

## Era
[Current era, theme, primary/secondary directions, quarterly focus]

## Near-term (next 1-3 months)
[Goals with specific metrics — Source: [[Note Title]]]

## Mid-term (3-12 months)
[Goals from annual planning notes]

## Long-term (1-3 years)
[Career/life direction from strategic planning]

## Stale Goals (>1 year old, may need review)
[Goals from notes not edited recently]
```

**`profile/expertise.md`** — domain knowledge, research taste:
- Only update if new evidence warrants it (new reviews, new domain exposure)
- Follow the update guidelines already in the file
- Don't downgrade expertise without multiple data points

### Step 5: Quality Gate — Profile Validation

Before writing profile files, dispatch **Reviewer** + **Challenger** in parallel:

- **Reviewer** spot-checks 3-5 claims in the draft profile against source notes by `Read`-ing the local file paths:
  - Are cited [[Note Titles]] real and accurately represented?
  - Do "Intellectual Taste" claims have evidence in the notes, or are they fabricated?
  - Are goal statuses (progressing/stale) consistent with note edit dates?
  - Score using Session Review rubric (Citation Accuracy + Honesty dimensions only)
- **Challenger** probes the profile for blind spots:
  - Are curiosity vectors genuinely emerging, or just noise from 1-2 notes?
  - Does the profile overweight recent notes and miss long-term patterns?
  - Are there important life areas absent from the profile entirely?

If Reviewer scores < 7 on either dimension, fix the specific issues before writing. Present the validated profile to the user before saving — the user confirms or corrects.

### Step 6: Check for Divergences

Compare the three profile layers and flag tensions:
- Identity taste says X, but directions don't include it → potential emerging goal?
- Reader persona (Readwise) shows heavy saves in area Y, but no Reflect notes → consuming but not processing?
- Expertise is deep in area Z, but no current goals reference it → dormant strength?

Present divergences to the user — these are the interesting findings.

### Session Log

After writing profile files, emit a session log:
1. `Bash: uv run scripts/session_log.py --type introspect --duration <minutes>`
2. `Edit` the created file to populate sections from session data (agents dispatched, searches, questions, frameworks, anomalies). See `reflect.md` Session Log for the full fill-in guide. Leave empty sections with headers only. If the write fails, warn and continue.

### Step 7: Report

Tell the user what you found:
- How many notes were queried
- Key themes identified
- **Taste and curiosity discoveries** (the new part)
- Any divergences between layers
- Suggest running `/reflect` to start using the profile
