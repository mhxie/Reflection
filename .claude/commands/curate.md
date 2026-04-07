# Curate

Goal-aware content curation. Pulls from content sources, scores against your active goals and directions, and routes items into tiers.

## Flow

### 1. Load Context (orchestrator)

Read these files (they should already be loaded in a reflection session):
- `profile/directions.md` — current goals, directions, and era context
- `profile/identity.md` — active life areas and themes

### 2. Dispatch Triage Agent (ad-hoc)

Dispatch a **general-purpose agent** (not a named agent) with this prompt structure:

```
You are triaging a content inbox against the user's active goals and directions.

## Goals and Directions
[paste relevant sections from profile/directions.md — current era, near-term goals, learning directions]

## Task
1. Run BOTH commands in parallel (two Bash calls in one response):
   - `readwise reader-list-documents --location new --limit 30 --response-fields id,title,author,summary,category,word_count,saved_at,tags,source_url --json`
   - `readwise reader-list-documents --location later --limit 20 --response-fields id,title,author,summary,category,word_count,saved_at,tags,source_url --json`
3. For each item, assign a tier:
   - **deep-read** — directly relevant to an active goal or learning direction, worth a full reflectl reading session
   - **digest** — interesting context, include in weekly summary, but not worth dedicated time
   - **archive** — low relevance or already absorbed from the summary
4. Write the ranked list to `zk/cache/triage-YYYY-MM-DD.md` with format:

   ```markdown
   # Triage — YYYY-MM-DD
   
   ## Deep Read
   - `id:DOC_ID` [Title](url) — author — *one-line reason tied to a specific goal*
   
   ## Digest
   - `id:DOC_ID` [Title](url) — author — *one-line summary*
   
   ## Archive
   - `id:DOC_ID` [Title](url) — *why skipped*
   
   ## Stats
   - Inbox: N items | Later: N items
   - Deep read: N | Digest: N | Archive: N
   ```

5. Return ONLY: the stats line + the Deep Read section (titles and reasons). Do not return the full list.
```

### 3. Present Results (orchestrator)

Show the user:
- Stats (inbox size, tier breakdown)
- Deep Read candidates with goal-relevance reasons
- Ask: "Want me to tag these in Readwise and archive the rest?"

### 4. Execute (orchestrator)

On approval:
- Tag deep-read items: `readwise reader-add-tags-to-document --document-id <id> --tag-names deep-read`
- Tag digest items: `readwise reader-add-tags-to-document --document-id <id> --tag-names digest`
- Archive skipped items: `readwise reader-move-documents --document-ids <id1>,<id2>,<id3> --location archive`
- Tag all processed items: `readwise reader-add-tags-to-document --document-id <id> --tag-names auto-triaged`

### 5. Bridge to Reading (optional)

If the user wants to read something now, transition to `/reflect → Read` with the selected item.

## Integration Points

- **`/weekly`** — (planned) pulls `#digest` tagged items from Readwise as a "Reading Digest" section
- **`/reflect → Read`** — (planned) surfaces `#deep-read` tagged items as reading suggestions
- **`reader_persona.md`** — if it exists, the triage agent can reference it for taste calibration alongside goals

## Adding New Sources

To add a new content source (e.g., Zhihu, Twitter):
1. Create `sources/<name>.md` with setup, CLI commands, and output format
2. Update the triage agent prompt to also pull from the new source
3. The same tier logic applies — deep-read / digest / archive
