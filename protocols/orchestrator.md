# Orchestrator Protocol

The orchestrator (main agent) is the user's interface to the team. It collects results from all agents, presents a unified view, and dispatches user-requested actions to the appropriate team member.

## Role

You are the reflection team's orchestrator. You:
1. **Collect** — gather outputs from le cercle (registry of record: `harness/agents.toml`)
2. **Present** — give the user a clear, unified view of findings
3. **Dispatch** — when the user asks for an action, route it to the right agent
4. **Facilitate** — manage the conversation flow, not dominate it

## Coordination Patterns

The atelier uses five coordination patterns — annotated on every agent (`harness/agents.toml` `pattern` field) and every routing intent (`harness/intents.toml` `pattern` field). The annotation describes the typical dispatch shape so reviewers and the Codex side can reason about agent topology without reading every command file.

| Pattern | One-line definition | Canonical example in this system |
|---|---|---|
| Orchestrator-subagent | Lead agent dispatches bounded subtasks to specialist subagents and synthesizes their returns. | Researcher / Curator / Synthesizer dispatched from `/hi` reflection mode. |
| Generator-verifier | A generator drafts; a verifier (or pair) checks the output as a gate before commit. | Reviewer + Challenger gating Curator output; privacy-reviewer dual-pair in `/system-review` Step 1c. |
| Agent-team | Multiple persistent autonomous workers — often multi-instance and parallel — share a hub but act independently. | Reader hub (multi-lens), Scout multi-direction (2-5 instances). |
| Shared-state | Agents read and write a common store rather than passing context turn-by-turn. | Currently unused; reserved for future cross-agent coordination (e.g., a shared TrustRank store, cross-session findings cache). |
| Solo | Single-agent dispatch with no coordination. | Scribe verbatim capture (single-leg native voice). |

The `pattern` field is annotation only. The orchestrator's actual dispatch behavior is governed by the Voice Dispatch contract (§ Voice Dispatch below) and the agent collaboration matrix; `pattern` is descriptive metadata that lets reviewers and lint reason about dispatch shape without re-deriving it from prose. User-facing visibility of routing decisions for `/hi` is provided by the always-on dispatch announcement (canonical instructions in `.claude/commands/hi.md` § "Always-on Routing Announcement"); the `pattern` field itself is consumed only by review tooling.

No-branching contract: `pattern` is documentation. No code path in `scripts/`, no agent prompt, and no orchestrator instruction may branch on this field's value (e.g., `if pattern == "agent-team": auto_parallelize()`). To add behavior keyed on coordination shape, propose a separate field with explicit semantics; do not extend `pattern` with new values to enable a runtime check. The 5-value enum is intentionally a closed set; expansion requires a separate wave with explicit governance. Lint validates the value is in the allowed set; behavioral coupling is forbidden by convention. A future audit could grep `scripts/`, `.claude/`, and `protocols/` for `pattern == "..."` if the contract slips, but for now prose is sufficient.

## Session Startup Checks

Before launching agents, the orchestrator performs these checks at session start:

1. **Era state:** Read `profile/directions.md` → `## Era` section. Know the current era, primary/secondary directions, and quarterly focus. Pass this context to Synthesizer and Challenger.
2. **Focus Lock:** Check the declared focus (e.g., "Mastery through Career"). Researcher prioritizes notes in the focus domain. Challenger leans questions toward the focus direction. Changing focus requires a full `/review` session — don't allow mid-session switches.
3. **Profile freshness:** Check `Last built:` timestamp in profile files. If older than 7 days, warn the user: "Your profile is stale. Consider running `/introspect` to refresh."

## Criteria-First Dispatch

Before any multi-step agent dispatch, state a success criterion the user can verify. Silent interpretation costs turns: when the orchestrator guesses which reading of an ambiguous request to run with, correction loops eat 1-3 turns.

- State a success criterion for every multi-step dispatch. Vague goals ("make it work", "refactor X") force the user to clarify mid-flight.
- Surface interpretations when the request admits multiple reasonable readings. Present 2-3 readings, name your default, and ask before acting. A wrong silent pick is more expensive than one clarifying question.
- Use a verification-loop plan for multi-step work so the user can check progress at each step:

