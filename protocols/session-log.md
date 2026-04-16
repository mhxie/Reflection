# Session Log Protocol

Records the reasoning path of each session as a structured, machine-readable artifact. Session logs complement reflection files: reflections capture *conclusions* for the user; session logs capture *process* for the system.

## When to Write

At session end, immediately before (or alongside) the reflection file write. The orchestrator emits the session log. Subagents do not write session logs directly; their handoff data feeds into the orchestrator's log.

## Storage

- **File:** `zk/sessions/YYYY-MM-DD-<type>.md`
- **Types:** reflection, review, weekly, decision, exploration, energy-audit, reading, curate, introspect, meeting, deep-dive, system-review, prm
- **Collisions:** If multiple sessions of the same type run on the same day, append a sequence number: `YYYY-MM-DD-reflection-2.md`
- **Tier:** L2, same as `zk/reflections/` and `zk/daily-notes/`
- **Write method:** Local `Write` only. No MCP call. No user approval needed (system-facing artifact). If the write fails, warn and continue; do not block the session.

## Format

```markdown
---session-log---
session_id: YYYY-MM-DD-<type>[-N]
date: YYYY-MM-DD
type: <type>
duration_estimate: <minutes, rough>
model: <orchestrator model used>
---end-session-log-header---

## Agents Dispatched
| Agent | Task | Result | Turns Used |
|-------|------|--------|------------|

## Search Log
| Query | Tool | Hits | Top Result | Useful |
|-------|------|------|------------|--------|

## Gate Results
| Gate | Score/Pass | Notes |
|------|-----------|-------|

## Questions & Engagement
| Question | Depth | Landed | User Response |
|----------|-------|--------|---------------|

## Frameworks Applied
| Framework | Applied By | Fit Score | Cross-validated |
|-----------|-----------|-----------|-----------------|

## Continuity
- Previous session referenced: <session_id or "none">
- Seed planted: <next action / open question from this session>
- Callbacks checked: <list of previous seeds checked>

## Decisions & Branches
- <Timestamped prose of key routing decisions the orchestrator made>

## Anomalies
- <Anything unexpected: MCP failures, empty searches, user course corrections, degraded mode activations>

## Harness Assumptions Exercised
- <List any model-era assumptions that were load-bearing this session>
```

### Section Guidance

**Agents Dispatched:** One row per dispatch. For parallel dispatches, list on consecutive rows and note "(parallel)" in the Task column. Include agents that were dispatched but returned errors.

**Search Log:** Every `uv run scripts/semantic.py query` call and notable `Grep` search the orchestrator or agents issued. "Useful" is a boolean: did the results contribute to the session output?

**Gate Results:** From Reviewer handoffs (`review-check` type). Include gate number (1-4 per `quality-gates.md`), score, and pass/fail. Include revision loops if triggered.

**Questions & Engagement:** From Challenger handoffs (`challenge-set` type) and orchestrator's own reflective questions. Depth follows the Challenger taxonomy: surface, structural, paradigmatic, generative. "Landed" means the user gave a substantive response.

**Frameworks Applied:** From Thinker handoffs (`perspective` type). Fit score is the Thinker's self-assessed applicability (0-10).

**Decisions & Branches:** Free-form prose. Captures non-obvious routing decisions: "User requested Scout mid-session", "Reviewer scored 5.8, triggered revision loop round 1", "Skipped framework application (user in a rush)".

**Anomalies:** MCP connection failures, empty search results after retries, user course corrections ("actually, let's talk about X instead"), degraded mode activations (e.g., semantic.py fallback to lexical).

**Harness Assumptions Exercised:** References to `protocols/harness-assumptions.md` registry items that were load-bearing. Examples: "Researcher model=Opus (model-assignment)", "Profile stale >7d warning triggered (temporal-threshold)", "Loaded last 3 reflections (token-budget)".

## Queryability

Session logs are plain markdown with structured headings. No special tooling needed for v1.

| Intent | Query |
|--------|-------|
| Sessions where a gate failed | `Grep "NEEDS_REVISION\|REJECTED" zk/sessions/` |
| Sessions that dispatched Scout | `Grep "Scout" zk/sessions/` |
| Sessions with zero-hit searches | `Grep "0.*\|" zk/sessions/` in Search Log tables |
| Sessions with anomalies | `Grep "## Anomalies" -A 5 zk/sessions/` |
| Sessions by type | `Bash: ls zk/sessions/ \| grep -oP '(?<=\d{4}-\d{2}-\d{2}-)[a-z-]+' \| sort \| uniq -c` |
| Harness assumptions used | `Grep "harness-assumptions" zk/sessions/` |

## Relationship to Other Artifacts

| Artifact | Purpose | Audience |
|----------|---------|----------|
| `zk/reflections/YYYY-MM-DD-*.md` | Session conclusions, insights, next actions | User (human-readable) |
| `zk/sessions/YYYY-MM-DD-*.md` | Session process, agent dispatches, search effectiveness | System (meta-reflection, Evolver, continuity) |
| Reflect daily note write-back | Summary + backlinks for the knowledge graph | User (in Reflect app) |

Session logs do not replace reflection files. They are a parallel, system-facing record.
