# Error Handling & Graceful Degradation

Defines how agents handle failures without blocking sessions.

The mental model is **local-first**: `zk/` is the authoritative read path and is always available (plain files on disk). Reflect MCP is a capture/archival surface — its outage only degrades today's fresh daily note (before the sync catches up), write-backs via `append_to_daily_note`, and `create_note` dispatches. Readwise MCP only matters for `/curate` inbox flows. Treat MCP failures as degraded peripherals, not as a loss of the knowledge base.

## Failure Hierarchy

Failures are ranked by severity. Handle at the lowest level possible.

### Level 1: Recoverable (handle silently)
- Grep returns empty → try alternative phrasing, broader pattern, or other language
- Note file shorter than expected → use what's available
- Framework file missing → skip framework, use first principles
- Previous reflection file missing → treat as first session

### Level 2: Degraded (warn and continue)
- **Reflect MCP unreachable**: No effect on the read path — `zk/` is primary. Degrades only (a) today's fresh daily note before the sync catches up (fall back to yesterday's local file and warn), (b) write-back via `append_to_daily_note` (save the write-back to `zk/reflections/` and inform the user), and (c) `create_note` dispatches (Curator queues the proposed note as a local draft under `zk/drafts/` for later retry).
- **Readwise MCP unreachable**: `/curate` is blocked. All other commands unaffected.
- **Local mirror stale** (today's daily note not yet synced from Reflect): fall through to `get_daily_note(date: "<today>")` for that one read; continue.
- **Target note genuinely missing from local mirror**: fall through to `get_note(id)` or `search_notes` for that one lookup. Note the fallback in the agent handoff.
- **Index files stale (>7 days)**: warn user, proceed with stale profile.
- **Multiple searches return empty**: report coverage gap, continue with available data.
- **Web search fails**: Scout/Thinker continue without external sources, note the limitation.

### Level 3: Blocking (stop and inform)
- `zk/` directory missing or unreadable → the primary read path is gone. Guide the user to check the Google Drive sync.
- Profile files missing → cannot run reflection, guide user to `/introspect`.
- All goal data missing → cannot run review, suggest `/introspect`.
- Fundamental prompt misunderstanding → ask user to clarify.

## Agent-Specific Fallbacks

### Researcher
- **Grep returns empty**: Try 3 alternative queries before reporting gap. Strategy: exact → synonym → other language → broader category.
- **Target note not in local mirror**: Fall through to `get_note(id)` or `search_notes` via MCP for that specific lookup. Note the fallback in the handoff.
- **Semantic concept can't be phrased as grep**: Run `Bash: scripts/semantic.py query "<concept>"` — the stub lexical-falls-through today (stderr warning) and switches to embeddings once the `zk/.semantic/index.sqlite` sentinel lands. This is the primary semantic path, not a degraded one. Escalate to `search_notes(searchType: "vector")` only when the stub demonstrably misses the concept; that MCP call is a documented escape hatch.
- **Reflect MCP down AND local grep misses**: Report the gap honestly with `[DEGRADED: not in local mirror, MCP unavailable]`. Do not fabricate content.
- **Rate limited on MCP fallback**: Batch remaining queries, report partial results.

### Synthesizer
- **No research brief received**: Read `zk/` directly (bypass normal contract). Prefix output with `[DEGRADED: No research brief, synthesizing from direct reads]`.
- **Research brief has critical gaps**: Acknowledge gaps explicitly in output rather than filling with speculation.
- **Write failure to `zk/reflections/`**: Abort with a clear error — this is the primary write path and there is no further fallback. Report the filesystem error to the user.

### Reviewer
- **Cannot verify citation**: Mark as `UNVERIFIED` rather than `FAIL`. Distinguish "wrong" from "couldn't check".
- **`profile/directions.md` missing**: Skip goal coverage check, note in output.
- **Source note not in local mirror**: Attempt `get_note()` via MCP; if still missing, mark `UNVERIFIED`.

### Challenger
- **No recent entries in `zk/daily-notes/`**: Use the latest reflection file in `zk/reflections/` as context instead.
- **No contradictions found**: This is fine — not every session has contradictions. Don't force them.
- **User emotional state unclear**: Default to neutral register.

### Thinker
- **Framework files missing**: Use built-in knowledge of frameworks (they're well-known models).
- **Web search fails**: Proceed without external sources, note the limitation.
- **No clear framework fit**: Use first principles thinking — always available.

### Curator
- **Content loss in merge**: Run Content Preservation Checklist (see `curator.md`). Scan snapshot files in `zk/cache/<operation>-*.md` for `![`, `http`, `[[`, table syntax before finalizing. If any media is found in snapshots but missing from output, block the proposal until fixed.
- **create_note produces empty note (silent failure)**: The parameter is `contentMarkdown`, not `content`. After every `create_note` call, verify with `get_note` that the body is non-empty. If empty: the wrong parameter was used. Fix the parameter name and retry with a new title (the empty note now occupies the original title and cannot be overwritten or deleted via API).
- **create_note returns existing note**: This means the title conflicts. Inform the user — they must either choose a different title or manually edit in Reflect.
- **Merge mistake after creation**: Cannot fix via API. Create a corrected note with an amended title (e.g., "Title v2") and inform the user to delete the bad one manually.
- **Snapshot missing at dispatch time**: If the orchestrator could not produce a snapshot at `zk/cache/<operation>-<slug>.md` for any source note (neither local copy nor MCP `get_note` fallback succeeded), abort the operation. Do not proceed with partial sources.
- **Source note disappears mid-session**: The dispatch-time snapshot in `zk/cache/` is authoritative. Continue working from the snapshot — the loss of the original is informational only. This is exactly what the snapshot step exists to protect against.
- **Size overflow**: The Reflect API times out at ~20KB. Use 15KB as the working limit — split notes into parts at 15KB with cross-link headers. Never attempt to create a note you estimate will exceed 15KB.
- **Image/media count mismatch**: If the output media count does not match the snapshot media count, the proposal is invalid. Re-scan snapshot files and fix before presenting to user.
- **Reflect MCP down at write time**: Save the proposed note as a local draft under `zk/drafts/<slug>.md` and inform the user to retry when MCP is available. Do not block the session.

### Evolver
- **Cannot write to files**: Report proposed changes as text diff for manual application.
- **Git operations fail**: Propose changes without committing.
- **Conflicting improvement signals**: Document the tension, don't force resolution.

## Session Continuity

If a session is interrupted:
1. Check `zk/reflections/` for partial output from today.
2. Check today's daily note (`zk/daily-notes/YYYY-MM-DD.md`) for a session write-back already written. Detect by descriptive heading that matches today's session topic. As a best-effort fallback, also scan for a legacy `#ai-reflection` section (pre-Phase-A content). The new alloy default carries no provenance tag, so the heading is the primary signal; the tag scan is historical-only.
3. Resume from the last completed step rather than restarting.
4. If unclear what was done, ask the user.

## Timeout Policy

- Local file reads: immediate — if `Read` fails, the file genuinely does not exist.
- Reflect MCP calls: 30 seconds before falling back (to local grep, or to skip)
- Readwise MCP calls: 30 seconds before reporting `/curate` as degraded
- Web searches: 15 seconds before skip
- Agent handoffs: No timeout (rely on maxTurns)
- Local writes (`zk/reflections/`, `zk/drafts/`, `zk/cache/`): 5 seconds
- Reflect write operations: 10 seconds, then queue as local draft under `zk/drafts/`