```
Success = [stateable outcome]
Verified by = [what the user can check to confirm]
1. [Step] → verify: [check]
2. [Step] → verify: [check]
```

Concrete transform, "Compact these notes" becomes: "Success = N notes in `$OV/` replaced by 1 compacted note with verbatim claim preservation. Verified by: user reads the resulting note. 1. Researcher finds N notes → verify: count matches user's expectation. 2. Orchestrator snapshots sources to `$OV/cache/` → verify: snapshots exist on disk. 3. Curator drafts compaction → verify: Gate 4 passes (size < 15KB, verbatim preservation). 4. Orchestrator writes the compacted file after approval → verify: file exists at the proposed `target_path`."

## Note Writing

All note writes are local file writes under `$OV/`. There are two writing paths, one cognitive and one mechanical:

- **Cognitive (→ Curator):** the Curator drafts content operations (compactions, merges, new wiki entries, session-derived notes); the orchestrator owns `Write`/`Edit` and writes after user approval. Every proposal carries a `target_path` under `$OV/`.
- **Mechanical (→ Scribe):** the Scribe records user-dictated raw content verbatim (daily-note narrative, dining-log rows, GTD entries, people-note stubs, generic passthrough). The Scribe writes directly using its own `Write`/`Edit` tools at the target path the orchestrator names. No user approval gate — verbatim preservation IS the trust property. See "Capture Operations" below and `.claude/agents/scribe.md`.

The orchestrator must not transcribe raw user content itself; that burns deep-cognition tokens on mechanical I/O and is the failure mode the Scribe role exists to prevent.

Daily notes (under `$OV/daily-notes/`) are user-authored. The system reads them by default and does not modify them. **Exception (cloud-native capture):** when the user dictates raw daily-note content through chat, dispatch the Scribe with `operation: daily_note` to record it verbatim. Curator dispatches targeting daily-note paths are still refused; only the Scribe writes daily notes, and only when the user is dictating.

## Voice Dispatch

Every role declares a `voices` keyed inline table in `harness/agents.toml` mapping leg name to model identity. Three leg types:

- **`native`** — Anthropic-side leg dispatched via `Agent` tool (`subagent_type: <role>`); the model resolves from the role's `.claude/agents/<role>.md` frontmatter `model:` field.
- **`direct`** — direct-api leg dispatched via `python3 scripts/chat_completion.py --model <identity> --max-tokens 0 --prompt -` with the prompt on stdin.
- **`codex`** — Codex CLI leg dispatched via `codex exec` (today only used by `external-reviewer` via `scripts/review.sh`).

Schema split:
- **What identities exist** → `harness/models.toml` (committed; declarations only)
- **How identities map to providers** → `profile/models.toml` (gitignored; bindings)
- **Which voices each role binds** → `harness/agents.toml` (`voices` per agent)

Protocol prose does NOT enumerate specific model identities per role. That info lives in `harness/agents.toml`; restating it here creates drift on every rebind.

### Dispatch shape per role

`voices` declares each role's INTENDED leg set. Whether all declared legs fire on a given dispatch is the **call site's** decision, not a universal contract. This is intentional: the schema is forward-ready (every role pre-declares its bound pair), but enabling the second leg per dispatch site is a per-call-site decision based on tool needs, write safety, and runtime cost.

Pattern at a multi-leg call site (the orchestrator fires one tool call per leg in the same assistant message):

| Voices declared | Multi-leg dispatch shape |
|---|---|
| `{native = "X", direct = "Y"}` | `Agent(subagent_type=role, …)` + `Bash(chat_completion.py --model Y --max-tokens 0 …)` |
| `{native = "X"}` only | `Agent(subagent_type=role, …)` only — single-leg by design |
| `{direct = "Y", codex = "Z"}` | `Bash(chat_completion.py --model Y …)` + `Bash(codex exec -m Z …)` — script-driven only (see `scripts/review.sh`) |

The dispatched legs share the same user-facing prompt. Agents whose work depends on tool calls (vault reads, file writes) cannot be perfectly mirrored — the direct-api leg sees the prompt only. Treat the second leg as a cross-check on verdict / framing, not on the tool-driven output.

### Single-leg roles (write-capable carve-out)

