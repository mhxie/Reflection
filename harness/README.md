# Harness

Provider-neutral registry files for the Atelier runtime layer.

| File | Purpose |
|---|---|
| `commands.toml` | Portable workflow names mapped to `.claude/commands/*.md` sources and Codex prompts. |
| `agents.toml` | Portable role names mapped to source files (typically `.claude/agents/*.md`; may be a script for script-driven roles like `external-reviewer`) and a per-role `voices = {leg = "model", ...}` keyed inline table. Allowed leg keys: `native`, `direct`, `codex`. |
| `intents.toml` | Intent router registry for `/hi` — trigger phrases mapped to dispatch shape (mode, agents, profile reads, coordination pattern). |
| `models.toml` | Model identity registry (committed schema: identity names like opus, sonnet, deepseek_pro_max — declarations only, no bindings). Provider/model bindings live in gitignored `profile/models.toml` and merge at runtime. |
| `capabilities.toml` | Runtime-neutral capability names and the Codex-side tool that implements each. The Claude Code mapping lives in `.claude/agents/*.md` `tools:` frontmatter (single source of truth). |

Provider pricing data lives at `scripts/pricing.toml`, not here. It is offline reference data consumed only by `scripts/pricing.py` for cost estimation and future Pareto-optimal model selection: nothing on the dispatch path loads it, so it stays out of the runtime contract.

Use the helper CLI instead of scraping TOML directly:

```bash
python3 scripts/atelier.py status
python3 scripts/atelier.py commands
python3 scripts/atelier.py agents
python3 scripts/atelier.py prompt reflect
python3 scripts/atelier.py agent-prompt researcher
```

Before finishing harness changes:

```bash
python3 scripts/harness_lint.py
python3 scripts/harness_smoke.py
```

The lint checks that Claude command/agent files, portable registries, model
profiles, capabilities, `AGENTS.md`, `CLAUDE.md`, and the repo-scoped Codex
skill stay aligned.

The smoke test exercises the helper CLI and JSON surfaces without reading the
private vault.
