# Error Handling & Graceful Degradation

Defines how agents handle failures without blocking sessions.

The mental model is **local-first**: `$OV/` is the authoritative read and write path. Plain markdown files on disk are always available (subject only to filesystem health). Readwise integration only matters for `/curate` inbox flows; its absence does not affect the knowledge base.

## Failure Hierarchy

Failures are ranked by severity. Handle at the lowest level possible.

### Level 1: Recoverable (handle silently)
- Grep returns empty → try alternative phrasing, broader pattern, or other language
- Note file shorter than expected → use what's available
- Framework file missing → skip framework, use first principles
- Previous reflection file missing → treat as first session

### Level 2: Degraded (warn and continue)
- **Readwise unreachable**: `/curate` is blocked. All other commands unaffected.
- **Target note missing from `$OV/`**: report the gap honestly. There is no remote fallback; if the user expected a file to exist, they need to author or re-import it.
- **Index files stale (>7 days)**: warn user, proceed with stale profile.
- **Multiple searches return empty**: report coverage gap, continue with available data.
- **Web search fails**: Scout/Thinker continue without external sources, note the limitation.

### Level 3: Blocking (stop and inform)
- `$OV/` directory missing or unreadable → the primary read path is gone. Guide the user to check filesystem / cloud-sync state.
- Profile files missing → cannot run reflection, guide user to `/introspect`.
- All goal data missing → cannot run review, suggest `/introspect`.
- Fundamental prompt misunderstanding → ask user to clarify.

## Agent-Specific Fallbacks

### Researcher
- **Semantic query returns empty**: Reframe the concept and retry `uv run scripts/semantic.py query`. Then try grep with synonym variants in both languages. Report the gap after 3 attempts.
- **Grep returns empty**: Try 3 alternative phrasings in both languages before reporting gap. Strategy: exact → synonym → semantic reframe → broader category.
- **Target note not in `$OV/`**: Report the gap honestly with `[DEGRADED: not found in $OV]`. There is no remote fallback.
- **Semantic script errors**: The script is stdlib-only and should not error. If it does (e.g., permission problem), report the stderr and fall back to Grep with synonym variants for the immediate query, then file an Evolver note.

### Synthesizer
- **No research brief received**: Read `$OV/` directly (bypass normal contract). Prefix output with `[DEGRADED: No research brief, synthesizing from direct reads]`.
- **Research brief has critical gaps**: Acknowledge gaps explicitly in output rather than filling with speculation.
- **Write failure to `<paths.reflections>/`**: Abort with a clear error — this is the primary write path and there is no further fallback. Report the filesystem error to the user.

### Reviewer
- **Cannot verify citation**: Mark as `UNVERIFIED` rather than `FAIL`. Distinguish "wrong" from "couldn't check".
- **`profile/directions.md` missing**: Skip goal coverage check, note in output.
- **Source note missing from `$OV/`**: Mark `UNVERIFIED`. Reviewer cannot fetch missing notes. An UNVERIFIED mark is the correct outcome.

### Challenger
- **No recent entries in `<paths.daily_notes>/`**: Use the latest reflection file in `<paths.reflections>/` as context instead.
- **No contradictions found**: This is fine — not every session has contradictions. Don't force them.
- **User emotional state unclear**: Default to neutral register.

### Thinker
- **Framework files missing**: Use built-in knowledge of frameworks (they're well-known models).
- **Web search fails**: Proceed without external sources, note the limitation.
- **No clear framework fit**: Use first principles thinking — always available.

### Curator
- **Content loss in merge**: Run Content Preservation Checklist (see `curator.md`). Scan snapshot files in `<paths.cache>/<operation>-*.md` for `![`, `http`, `[[`, table syntax before finalizing. If any media is found in snapshots but missing from output, block the proposal until fixed.
- **Snapshot missing at dispatch time**: If the orchestrator could not produce a snapshot at `<paths.cache>/<operation>-<slug>.md` for any source note (the local source could not be copied), abort the operation. Do not proceed with partial sources.
- **Source note disappears mid-session**: The dispatch-time snapshot in `<paths.cache>/` is authoritative. Continue working from the snapshot — the loss of the original is informational only. This is exactly what the snapshot step exists to protect against.
- **Size overflow**: Use 15KB as a working limit for individual notes — split larger drafts into numbered parts with cross-link headers.
- **Image/media count mismatch**: If the output media count does not match the snapshot media count, the proposal is invalid. Re-scan snapshot files and fix before presenting to user.
- **Local write failure**: Surface the filesystem error to the user; the orchestrator owns `Write`/`Edit` and is the only writer. Curator never writes.

### Evolver
- **Cannot write to files**: Report proposed changes as text diff for manual application.
- **Git operations fail**: Propose changes without committing.
- **Conflicting improvement signals**: Document the tension, don't force resolution.

## Session Continuity

If a session is interrupted:
1. Check `<paths.reflections>/` for partial output from today.
2. Check today's daily note (`<paths.daily_notes>/YYYY-MM-DD.md`) for a session write-back the user may have authored. The system never writes to daily notes, so any content there is user-authored; resume from where the user left off.
3. Resume from the last completed step rather than restarting.
4. If unclear what was done, ask the user.

## Timeout Policy

- Local file reads: immediate -- if `Read` fails, the file genuinely does not exist.
- Readwise calls: 30 seconds before reporting `/curate` as degraded
- Web searches: 15 seconds before skip
- Agent handoffs: No timeout (rely on maxTurns)
- Local writes (`<paths.reflections>/`, `<paths.wip>/`, `<paths.cache>/`): 5 seconds

## Escalation Rules

When failures cannot be handled at the agent level, escalate to the orchestrator.

### Agent to Orchestrator Triggers

| Trigger | Escalation |
|---------|-----------|
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