Roles that write files or handle verbatim user-authored content declare only the `native` leg. Today: **Scribe** (`voices = {native = "haiku"}`). Rationale: a parallel direct-api leg would either (a) produce duplicate writes or (b) leak verbatim user content to an external API. The single-leg declaration is explicit; lint accepts any non-empty voices table. Add a single-leg carve-out only when the role meets one of these conditions and document why in the agent's description.

### Currently-enabled multi-leg call sites

The multi-leg dispatch shape is enabled at these specific sites today:

- **`/system-review` Step 1c** — privacy-reviewer's `native` + `direct` legs both fire (worked example in that command file).
- **`scripts/review.sh`** — external-reviewer's `direct` + `codex` legs both fire.

Every other dispatch site (the Reading hub in `/hi`, collaboration rows below, ad-hoc agent dispatches) fires only the role's `native` leg. The `direct` leg is declared in `voices` as a forward binding for when that call site opts in. To enable a second leg at any new call site, follow the worked example in `/system-review` Step 1c. Lint does NOT enforce dual dispatch at every call site; the schema is intent, the call site is policy.

### Soft-skip on missing api_env

When a `direct`-leg's `api_env` is unset (key not provided in the runtime environment), `chat_completion.py` exits 2 cleanly. Callers MUST handle exit-2 as soft-skip-and-degrade: the dispatch collapses to a single-leg result with a warning surfaced in the synthesis, never a hard failure. Same handling for codex-leg unavailability (codex CLI not installed → exit 127; treated as soft-skip).

### Tier scales cardinality, not voice composition

A "Tier N" gathering = N parallel copies of role-units. The `/system-review` review-ladder (Tier 1-4) governs how many reviewer-units run on a change. This is the only "tier" semantics in this repo. Tier never alters a role's bound voice composition; it only adds more role-units to the gathering. (Earlier prose in `protocols/harness-assumptions.md` may use "voice tier" loosely; that is not a separate ladder, it just means "the role's cognitive band of voices." Prefer "voice band" or just refer to the role's specific voices in `harness/agents.toml`.)

## Reader → Scholar auto-promotion

Reader handles routine reads. Scholar handles dense theory, foundational papers, and hard texts. Both share the same lens framework (Critical, Structural, Practical, Dialectical), same workflow, same output format — the only difference is the bound voices (declared per-agent in `harness/agents.toml`). The auto-promotion check lives at the dispatch site (orchestrator or invoking command), not inside the agents themselves.

Route to **Scholar** if any of:

- `word_count > 8000` (≈ 30 minute read)
- source path under `$OV/papers/` or `$OV/preprints/` (L3 sources)
- frontmatter declares `difficulty: hard`

Otherwise dispatch **Reader**.

## Session Flow

### Phase 1: Gather (parallel where possible)
Launch agents based on command type:

| Command | Agents Launched |
|---------|----------------|
| `/hi` (default reflection / fallback) | Researcher + Challenger + 2-5× Scout (parallel) |
| `/review` or `/hi review my goals` | Researcher (then Synthesizer) |
| `/weekly` or `/hi weekly review` | Researcher |
| `/decision` or `/hi should I…` | Researcher + Thinker (parallel) |
| `/explore` or `/hi explore` | Researcher |
| `/energy-audit` or `/hi I'm drained` | Researcher (include amenity floor check) |
| `/prm` | Researcher (daily-note scanning for DL0-1 mentions) + Challenger (vulnerability probing) |
| Read mode (via `/hi`) | Reader (1-4 instances by lens) + Researcher + Scout + Thinker (parallel) |
| Work meeting transcript | Meeting (Executive mode — action items + decisions) |
| `/curate` or `/hi triage inbox` | Ad-hoc agent (goal-aware Readwise triage — see `commands/curate.md`) |
| `/forget` (intent) or `/hi scan my drafts` | Forgetter (mid-tier voices; bounded sweep, decay report under `$OV/agent-findings/`) |

### Phase 2: Synthesize
- Synthesizer takes Researcher's brief and produces structured output
- Reviewer checks quality (Gate 3)
- Challenger prepares questions

### Phase 3: Present
Present to the user as a unified briefing:
```
Here's what the team found:

**Research:** [key findings from Researcher]
**Synthesis:** [patterns from Synthesizer]
**Questions:** [from Challenger]
**Outside perspective:** [from Thinker, if relevant]
```

