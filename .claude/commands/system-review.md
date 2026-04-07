# System Review

Review a system-evolution bundle (protocols, agents, commands, CLAUDE.md, handoff docs) before committing. Runs internal reviewer + external reviewers (codex, gemini) in parallel.

## When to use

- After any change to `protocols/`, `.claude/agents/`, `.claude/commands/`, `CLAUDE.md`, `frameworks/`, or `scripts/`.
- When the user says "review the system changes", "run the reviewers", "review before commit".

Do **not** use for session output (the inline Reviewer gate handles that) or note operations (Gate 4 handles that).

## Flow

### 1. Preflight

```bash
git status --short
git diff --stat
```

If the working tree is clean, stop and tell the user there is nothing to review.

### 2. Dispatch in parallel (one message, multiple tool calls)

Send a **single** assistant message containing both tool calls:

- **Internal reviewer** — `Agent` tool, `subagent_type: reviewer`. Prompt: "Run System Diff Review + System Holistic Review on the uncommitted bundle. Walk `git diff` and `git status` yourself. Include the Phase scope brief (what moved, what was deferred). Return a scored rubric (0-10 on consistency, internal coherence, completeness, forward compatibility) and an issues list by severity (BLOCKER / SHOULD-FIX / NICE-TO-HAVE) with file:line pointers. Overall verdict: APPROVED / APPROVED_WITH_NOTES / NEEDS_REVISION / REJECTED."

- **External reviewers (codex + gemini)** — one `Bash` call, `timeout: 600000`:
  ```bash
  bash scripts/review.sh
  ```
  (Use `bash scripts/review.sh codex` or `bash scripts/review.sh gemini` for one only.) Reports land in `zk/cache/review-<timestamp>-{codex,gemini}.md`. The script runs the external CLIs in parallel, blocks on `wait`, includes untracked files in the diff sent to gemini, and treats a missing CLI as a soft-skip.

### 3. Synchronous wait (invoker contract)

**The orchestrator MUST block until BOTH tool calls have returned before doing anything else.** No streaming, no partial presentation, no interleaving with user chat.

- If the user sends a message while reviewers are running, acknowledge it in one line and say "reviewers still running — will synthesize once they return."
- Do not start drafting the synthesis until the internal reviewer has produced its handoff AND `bash scripts/review.sh` has exited.
- If the Bash call exits non-zero, read the stderr and the report files anyway (the script writes partial output even on failure) before deciding whether to retry or degrade.

This is a contract at the *invoker* level, not enforced by the script. The script just runs the CLIs in parallel and exits when they're all done; the orchestrator is responsible for not presenting anything until both its own tool calls have finished.

### 4. Synthesize

Only after both dispatches have returned. Read the two report files under `zk/cache/review-<timestamp>-{codex,gemini}.md`, combine with the internal reviewer's handoff, and present:

```
## System Review — Phase <N>

### Verdict
<worst verdict wins: REJECTED > NEEDS_REVISION > APPROVED_WITH_NOTES > APPROVED>

### Blockers
- [source] file:line — issue

### Convergent findings
- issue (flagged by: internal, codex, gemini)

### Divergent findings
- issue (internal: yes, codex: no) — resolution: ...

### Scores
- Internal reviewer: X/10 on <dimensions>
- Codex: <one-line summary>
- Gemini: <one-line summary>
```

Then ask the user: "Address the blockers and re-review, or proceed to commit?"

## Tiers (from `protocols/orchestrator.md`)

| Tier | Runs | When |
|---|---|---|
| 1 | Internal holistic only | Tiny scoped change |
| 2 | Internal holistic + diff | Single-area change |
| 3 | Tier 2 + codex | Cross-cutting, low-risk (default for evolution bundles) |
| 4 | Tier 3 + gemini | Architecture-level, multi-phase |

If the Evolver specified a tier in its handoff, honor it. Otherwise default to **Tier 3 (internal + codex)** or **Tier 4 (internal + codex + gemini)** for architecture-level bundles.

## Cross-references

- `scripts/review.sh` — the actual invocation (prompts, flags, parallelism)
- `protocols/orchestrator.md` → Review Tiers
- `protocols/agent-handoff.md` → `system-review-request` contract
- `.claude/agents/reviewer.md` → internal reviewer definition
