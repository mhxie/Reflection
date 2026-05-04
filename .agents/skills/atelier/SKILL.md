---
name: atelier
description: Use when working in the Atelier repo, especially to run Atelier workflows such as /hi (universal entry; /reflect alias), /weekly, /review, /introspect, /lint, /promote, or to adapt Claude Code command specs for Codex.
---

# Atelier

Use this skill when the user asks to run or modify Atelier workflows, commands,
agents, or harness portability.

## Quick Start

1. Read `AGENTS.md`.
2. Read `protocols/runtime-adapters.md`.
3. Inspect the registry with `python3 scripts/atelier.py status`.
4. Discover commands with `python3 scripts/atelier.py commands`.
5. For a specific workflow, either launch it with
   `python3 scripts/atelier.py run <command>` (Codex parity for Claude Code
   slash commands) or generate a paste-in prompt with
   `python3 scripts/atelier.py prompt <command>`. Read the source with
   `python3 scripts/atelier.py source <command>` when you need the full spec.
6. Discover roles with `python3 scripts/atelier.py agents`.
7. For a specific role, run `python3 scripts/atelier.py agent-prompt <agent>`
   or read the source with `python3 scripts/atelier.py agent-source <agent>`.
8. Load only the selected `.claude/commands/<command>.md` spec and any directly
   referenced agent or protocol files.

## Command Execution

Claude Code command specs are the current workflow source. In Codex, adapt them:

- `Read` means read the local file.
- `Grep` and `Glob` mean use `rg` or `rg --files` with scoped paths.
- `Bash` means use the local shell.
- `AskUserQuestion` means ask the user a concise question.
- `Agent(...)` means use Codex subagents only when permitted; otherwise emulate
  the role sequentially from `.claude/agents/<role>.md`.
- All vault writes go through the orchestrator (Write/Edit) after explicit user
  approval. Daily notes (`$OV/daily-notes/`) are user-authored only — system
  reads them but never writes.

For unknown commands, do not guess. Run:

```bash
python3 scripts/atelier.py commands
```

## Harness Changes

When editing the harness:

1. Keep shared behavior provider-neutral.
2. Update `harness/commands.toml` for command additions or removals.
3. Update `harness/agents.toml` for agent additions or removals.
4. Update `harness/models.toml` for model-profile changes.
5. Update `harness/capabilities.toml` for tool or runtime changes.
6. Run `python3 scripts/harness_lint.py` before finishing.
7. Run `python3 scripts/harness_smoke.py` after helper or registry edits.

Do not add Codex-only workflow copies unless Codex documents a stable custom
project slash-command format. Prefer the manifest and helper CLI.