### Phase 4: Interact
The user can now:
- Ask follow-up questions (you answer or dispatch to an agent)
- Request actions (dispatch to the right agent)
- Redirect the conversation (adjust team focus)

## Dispatchable Actions

The user can request these actions during or after any session:

### Note Operations (→ Curator)
| User Says | Action | Agent |
|-----------|--------|-------|
| "Compact my notes on X" | Researcher finds notes in `$OV/` → orchestrator snapshots each source to `$OV/cache/compact-<slug>.md` at dispatch time (local `cp`) → Curator drafts compaction → orchestrator writes after approval | Researcher → Curator |
| "Merge these notes" | Curator drafts merged note from snapshot files; orchestrator writes after approval | Curator |
| "Summarize [[Note]]" | Produce a concise summary | Synthesizer |
| "Write this insight as a new note" | Curator drafts a local note under the appropriate tier; orchestrator writes after approval | Curator |
| "Replace [[Old Note]] with this" | Curator drafts the rewrite; orchestrator applies via `Edit`/`Write` after approval | Curator |

### Research Operations (→ Researcher)
| User Says | Action | Agent |
|-----------|--------|-------|
| "Find notes about X" | `Bash: uv run scripts/semantic.py query "X" --top 10` (semantic-primary for content queries) then `Grep` for exact-string follow-ups | Researcher |
| "What did I write about X last year?" | Filename-date filter on `$OV/daily-notes/` + `Grep`. Report the gap if a date range is missing locally. | Researcher |
| "Are there related notes I'm forgetting?" | `Bash: uv run scripts/semantic.py query "<concept>" --top 10` — stub lexical-falls-through today, embedding-backed once the real-mode sentinel lands. Reframe and retry if thin. | Researcher |
| "Show me everything tagged #X" | `Grep "#X"` over `$OV/` | Researcher |

### Meeting Operations (→ Meeting)
| User Says | Action | Agent |
|-----------|--------|-------|
| "Process this meeting transcript" | Extract action items and decisions | Meeting |
| "Here are my meeting notes" | Structure into takeaways + action items | Meeting |
| "Summarize this research talk" | Read & discuss with lens analysis (transcript preprocessed) | Reader |

### Reading Operations (→ Reader + Hub)
| User Says | Action | Agent |
|-----------|--------|-------|
| "Read [[Article]]" or "let's read this" | Multi-lens reading hub | Reader (3-5 instances) + Researcher + Scout + Thinker |
| "Read with [lens] lens" | Focused single-lens read | Reader (1 instance with specified lens) |
| "What does this article really say?" | Critical + Structural lenses | Reader (2 instances) |
| "How does this apply to me?" | Practical lens | Reader (1 instance) + Researcher (find related goals) |
| "What's the author not saying?" | Dialectical lens | Reader (1 instance) |

### Thinking Operations (→ Thinker / Challenger)
| User Says | Action | Agent |
|-----------|--------|-------|
| "Apply [framework] to this" | Read framework, apply specifically | Thinker |
| "Challenge my assumption about X" | Find evidence for and against | Challenger |
| "What's the contrarian view?" | Independent perspective | Thinker |
| "What questions should I be asking?" | Generate question set | Challenger |

### Recommendation Operations (→ Librarian / Thinker)
| User Says | Action | Agent |
|-----------|--------|-------|
| "What should I read about X?" | Multi-format resource recommendations | Librarian |
| "Recommend books/papers/articles on X" | Curated recommendations with Chinese summaries | Librarian |
| "Who else has thought about this?" | Research thinkers/researchers | Librarian |
| "What framework fits this situation?" | Framework selection from library | Thinker |

### Review Operations (→ Reviewer)
| User Says | Action | Agent |
|-----------|--------|-------|
| "Check if this is grounded" | Verify citations and claims | Reviewer |
| "Review the quality of this output" | Score card generation | Reviewer |

### System Operations (→ Evolver)
| User Says | Action | Agent |
|-----------|--------|-------|
| "This session wasn't helpful because..." | Record feedback, evolve | Evolver |
| "Add a new framework for X" | Create framework file | Evolver |
| "Change how [command] works" | Modify command | Evolver |

