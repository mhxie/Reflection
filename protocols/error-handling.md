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
- **Local mirror stale** (today's daily note not yet synced from Reflect): the **orchestrator** falls through to `get_daily_note(date: "<today>")` for that one read. Subagents do not have the tool; if a subagent needs it, it flags `needs: get_daily_note(today)` in its handoff and the orchestrator fetches.
- **Target note genuinely missing from local mirror**: report the gap honestly. There is no generic `get_note` / `search_notes` fallback — subagents do not have these tools. The orchestrator-side `get_note` calls that remain are narrow: (a) the curator snapshot flow in `protocols/agent-handoff.md`, (b) `/sync` Phase 3 verification after `create_note`, and (c) Curator self-verification of its own `create_note` writes. Nothing else.
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
- **Semantic query returns empty**: Reframe the concept and retry `uv run scripts/semantic.py query`. Then try grep with synonym variants in both languages. Report the gap after 3 attempts.
- **Grep returns empty**: Try 3 alternative phrasings in both languages before reporting gap. Strategy: exact → synonym → semantic reframe → broader category.
- **Target note not in local mirror**: Report the gap honestly with `[DEGRADED: not in local mirror]`. Researcher has no Reflect MCP tools. If the gap is specifically today's daily note, flag `needs: get_daily_note(today)` and let the orchestrator fetch.
- **Semantic script errors**: The script is stdlib-only and should not error. If it does (e.g., permission problem), report the stderr and fall back to Grep with synonym variants for the immediate query, then file an Evolver note.

### Synthesizer
- **No research brief received**: Read `zk/` directly (bypass normal contract). Prefix output with `[DEGRADED: No research brief, synthesizing from direct reads]`.
- **Research brief has critical gaps**: Acknowledge gaps explicitly in output rather than filling with speculation.
- **Write failure to `zk/reflections/`**: Abort with a clear error — this is the primary write path and there is no further fallback. Report the filesystem error to the user.

### Reviewer
- **Cannot verify citation**: Mark as `UNVERIFIED` rather than `FAIL`. Distinguish "wrong" from "couldn't check".
- **`profile/directions.md` missing**: Skip goal coverage check, note in output.
- **Source note not in local mirror**: Mark `UNVERIFIED`. Reviewer has no Reflect MCP tools and cannot fetch missing notes. Do not escalate to the orchestrator for individual citation verification — an UNVERIFIED mark is the correct outcome.

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

- Local file reads: immediate -- if `Read` fails, the file genuinely does not exist.
- Reflect MCP calls: 30 seconds before falling back (to local grep, or to skip)
- Readwise MCP calls: 30 seconds before reporting `/curate` as degraded
- Web searches: 15 seconds before skip
- Agent handoffs: No timeout (rely on maxTurns)
- Local writes (`zk/reflections/`, `zk/drafts/`, `zk/cache/`): 5 seconds
- Reflect write operations: 10 seconds, then queue as local draft under `zk/drafts/`

## Escalation Rules

When failures cannot be handled at the agent level, escalate to the orchestrator.

### Agent to Orchestrator Triggers

| Trigger | Escalation |
|---------|-----------|
| MCP connection failed after 3 retries | Switch to degraded mode, inform user |
| Contradictory evidence found | Present both sides, let user resolve |
| User emotional distress detected | Shift to supportive mode, pause challenging questions |
| Scope creep (session expanding beyond command intent) | Check with user if they want to continue or refocus |
| Framework does not fit | Report honestly rather than force-fitting |

### Orchestrator to User Triggers

| Trigger | Action |
|---------|--------|
| 2 revision rounds failed | Deliver with caveats, explain what could not be fixed |
| No relevant notes found for query | Tell user honestly, suggest alternative angles |
| System conflict (agents disagree) | Present both perspectives transparently |
| Session quality declining | Suggest ending and returning fresh |

### Emotional Escalation

When the user's emotional state shifts during a session:

| Signal | Response |
|--------|----------|
| Short, terse answers | Check in: "Would you rather pause here?" |
| Expressing frustration | Validate, do not analyze: "That sounds frustrating." |
| Avoiding a topic | Note it gently once, do not push |
| Energy dropping | Offer to wrap up with a quick summary |
| Excited about something | Ride the energy, go deeper on what excites them |

Never push through emotional resistance for the sake of "completing" a session. A half-session that respects the user is worth more than a full session that ignores them.

### Escalation Anti-Patterns

1. Do not hide failures. If something went wrong, say so.
2. Do not retry indefinitely. 3 retries max for any operation.
3. Do not blame the user. "I couldn't find notes about X" not "You haven't written about X."
4. Do not lower the bar silently. If delivering lower-quality output, say why.
5. Do not escalate everything. Use judgment -- minor issues can be handled inline.
