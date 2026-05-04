# Runtime Adapters Protocol

Atelier should run under Claude Code and Codex without forking the reflection
system. The core idea is to separate four concerns:

| Concern | Owned by | Example |
|---|---|---|
| Workflow | `protocols/`, command specs | `/hi`, `/weekly`, `/review` |
| Role | `harness/agents.toml`, agent specs | Researcher, Synthesizer, Reviewer |
| Capability | `harness/capabilities.toml` | `semantic_query`, `write_local_file`, `web_search` |
| Runtime and model | adapters, local CLI config + `profile/models.toml` (gitignored) | one runtime per call, model bound per profile |

This follows the OpenClaw lesson: the system can use different models when the
provider and runtime are explicit metadata, not assumptions buried inside the
workflow.

## Runtime Surfaces

| Runtime | Reads | Native surface | Status |
|---|---|---|---|
| Claude Code | `CLAUDE.md` | `.claude/agents/`, `.claude/commands/` | Primary interactive harness |
| Codex | `AGENTS.md` | `.agents/skills/atelier/`, Codex CLI, Codex review | Portable harness |

Claude Code remains the most complete native surface because the command files
currently use Claude constructs such as `AskUserQuestion` and `Agent(...)`.
Codex uses `AGENTS.md` plus this protocol to translate those constructs.

`harness/commands.toml` and `harness/agents.toml` are the registries shared by
both runtimes. They map portable names to the current Claude source files and
give Codex prompts that can be generated with `python3 scripts/atelier.py
prompt <name>` and `python3 scripts/atelier.py agent-prompt <name>`. The
repo-scoped `atelier` skill points Codex to these registries without loading
every command or agent spec up front.

Codex does not yet ship a project-level custom slash-command surface, so the
parity invocation is `python3 scripts/atelier.py run <command>`. For the full
recipe set (run, run --exec, run --resume, run --fork, plus discovery
commands), see `AGENTS.md` § Codex Quick Recipes; that file is the operational
canon for Codex sessions and is read first by Codex.

## Provider-Neutral Rules

- Do not add new provider-specific model names to shared protocols. Use a model
  profile from `harness/models.toml`.
- Do not add new provider-specific tool names to shared protocols. Use a
  capability from `harness/capabilities.toml`.
- Existing `.claude/` files may keep Claude frontmatter and tool names. They are
  adapter surfaces.
- New shared docs should say "run a semantic query" or "write a local file",
  not name provider-specific tools, unless they are documenting an adapter
  itself.
- If a runtime lacks a feature, degrade explicitly. Example: if Codex cannot
  spawn subagents in a given environment, read the target agent spec and run the
  step sequentially.

## Model Profiles

Agent roles ask for capability classes, not fixed provider models. Profile
schema (names, rationale, invocation pattern, agent assignments) is defined
in `harness/models.toml` (committed; identity declarations only); the
actual provider/model bindings (model id, endpoint URL, env var, request
extras) live in `profile/models.toml` (gitignored). Loaders merge schema +
bindings at runtime.

Voice dispatch model — single source of truth: `protocols/orchestrator.md` → "Voice Dispatch (every role is intrinsically dual)". The agent-to-voices mapping lives in `harness/agents.toml` (committed) as `voices = [a, b]` per agent. Swapping providers or models is a binding-file edit in `profile/models.toml`; no committed file changes.

## Capability Profiles

Capabilities describe what an agent needs, independent of the runtime:

- `read_file`
- `search_text`
- `run_shell`
- `semantic_query`
- `web_search`
- `web_fetch`
- `write_local_file`
- `spawn_role`
- `ask_user`

The concrete tool mapping is in `harness/capabilities.toml`.

## Codex Command Execution

When a user asks Codex to run an Atelier command:

1. Read `AGENTS.md`.
2. Read `CLAUDE.md` for domain rules and safety constraints.
3. Read `.claude/commands/<command>.md` for the workflow.
4. Translate Claude-specific constructs using the table in `AGENTS.md` § Codex Adaptation.
5. Read any referenced agent specs from `.claude/agents/`.
6. Prefer local `$OV/` files, `rg`, and `uv run scripts/semantic.py`.
7. Ask before any local file write under `$OV/`. **Exception: Scribe capture operations** (`daily_note`, `dining_row`, `gtd_entry`, `people_stub`, `generic`) write directly without an approval gate — the user has already authored the raw content via chat and verbatim preservation is the trust property. Other agents and ad-hoc orchestrator writes still ask first.
8. Report any downgraded capability, such as missing web access or unavailable
   subagent dispatch.

For discovery, launch, resume, and fork recipes (`python3 scripts/atelier.py
status | commands | prompt | source | agents | agent-prompt | agent-source |
run [--exec | --resume | --fork]`), see `AGENTS.md` § Codex Quick Recipes.