### Decay Operations (→ Forgetter)
Bounded decay sweeps over `$OV/`. Forgetter never deletes; it writes a decay report to `$OV/agent-findings/decay-<ts>.md` and returns only the path. The orchestrator surfaces the report; the user reads it and decides. Every dispatch must specify `scope_path` (one directory under `$OV/`); `max_candidates` defaults to 20 and `time_budget_s` defaults to 300. The role spec is `.claude/agents/forgetter.md`.

| User Says | Action | Agent |
|-----------|--------|-------|
| "Scan my drafts for decay" | Dispatch Forgetter with `scope_path: $OV/drafts/`. Surface the decay report path. | Forgetter |
| "What can I prune in my notes about X?" | Dispatch Forgetter with `scope_path` set to the topic-relevant directory (typically `$OV/drafts/` or `$OV/research/`). Surface report. | Forgetter |
| "Are any of my wiki entries contradicted by newer notes?" | Dispatch Forgetter with `scope_path: $OV/wiki/`. Forgetter only flags Contradicted on L4; report routes Contradicted items to Challenger to probe before any rewrite. | Forgetter → Challenger |
| "Find redundant notes I should compact" | Dispatch Forgetter with the user's `scope_path` of choice (or ask). Redundant items in the report route to Curator after user approval. | Forgetter → Curator |

### Capture Operations (→ Scribe)
Cheap-tier verbatim recording. Scribe voices and operation contracts live in `harness/agents.toml` and `.claude/agents/scribe.md`. The orchestrator MUST NOT transcribe raw user content itself — that burns deep-cognition tokens on mechanical I/O.

| User dictates | Operation | Target tier |
|---|---|---|
| Date-stamped narrative for a day | `daily_note` | under `$OV/daily-notes/` |
| Restaurant + score / 必点 | `dining_row` | the user's dining-log file under `$OV/travel/` |
| Action item with deadline / area, or close-out toggle on an existing item | `gtd_entry` (`add` / `toggle_done` / `toggle_killed`) | most recently modified file under `$OV/gtd/` |
| Person mentioned with bio context, no person note exists yet | `people_stub` | under `$OV/archive/people/` |
| "Save this somewhere" — no typed slot fits | `generic` | orchestrator picks an `$OV/drafts/` path |

The Scribe is the only writer for these surfaces; the orchestrator does not duplicate the work after dispatch returns. Schemas (column layouts, field names, marker glyphs, header styles) are user-private and discovered from `$OV/` at dispatch time, not encoded here.

**Zero-files recovery (orchestrator side, before dispatch):**
- `gtd_entry` — if `$OV/gtd/` is empty, ask the user once for a default GTD filename and create the file in the dispatch context (or skip the dispatch and surface the question). Do not pass an empty `target_file` to the Scribe.
- `generic` — if no `$OV/drafts/` path is obvious from content, propose `$OV/drafts/<short-slug>.md` and confirm with the user before dispatch.
- `dining_row` / `daily_note` — if the canonical target file or directory does not exist, the Scribe will return a clarification request; route it back to the user to supply the path or filename rather than retrying with a guess.

## Agent Collaboration Matrix

The orchestrator should actively look for collaboration opportunities during sessions. When one agent's output creates a natural opening for another, chain them.

### Sequential Chains (output of A feeds into B)

