# AGENTS.md — Atelier

Root instructions for Codex and other non-Claude runtimes. Claude Code reads
`CLAUDE.md`; Codex reads this file. Treat both as the same behavioral contract.

This system is **the Atelier** — a workshop wrapping the user's **œuvre**
(accumulating body of work, kept under `$OV/`). The user is the **Painter**;
agents collectively are **le cercle**. For the full vocabulary and the
13-operator archetype map, see `protocols/atelier.md`.

Codex can also discover the repo-scoped `atelier` skill in `.agents/skills/atelier/`.

Before user-facing reflection work, read `CLAUDE.md` for the domain rules. The
operational Claude-to-Codex tool mapping lives in this file (§ Codex
Adaptation, below). The conceptual contract (workflow / role / capability /
runtime separation, model and capability profiles) lives in
`protocols/runtime-adapters.md`; consult it when adding a new role, command,
or runtime, not for routine command execution.

## Critical Rules

`CLAUDE.md` is the single source of behavioral rules. Codex MUST read it at
session start; Critical Rules, Reading Rules, Writing Rules, and Coaching
Style there apply equally under Codex. Do not restate them here; this file
documents the runtime contract only.

## Runtime Contract

- Shared behavior belongs in `CLAUDE.md`, `AGENTS.md`, `protocols/`, `harness/`,
  `frameworks/`, `sources/`, and `scripts/`.
- Runtime-specific behavior belongs at the edge: `.claude/`, `.codex/`, local
  CLI config, MCP config, or adapter documentation.
- `.claude/commands/*.md` are command specifications. In Codex, read the matching
  command file and adapt the tool syntax rather than treating the file as
  unusable. `harness/commands.toml` is the portable command registry.
- `.claude/agents/*.md` are role specifications. In Codex, use them as role
  briefs. If subagents are unavailable or disallowed by higher-priority runtime
  rules, emulate the role sequentially in the main session and disclose the
  downgrade. `harness/agents.toml` is the portable role registry.
- Model names in agent frontmatter are harness assumptions. The neutral mapping
  lives in `harness/models.toml`.
- Tool names in agent frontmatter are runtime affordances. The neutral mapping
  lives in `harness/capabilities.toml`.

## Codex Adaptation

When a command spec uses Claude Code syntax, adapt it this way:

| Claude surface | Codex behavior |
|---|---|
| `Read` | Read the local file. |
| `Grep` / `Glob` | Use `rg` / `rg --files` with scoped paths. |
| `Bash` | Use the shell tool with project-relative paths. |
| `Write` / `Edit` | Use `apply_patch` or the runtime's local-file write tool to create or modify project files. |
| `AskUserQuestion` | Ask a concise question; use numbered options if there is no native picker. |
| `Agent(...)` | Dispatch a Codex subagent only when the runtime permits it; otherwise run the role sequentially from its `.claude/agents/*.md` brief. |
| `WebSearch` / `WebFetch` | Use web search when enabled; otherwise state that web access is unavailable. |

## Codex Quick Recipes

High-frequency operations. Lift these directly instead of re-deriving from `protocols/runtime-adapters.md` each session:

| Need | Command |
|---|---|
| Semantic vault search | `uv run scripts/semantic.py query "<concept>" --top 10` |
| Today's daily note | `cat "$OV/daily-notes/$(date +%Y-%m-%d).md"` (before 03:00 local also read previous day) |
| Wiki entry by title | `rg -l "<title>" "$OV/wiki/"` |
| Privacy gate | `uv run scripts/privacy_check.py --json` |
| Harness state / lint | `python3 scripts/harness_lint.py --json` |
| Source spec for a command | `python3 scripts/atelier.py source <name>` |
| Run a workflow | `python3 scripts/atelier.py run <name>` |

For project slash commands such as `/reflect`, `/review`, `/weekly`, and
`/lint`, read the corresponding `.claude/commands/<name>.md` file and run the
workflow under this adaptation table.

To discover command specs from Codex:

```bash
python3 scripts/atelier.py status
python3 scripts/atelier.py commands
python3 scripts/atelier.py prompt reflect
python3 scripts/atelier.py source reflect --path-only
```

To launch a workflow directly (Codex parity for Claude Code's slash commands):

```bash
python3 scripts/atelier.py run reflect            # interactive TUI (fresh session)
python3 scripts/atelier.py run lint --exec        # non-interactive
python3 scripts/atelier.py run reflect "context"
python3 scripts/atelier.py run promote --resume   # continue last session (resume_friendly only)
python3 scripts/atelier.py run promote --fork     # branch from last session without mutating it
```

Default is a fresh session. `--resume` (`codex resume --last`) and `--fork`
(`codex fork --last`) carry prior session context and are only recommended
for commands marked `resume_friendly = true` in `harness/commands.toml`.

To discover role specs from Codex:

```bash
python3 scripts/atelier.py agents
python3 scripts/atelier.py agent-prompt researcher
python3 scripts/atelier.py agent-source researcher --path-only
```

## Project Shell Trust (Codex)

Project shell trust lives in `~/.codex/config.toml`:

```toml
[projects."/path/to/atelier"]
trust_level = "trusted"
```

This bypasses shell-command approval for trusted projects.

## System Evolution

When changing the harness:

1. Keep the core protocol provider-neutral.
2. Add or update model profiles in `harness/models.toml`.
3. Add or update capability mappings in `harness/capabilities.toml`.
4. Add or update role mappings in `harness/agents.toml`.
5. Add or update command mappings in `harness/commands.toml`.
6. Update `.agents/skills/atelier/SKILL.md` if the Codex workflow changes.
7. Keep Claude-specific syntax in `.claude/` and Codex-specific notes in
   `.codex/`.
8. Run `python3 scripts/harness_lint.py` before finishing.
9. Run `python3 scripts/harness_smoke.py` after helper or registry edits.
