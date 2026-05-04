# System Review

Review a system-evolution bundle (protocols, agents, commands, CLAUDE.md, handoff docs) before committing. Runs internal reviewer + external reviewers (codex + direct-api / DeepSeek Pro) in parallel.

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

### 1b. Privacy gate (blocking)

```bash
uv run scripts/privacy_check.py --json
```

Parse stdout as JSON. `--json` mode emits the document on every run regardless of exit code; `exit 1` is the script's normal "hits found" signal, not a script error.

Match top-to-bottom — first matching row wins. Field defaults when keys are absent: `zk_missing` → `false` (only the missing-vault payload sets it); `vacuous_gate` → `false` (only the empty-dirs payload sets it); `hit_count` → `len(hits)` (only the skip payloads omit it).

| JSON parses? | zk_missing | vacuous_gate | hit_count | Action |
|---|---|---|---|---|
| Yes | true | any | any (often absent) | Soft-skip; note "privacy gate skipped (vault not available)" in synthesis. Proceed to Step 2. |
| Yes | any | true | any (often absent) | Soft-skip; note "privacy gate skipped (no private dirs to scan)" in synthesis. Proceed to Step 2. |
| Yes | false | false | >0 | Abort with `NEEDS_REVISION`. Present each `hits` entry verbatim (`file:line` + `private_title`). Do not dispatch reviewers; fix leaks, re-run `/system-review`. |
| Yes | false | false | 0 | Proceed to Step 2. |
| No, OR stdout empty, OR exit ≥2 with no JSON | any | any | any | Real script error. Surface stderr, soft-skip, note "privacy gate skipped (script error)" in synthesis. |

The script scans tracked files PLUS untracked-but-not-ignored files (per `tracked_files()` in `scripts/privacy_check.py`), so a brand-new command file with a leak is caught before it is staged.

Rationale: privacy leaks are a hard veto regardless of score. Catching them deterministically before dispatching the expensive external reviewers saves tokens and prevents NEEDS_REVISION cycles caused by mechanical issues a script already knows. Mirrors `/lint` Phase 0c.

### 1c. Semantic privacy double-guard (blocking, cross-provider)

The mechanical script in 1b only matches filename stems under `$OV/` and wikilink targets. It misses **semantic** leaks: real names, restaurants, $-amount + deadline pairs, demographic phrases, personal taxonomies. Step 1c closes that gap with the privacy-reviewer's two voices (declared in `harness/agents.toml`). Cross-provider disagreement carries more diagnostic weight than two samples of the same model.

**Run only after 1b returns `hit_count: 0`** (or soft-skips). If 1b aborted with hits, do not dispatch 1c — fix 1b first.

Dispatch **both legs in parallel — single message, one `Agent` tool call AND one `Bash` tool call**:

**Leg A — Anthropic side (`Agent` tool, `subagent_type: privacy-reviewer`):**

> Privacy review the uncommitted bundle. Walk `git status --short` and `git diff HEAD --` yourself; for untracked-but-not-ignored files, `Read` them in full. Cross-reference `profile/` files (canonical config home; gitignored but on disk) to detect taxonomy mirroring and value coincidences with what's about to be committed. Apply all leak categories from your agent definition. Return verdict per the format in your spec. You are instance `A` (Anthropic leg); do not coordinate with the direct-api leg.

**Leg B — direct-api side (`Bash` tool, single call):**

```bash
{
  echo 'Privacy review the uncommitted bundle. Identify semantic leaks: real names, restaurants, $-amount + deadline pairs, demographic phrases, personal taxonomies, employer slugs that the mechanical filename-stem scanner misses. You are instance B (direct-api leg); do not coordinate with the Anthropic leg. Output one of: CLEAN | NEEDS_REVISION (with SHOULD-FIX list) | BLOCKER (with leak descriptions and file:line pointers).'
  echo
  echo '--- DIFF ---'
  git diff HEAD --
  echo
  echo '--- UNTRACKED FILES ---'
  for f in $(git ls-files --others --exclude-standard); do
    echo "=== $f ==="
    cat "$f"
  done
} | uv run scripts/chat_completion.py --model deepseek_pro --max-tokens 0 --prompt -
```

Both legs return verdicts (CLEAN / NEEDS_REVISION / BLOCKER). The direct-api leg returns `message.content`; treat it as the verdict.

**Verdict aggregation** (most-paranoid wins):

| Leg A (Anthropic) | Leg B (direct-api) | Action |
|---|---|---|
| CLEAN | CLEAN | Proceed to Step 2 |
| CLEAN | NEEDS_REVISION | Surface SHOULD-FIX list as concerns; proceed to Step 2 (do not block) |
| NEEDS_REVISION | NEEDS_REVISION | Surface union of SHOULD-FIX as concerns; proceed to Step 2 |
| Either | BLOCKER | **Abort** with `NEEDS_REVISION`. Present union of BLOCKERs verbatim. Do not dispatch Step 2 reviewers. Fix and re-run `/system-review`. |

If the direct-api leg soft-skips (exit 2 — api_env unset), note "direct-api leg unavailable; cross-provider check downgraded to single-leg Anthropic" in the synthesis and continue with Leg A's verdict only. Do not block on direct-api availability.