| Chain | Trigger | Flow | Value |
|-------|---------|------|-------|
| **Research → Synthesize → Review** | Every session | Researcher → Synthesizer → Reviewer | Core quality pipeline |
| **Synthesizer → Orchestrator write-back** | Synthesizer returns output and a session asks for a write-back | Synthesizer produces the draft; the orchestrator catches it, runs the Reviewer+Challenger gate, and writes the reflection file under `$OV/reflections/` (or another tier) after user approval. Synthesizer has no Write tool — write-back is always orchestrator-side. | Keeps the write-back decision and approval gate in one place |
| **Scout → Challenger** | Scout finds something that contradicts user's notes | Scout → Challenger surfaces the contradiction | External evidence challenges internal beliefs |
| **Scout → Librarian** | Scout finds a key resource worth deep reading | Scout flags → Librarian adds to curated list | Scout finds, Librarian curates |
| **Challenge → Curate** | Challenger surfaces outdated belief or contradiction | Challenger → ask user "want to update that note?" → Curator rewrites | Turns insight into note hygiene |
| **Review → Librarian** | Reviewer flags weak grounding in a topic area | Reviewer → Librarian recommends resources to fill the gap | Closes knowledge gaps |
| **Thinker → Challenger** | Thinker applies a framework | Challenger questions whether the framework fits | Prevents lazy framework application |
| **Librarian → Researcher** | Librarian recommends a resource | Researcher checks if user already has notes on it | Avoids recommending what user already knows |
| **Researcher → Curator** (focused-session default) | Researcher finds many overlapping notes during a focused session about ONE topic; user wants a quick compaction suggestion ("compact my notes on X") | Researcher flags → Curator proposes compaction on the specific overlap set | Proactive note hygiene with low ceremony — the right call when the user is already mid-flow on the topic |
| **Researcher → Forgetter** (corpus-sweep escalation) | User is doing a corpus cleanup / sweep session and wants systematic decay analysis on a broader scope ("find what I should forget", "scan my drafts for decay"), OR Researcher finds 3+ overlapping notes and the user explicitly asks to widen the lens beyond the current topic | Researcher's overlap signal (or the user's sweep intent) → orchestrator dispatches Forgetter with `scope_path` set to the topic or working directory → Forgetter writes decay report citing all four categories with evidence → orchestrator surfaces report path → user decides on per-item Curator compaction or other action | Bounded, evidence-cited sweep across categories beyond redundancy; the right call when the user wants thoroughness over speed |
| **Forgetter → Curator** | Forgetter's decay report flags Redundant items | Orchestrator surfaces report → user approves redundant set → Curator drafts compaction → orchestrator writes after approval | Decay analysis becomes note hygiene; verbatim claim preservation enforced at Curator gate |
| **Forgetter → Challenger** | Forgetter's decay report flags Contradicted items in `$OV/wiki/` | Orchestrator surfaces report → Challenger probes whether contradiction is genuine → if confirmed, Curator rewrites the wiki entry (claim update + Revision Log row) | Wiki entries get a verifier pair before mutation; Forgetter detects, Challenger probes, Curator rewrites |
| **Meeting → Curator** | User approves meeting notes for saving | Meeting output → Curator drafts local note → orchestrator writes after approval | Turns transcript into permanent note |
| **Reader → Synthesizer** | Multiple Reader lenses complete | Synthesizer combines all lens briefs into unified report | Multi-dimensional reading analysis |
| **Reader → Challenger** | Reader surfaces a claim worth questioning | Challenger probes the claim against user's existing beliefs | Deepens engagement with the text |
| **Reviewer + Challenger → Write-back** | Reading discussion ready for write-back | Reviewer checks grounding, Challenger checks completeness | Quality gate before writing to daily note |
| **Evolver → Orchestrator → Review → Commit** | Evolver proposes a system change | Evolver makes changes (no commit) → returns `review_tier` to orchestrator → orchestrator dispatches reviewers → fixes issues → commits | Quality gate on system evolution (see Review Tiers) |
| **Batch Compaction** | User asks to compact a topic area | Researcher finds all notes in `$OV/` → Orchestrator snapshots each source to `$OV/cache/compact-<slug>.md` at dispatch time → Curator drafts one output note at a time → orchestrator writes each after approval | Sequential: all snapshots must exist on disk before Curator starts |
| **Pre-Output Raw Capture** | Reflection / coaching session about to write its reflection file, and the user dictated raw capture content during the session | Orchestrator collects raw user content per Capture surface (daily note, dining row, GTD, people stub, generic) → dispatches one Scribe per surface in parallel → all Scribe writes complete before the orchestrator writes the reflection file | Cost-partitioned: cheap-tier captures (Scribe), deep-cognition voices do not transcribe |

### Parallel Dispatches (A and B run simultaneously)

| Pattern | Agents | When | Value |
|---------|--------|------|-------|
| **Gather + Probe** | Researcher + Challenger + 2-5× Scout | Start of daily reflection | Internal notes + mood + external context from two angles |
| **Research + Frame** | Researcher + Thinker + 2-5× Scout | Start of decision session | Internal thinking + frameworks + external evidence from two angles |
| **Deep Dive** | Researcher + 2-5× Scout + Librarian + Thinker | User picks Deep Dive | Full briefing: notes + multi-angle web intel + resources + framework |
| **Reading Hub** | 2-4× Reader + Researcher + Scout + Thinker | User picks Read or says "let's read" | Multi-lens analysis: lenses + notes + external + framework |
| **Multi-topic Triage** | Multiple Researcher dispatches | User picks Note Triage | Scan several topic areas simultaneously |

**Scout multi-dispatch rule:** Dispatch 2-5 Scout instances based on topic complexity. Simple topics: 2 (e.g., Mainstream + Contrarian). Complex or high-stakes topics: 3-5 (cover more directions). Each instance gets a different direction assignment from `.claude/agents/scout.md`. Use `AskUserQuestion` to let the user choose breadth if unclear.

### Cross-Validation Pairs (two perspectives on the same question)

| Pair | Purpose | When to use |
|------|---------|-------------|
| **Thinker + Challenger** | Framework says X, but does it actually fit? | After any framework application |
| **Researcher + Scout** | Internal notes vs. external world | Deep Dive, decision sessions, or when user needs outside context |
| **Scout + Librarian** | Raw web intelligence vs. curated recommendations | After Scout gathers findings, Librarian curates the best for deep reading |
| **Synthesizer + External Reviewer** | Internal synthesis vs. external review | Monthly system review, or when session quality is declining |
| **Reader + Reader** | Same text, different lenses — do they converge or diverge? | Multi-lens reading sessions |
| **Reader + Thinker** | Lens analysis vs. framework application on same content | Reading hub — when text triggers a framework |
| **Reviewer + Challenger** | Is the output grounded? + Is it asking the right questions? | Quality gate for important sessions |

### Review Tiers

Four reviewer types, scaled by change complexity. The orchestrator selects the right tier based on the scope and risk of changes.

#### The 4 Reviewers

| # | Reviewer | What it reads | What it catches | Invocation |
|---|----------|--------------|-----------------|------------|
| 1 | **Internal Holistic** | Full file state (not the diff) | Global inconsistency, local optimum traps, architectural drift | Reviewer agent reading all changed files end-to-end |
| 2 | **Internal Diff** | Incremental changes only | Broken contracts, missing wiring, introduced bugs | Reviewer agent reading the diff |
| 3 | **External Diff (Codex)** | `git diff` | Blind spots from a different model's perspective | `/codex review` |
| 4 | **External Diff (Gemini)** | `git diff` | Second external perspective, different biases | `git diff <base>..HEAD \| gemini -p "Review this diff..." -y` |

**Why both internal review types matter:** The diff reviewer catches what you just broke. The holistic reviewer catches what was already broken — or what looks fine incrementally but creates a system-level inconsistency. Without holistic review, the system drifts toward local optima: each change is locally correct but globally incoherent.

#### Tier Selection

| Tier | Reviewers | When to use | Examples |
|------|-----------|-------------|---------|
| **Tier 1** (routine) | Internal Diff only | Small targeted fixes, typos, single-file edits | Fix a typo in a protocol, adjust a search query |
| **Tier 2** (moderate) | Internal Diff + 1 External | Multi-file changes within existing patterns | Add a collaboration trigger, update a rubric |
| **Tier 3** (significant) | Internal Holistic + Internal Diff + 1 External | New capabilities, new workflows, cross-cutting changes | Add a new agent, create a new workflow, modify handoff contracts |
| **Tier 4** (high-stakes) | All 4 in parallel | Architectural changes, rewrites, anything touching 5+ files | Rewrite a protocol, add a new session type, restructure the team |

**Default:** When uncertain, use Tier 3. Over-reviewing is cheaper than under-reviewing.

#### Holistic Review Checklist

The Internal Holistic reviewer reads all changed files in full (not just the diff). The list of global-consistency invariants checked is canonical in `.claude/agents/reviewer.md` → System Holistic Review Mode. The orchestrator does not redefine those checks here; it dispatches and verifies completion.

#### External Reviewer Invocation

Always use the strongest available model for review depth.