Cross-provider rationale: two instances of the same model from the same provider have correlated failure modes (training lineage, tokenizer, corpus). The privacy-reviewer's two voices share none of those. Disagreement here is more likely to surface a real leak than two same-model samples would.

### 2. Dispatch in parallel (one message, multiple tool calls)

Send a **single** assistant message containing both tool calls:

- **Internal reviewer** — `Agent` tool, `subagent_type: reviewer`. Prompt: "Run System Diff Review + System Holistic Review on the uncommitted bundle. Walk `git diff` and `git status` yourself. Include the Phase scope brief (what moved, what was deferred). Return: (a) 4-dim score card (Contract integrity, Wiring correctness, Bug absence, Claim fidelity, each 0-10); (b) antipattern scan walking every entry in `protocols/antipatterns.md` (count entries from the file at scan time) with FLAG or N/A-with-reason for each; (c) concern list with severity (BLOCKER / SHOULD-FIX / NICE-TO-HAVE) and `file:line` pointers, minimum 3 or a 'Hunted but not found' section; (d) pre-mortem one-liner; (e) scope clarifier block. Overall verdict per reviewer.md Scoring: APPROVED / NEEDS_REVISION / REJECTED (no APPROVED_WITH_NOTES for system reviews; any dim <6 or missing artifact forces NEEDS_REVISION)."

- **External reviewers (codex + direct-api / DeepSeek Pro)** — one `Bash` call, `timeout: 600000`:
  ```bash
  bash scripts/review.sh
  ```
  (Use `bash scripts/review.sh codex`, `bash scripts/review.sh deepseek`, or the legacy `bash scripts/review.sh gemini` for one only.) Reports land in `$OV/cache/review-<timestamp>-{codex,direct}.md` (the direct-api leg writes `-direct.md`). The script runs both reviewers in parallel, blocks on `wait`, includes untracked files in the diff sent to each, and treats a missing CLI / unset `DS_API` as a soft-skip.

### 3. Synchronous wait (invoker contract)

**The orchestrator MUST block until BOTH tool calls have returned before doing anything else.** No streaming, no partial presentation, no interleaving with user chat.

- If the user sends a message while reviewers are running, acknowledge it in one line and say "reviewers still running — will synthesize once they return."
- Do not start drafting the synthesis until the internal reviewer has produced its handoff AND `bash scripts/review.sh` has exited.
- If the Bash call exits non-zero, read the stderr and the report files anyway (the script writes partial output even on failure) before deciding whether to retry or degrade.

This is a contract at the *invoker* level, not enforced by the script. The script just runs the CLIs in parallel and exits when they're all done; the orchestrator is responsible for not presenting anything until both its own tool calls have finished.

### 4. Synthesize

Only after both dispatches have returned. Read the two report files under `$OV/cache/review-<timestamp>-{codex,direct}.md`, combine with the internal reviewer's handoff, and present.

**External verdict mapping for system reviews:** External reviewers (codex, direct-api) may emit `APPROVED_WITH_NOTES`. System reviews do not admit a notes-only verdict; treat external `APPROVED_WITH_NOTES` as `NEEDS_REVISION` for the merge ladder. The "notes" themselves still surface as concerns in the synthesis output. This applies only when synthesizing system reviews; session reviews preserve the original verdict.

Synthesis output:

```
## System Review — Phase <N>

### Verdict
<worst verdict wins: REJECTED > NEEDS_REVISION > APPROVED>

Floor check: any internal dim <6 OR any required artifact missing -> NEEDS_REVISION regardless of overall score.

### Required artifacts (internal reviewer)
- Antipattern scan: [complete N/N for catalog entries | missing entries: ...]
- Concern floor: [N surfaced | hunted-but-not-found rationale]
- Pre-mortem: "If this fails within 30 days, most likely cause is: ..."
- Scope clarifier: "What this change does NOT do: ..."

### Blockers
- [source] file:line - issue

### Convergent findings
- issue (flagged by: internal, codex, direct-api)

### Divergent findings
- issue (internal: yes, codex: no, direct-api: no) - resolution: ...

### Scores
- Internal reviewer: X/10 avg across 4 dims; dim floor [passed | BREACHED on <dim>]
- Codex: <one-line summary>
- Direct-api (DeepSeek Pro): <one-line summary>
```

Then ask the user: "Address the blockers and re-review, or proceed to commit?"

## Tiers (from `protocols/orchestrator.md`)

| Tier | Runs | When |
|---|---|---|
| 1 | Internal holistic only | Tiny scoped change |
| 2 | Internal holistic + diff | Single-area change |
| 3 | Tier 2 + codex | Cross-cutting, low-risk (default for evolution bundles) |
| 4 | Tier 3 + direct-api (DeepSeek Pro) | Architecture-level, multi-phase |

If the Evolver specified a tier in its handoff, honor it. Otherwise default to **Tier 3 (internal + codex)** or **Tier 4 (internal + codex + direct-api)** for architecture-level bundles.

## Cross-references

- `scripts/review.sh` — the actual invocation (prompts, flags, parallelism)
- `protocols/orchestrator.md` → Review Tiers
- `protocols/agent-handoff.md` → `system-review-request` contract
- `.claude/agents/reviewer.md` → internal reviewer definition
- `.claude/agents/privacy-reviewer.md` → semantic privacy guard (intrinsically dual; both voices fire in Step 1c)