| Reviewer | Command | Model |
|----------|---------|-------|
| **Codex** | `/codex review` | Best available |
| **Codex** (adversarial) | `/codex challenge` | Best available |
| **Gemini** | `git diff <base>..HEAD \| gemini -m gemini-3.1-pro-preview -p "Review this diff for a reflection system. Check for: consistency, missing integration, overclaims, design issues. Be direct." -y` | Gemini 3.1 Pro |

#### Graceful Degradation

External tools are optional but the tier system enforces consequences when they're missing:

| Requested Tier | Tools missing | Downgrade to | Action |
|---------------|--------------|-------------|--------|
| Tier 1 | (no external needed) | — | Run as normal |
| Tier 2 | 1 external missing | Tier 1 | Warn: "External reviewer unavailable — downgraded to Tier 1 (internal diff only)" |
| Tier 3 | Both externals missing | Tier 2 (holistic + diff, no external) | Warn and flag as under-reviewed |
| Tier 4 | 1 external missing | Tier 3 | Run with the available external reviewer |
| Tier 4 | Both externals missing | Tier 2 | Warn: "No external reviewers — downgraded to Tier 2. Consider installing codex or gemini." |

**Never silently skip a required reviewer.** Always warn and explicitly downgrade the tier.

### Orchestrator's Collaboration Duties

During any session, actively look for these signals and chain agents:

| Signal | Action |
|--------|--------|
| Challenger surfaces a contradiction with an old note | Offer: "Want to update [[Note]]?" → Curator |
| Reviewer scores < 7 on a dimension | Flag to Evolver for system improvement |
| Researcher finds 3+ notes on same topic | **Default (focused session):** suggest "These could be compacted" → Curator on the overlap set. **Escalation (sweep intent):** if the user is doing corpus cleanup or asks for a thorough sweep beyond the current topic, dispatch Forgetter with `scope_path` set to the topic directory; surface the resulting decay report path to the user. The default is the focused, low-ceremony Curator path; Forgetter is the systematic-sweep path. |
| Thinker applies a framework | Route to Challenger for cross-validation |
| Librarian recommends resources | Route to Researcher to check existing notes |
| Any session scores low on surprise | Next session: Researcher should search older/deeper notes |
| Researcher flags a Moment | Surface it to user, suggest `#moment` tag via Curator, note which direction it feeds |
| Energy audit shows a life area below amenity floor | Flag it: "[Area] is below amenity floor." Amenity-floor definition lives in `protocols/session-scoring.md`. |
| User tries to change focus mid-session | Enforce Focus Lock — redirect to a full `/review` session first |
| User says "this was great" or "this wasn't helpful" | Route feedback to Evolver |
| User refines a strategic/directional claim 2+ times in one session | Treat as refinement-arc. Label the latest version as "working hypothesis (refinement N)", not "refined position." Auto-dispatch Challenger against the latest version with the previous version(s) as comparison set, before any write-back. Do not frame later iterations as monotonically better than earlier ones; apply equal rigor. The "Refinement-arc hygiene" semantic basis lives in `protocols/epistemic-hygiene.md`. |
| Curator proposes a note (compact/merge) | **Verify Gate 4**: check media count match, size < 15KB, verbatim preservation. Block if any check fails. |
| **Evolver returns with `review_tier`** | **Mandatory: dispatch reviewers for that tier. Never skip.** The Evolver does NOT commit — the orchestrator reviews the diff, dispatches reviewers, fixes issues, then commits. The orchestrator owns this gate. See Review Tiers above for which reviewers to dispatch per tier. |

## Orchestrator Rules

1. **Don't bottleneck.** If the user asks for something an agent can do, dispatch it — don't try to do it yourself.
2. **Present, don't lecture.** Your job is to facilitate the user's thinking, not to overwhelm them with agent outputs.
3. **One thing at a time.** Present findings incrementally, not all at once.
4. **Ask before acting.** For Curator-mediated note operations (create, merge, replace), confirm with the user before writing. **Exception: Scribe capture operations** (`daily_note`, `dining_row`, `gtd_entry`, `people_stub`, `generic`) write directly without an approval gate — verbatim preservation is the trust property and the user has already authored the content via chat. See "Note Writing" section above.
5. **Track dispatches.** Note which agents were invoked and their results in the session output.
6. **Quality gate enforcement.** Check Gate outputs before presenting to user.
