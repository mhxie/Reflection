#!/usr/bin/env python3
"""
atelier.py: small helper CLI for portable Atelier workflows.

Claude Code has native project slash commands. Codex does not currently expose
a documented custom project slash-command format, so this helper gives Codex a
stable command discovery surface:

    python3 scripts/atelier.py commands
    python3 scripts/atelier.py prompt hi
    python3 scripts/atelier.py source hi
    python3 scripts/atelier.py agents
    python3 scripts/atelier.py agent-prompt researcher
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import textwrap
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMMANDS_PATH = ROOT / "harness" / "commands.toml"
AGENTS_PATH = ROOT / "harness" / "agents.toml"
MODELS_PATH = ROOT / "harness" / "models.toml"
CAPABILITIES_PATH = ROOT / "harness" / "capabilities.toml"


def load_commands() -> dict[str, dict[str, Any]]:
    commands = load_table(COMMANDS_PATH, "commands")
    if not isinstance(commands, dict):
        raise SystemExit("atelier: harness/commands.toml has no [commands] table")
    return commands


def load_agents() -> dict[str, dict[str, Any]]:
    agents = load_table(AGENTS_PATH, "agents")
    if not isinstance(agents, dict):
        raise SystemExit("atelier: harness/agents.toml has no [agents] table")
    return agents


def load_table(path: Path, table: str) -> dict[str, Any]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if table not in data:
        raise SystemExit(f"atelier: {path.relative_to(ROOT)} has no [{table}] table")
    value = data[table]
    if not isinstance(value, dict):
        raise SystemExit(f"atelier: {path.relative_to(ROOT)} [{table}] is not a table")
    return value


def require_command(commands: dict[str, dict[str, Any]], name: str) -> dict[str, Any]:
    try:
        command = commands[name]
    except KeyError:
        known = ", ".join(sorted(commands))
        raise SystemExit(f"atelier: unknown command `{name}`. Known commands: {known}") from None
    if not isinstance(command, dict):
        raise SystemExit(f"atelier: command `{name}` is not a table")
    # Resolve aliases: `status = "alias"` with `alias_of = "<target>"` redirects
    # source/codex_prompt lookups to the target entry. The alias's own row
    # remains visible in `commands` listings as a documentation breadcrumb.
    if command.get("status") == "alias":
        target_name = command.get("alias_of")
        if not isinstance(target_name, str) or not target_name:
            raise SystemExit(f"atelier: command `{name}` is `status = \"alias\"` but missing `alias_of`")
        if target_name == name:
            raise SystemExit(f"atelier: command `{name}` aliases itself")
        try:
            target = commands[target_name]
        except KeyError:
            raise SystemExit(f"atelier: command `{name}` aliases unknown command `{target_name}`") from None
        if not isinstance(target, dict):
            raise SystemExit(f"atelier: alias target `{target_name}` is not a table")
        if target.get("status") == "alias":
            raise SystemExit(f"atelier: alias chains are not allowed (`{name}` -> `{target_name}` -> alias)")
        return target
    return command


def require_agent(agents: dict[str, dict[str, Any]], name: str) -> dict[str, Any]:
    try:
        agent = agents[name]
    except KeyError:
        known = ", ".join(sorted(agents))
        raise SystemExit(f"atelier: unknown agent `{name}`. Known agents: {known}") from None
    if not isinstance(agent, dict):
        raise SystemExit(f"atelier: agent `{name}` is not a table")
    return agent


def print_rows(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    widths = [
        max(len(headers[i]), *(len(row[i]) for row in rows))
        for i in range(len(headers))
    ]
    print("  ".join(f"{headers[i]:<{widths[i]}}" for i in range(len(headers))))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(f"{row[i]:<{widths[i]}}" for i in range(len(headers))))


def cmd_commands(args: argparse.Namespace) -> int:
    commands = load_commands()
    selected: dict[str, dict[str, Any]] = {}
    for name, command in sorted(commands.items()):
        if args.category and command.get("category") != args.category:
            continue
        selected[name] = command
    if args.json:
        print(json.dumps(selected, indent=2, sort_keys=True))
        return 0

    rows: list[tuple[str, str, str, str]] = []
    for name, command in selected.items():
        rows.append((
            name,
            str(command.get("category", "")),
            str(command.get("status", "")),
            str(command.get("description", "")),
        ))
    if not rows:
        return 0

    print_rows(("command", "category", "status", "description"), rows)
    return 0


def cmd_agents(args: argparse.Namespace) -> int:
    agents = load_agents()
    selected: dict[str, dict[str, Any]] = {}
    for name, agent in sorted(agents.items()):
        if args.member:
            voices = agent.get("voices") or []
            if not isinstance(voices, list) or args.member not in voices:
                continue
        selected[name] = agent
    if args.json:
        print(json.dumps(selected, indent=2, sort_keys=True))
        return 0

    rows: list[tuple[str, str, str, str]] = []
    for name, agent in selected.items():
        voices = agent.get("voices") or []
        voices_str = ",".join(voices) if isinstance(voices, list) else str(voices)
        rows.append((
            name,
            voices_str,
            str(agent.get("status", "")),
            str(agent.get("description", "")),
        ))
    if not rows:
        return 0
    print_rows(("agent", "voices", "status", "description"), rows)
    return 0


def cmd_prompt(args: argparse.Namespace) -> int:
    commands = load_commands()
    command = require_command(commands, args.command)
    source = str(command.get("source", ""))
    base_prompt = str(command.get("codex_prompt", "")).strip()
    if not base_prompt:
        base_prompt = f"Run the /{args.command} workflow using `{source}`."

    extra_args = " ".join(args.arguments).strip()
    parts = [
        base_prompt,
        "",
        "Before acting, read `AGENTS.md`, `CLAUDE.md`, and `protocols/runtime-adapters.md`.",
        "Translate Claude Code tool syntax to the current runtime. Prefer local `$OV/` files and ask before any Reflect write.",
    ]
    if extra_args:
        parts.extend(["", f"Arguments/context: {extra_args}"])
    print("\n".join(parts))
    return 0


def cmd_agent_prompt(args: argparse.Namespace) -> int:
    agents = load_agents()
    agent = require_agent(agents, args.agent)
    source = str(agent.get("source", ""))
    base_prompt = str(agent.get("codex_prompt", "")).strip()
    if not base_prompt:
        base_prompt = f"Emulate the {args.agent} role using `{source}`."

    extra_args = " ".join(args.arguments).strip()
    parts = [
        base_prompt,
        "",
        "Before acting, read `AGENTS.md`, `CLAUDE.md`, and `protocols/runtime-adapters.md`.",
        "Use the agent spec as a role brief. Translate Claude Code tool syntax to the current runtime.",
    ]
    if extra_args:
        parts.extend(["", f"Task/context: {extra_args}"])
    print("\n".join(parts))
    return 0


def cmd_source(args: argparse.Namespace) -> int:
    commands = load_commands()
    command = require_command(commands, args.command)
    source = ROOT / str(command.get("source", ""))
    if args.path_only:
        print(source.relative_to(ROOT).as_posix())
        return 0
    if not source.exists():
        raise SystemExit(f"atelier: command source `{source}` does not exist")
    print(source.read_text(encoding="utf-8"))
    return 0


def cmd_agent_source(args: argparse.Namespace) -> int:
    agents = load_agents()
    agent = require_agent(agents, args.agent)
    source = ROOT / str(agent.get("source", ""))
    if args.path_only:
        print(source.relative_to(ROOT).as_posix())
        return 0
    if not source.exists():
        raise SystemExit(f"atelier: agent source `{source}` does not exist")
    print(source.read_text(encoding="utf-8"))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    commands = load_commands()
    command = require_command(commands, args.command)
    source = str(command.get("source", ""))
    base_prompt = str(command.get("codex_prompt", "")).strip()
    if not base_prompt:
        base_prompt = f"Run the /{args.command} workflow using `{source}`."

    extra = (args.context or "").strip()
    parts = [
        base_prompt,
        "",
        "Before acting, read `AGENTS.md`, `CLAUDE.md`, and `protocols/runtime-adapters.md`.",
        "Translate Claude Code tool syntax to the current runtime. Prefer local `$OV/` files and ask before any Reflect write.",
    ]
    if extra:
        parts.extend(["", f"Arguments/context: {extra}"])
    prompt = "\n".join(parts)

    if args.fork and args.exec:
        raise SystemExit("atelier: --fork is not supported with --exec; `codex exec` has no fork subcommand.")

    resume_friendly = bool(command.get("resume_friendly", False))
    if (args.resume or args.fork) and not resume_friendly:
        sys.stderr.write(
            f"atelier: warning: `{args.command}` is not marked resume_friendly; "
            "carrying prior session context may pollute reflection-style workflows. "
            "Consider running fresh, or `--fork` to isolate side effects.\n"
        )

    if args.print:
        print(prompt)
        return 0

    if args.fork:
        codex_cmd = ["codex", "fork", "--last", prompt]
    elif args.resume:
        codex_cmd = (
            ["codex", "exec", "resume", "--last", prompt]
            if args.exec
            else ["codex", "resume", "--last", prompt]
        )
    elif args.exec:
        codex_cmd = ["codex", "exec", "-C", str(ROOT), prompt]
    else:
        codex_cmd = ["codex", "-C", str(ROOT), prompt]

    try:
        return subprocess.run(codex_cmd, cwd=str(ROOT)).returncode
    except FileNotFoundError:
        raise SystemExit(
            "atelier: codex CLI not found on PATH. Install with `npm i -g @openai/codex`."
        ) from None


def cmd_status(args: argparse.Namespace) -> int:
    commands = load_commands()
    agents = load_agents()
    models = load_table(MODELS_PATH, "models")
    capabilities = load_table(CAPABILITIES_PATH, "capabilities")

    payload = {
        "roots": {
            "AGENTS.md": {
                "exists": (ROOT / "AGENTS.md").exists(),
                "bytes": (ROOT / "AGENTS.md").stat().st_size if (ROOT / "AGENTS.md").exists() else 0,
            },
            "CLAUDE.md": {
                "exists": (ROOT / "CLAUDE.md").exists(),
                "bytes": (ROOT / "CLAUDE.md").stat().st_size if (ROOT / "CLAUDE.md").exists() else 0,
            },
        },
        "registries": {
            "commands": len(commands),
            "agents": len(agents),
            "models": len(models),
            "capabilities": len(capabilities),
        },
        "commands_by_category": count_by(commands, "category"),
        "agents_by_voices_member": count_by_voices(agents),
        "paths": {
            "commands": COMMANDS_PATH.relative_to(ROOT).as_posix(),
            "agents": AGENTS_PATH.relative_to(ROOT).as_posix(),
            "models": MODELS_PATH.relative_to(ROOT).as_posix(),
            "capabilities": CAPABILITIES_PATH.relative_to(ROOT).as_posix(),
            "runtime_adapters": "protocols/runtime-adapters.md",
            "skill": ".agents/skills/atelier/SKILL.md",
        },
    }

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    print("Atelier harness status")
    print("")
    print(f"AGENTS.md: {payload['roots']['AGENTS.md']['bytes']} bytes")
    print(f"CLAUDE.md: {payload['roots']['CLAUDE.md']['bytes']} bytes")
    print("")
    print("Registries")
    for key, value in payload["registries"].items():
        print(f"- {key}: {value}")
    print("")
    print("Commands by category")
    for key, value in payload["commands_by_category"].items():
        print(f"- {key}: {value}")
    print("")
    print("Agents by voices member")
    for key, value in payload["agents_by_voices_member"].items():
        print(f"- {key}: {value}")
    return 0


def count_by(items: dict[str, dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items.values():
        key = str(item.get(field, "") or "(unset)")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def count_by_voices(agents: dict[str, dict[str, Any]]) -> dict[str, int]:
    """Count how many agents include each model in their voices.

    Each agent's `voices` is a list of model names; an agent contributes
    one increment per distinct model it lists. The result is keyed by model
    name (not by voices tuple), so totals will exceed `len(agents)` when
    each agent declares 2 voices.
    """
    counts: dict[str, int] = {}
    for agent in agents.values():
        voices = agent.get("voices") or []
        if not isinstance(voices, list):
            continue
        for member in voices:
            key = str(member) if member else "(unset)"
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/atelier.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Discover Atelier command specs and generate Codex prompts.",
        epilog=textwrap.dedent(
            """\
            Examples:
              python3 scripts/atelier.py status
              python3 scripts/atelier.py commands
              python3 scripts/atelier.py commands --category session --json
              python3 scripts/atelier.py prompt hi -- "I had a tough day"
              python3 scripts/atelier.py run hi "I had a tough day"
              python3 scripts/atelier.py run lint --exec
              python3 scripts/atelier.py source lint --path-only
              python3 scripts/atelier.py agents
              python3 scripts/atelier.py agent-prompt researcher -- "find notes about agency"
            """
        ),
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)

    commands = sub.add_parser("commands", help="List portable command specs.")
    commands.add_argument("--category", help="Filter by command category.")
    commands.add_argument("--json", action="store_true", help="Emit JSON.")
    commands.set_defaults(func=cmd_commands)

    agents = sub.add_parser("agents", help="List portable agent role specs.")
    agents.add_argument(
        "--member",
        help="Filter to agents whose voices includes this model name (e.g., opus, deepseek_pro_max).",
    )
    agents.add_argument("--json", action="store_true", help="Emit JSON.")
    agents.set_defaults(func=cmd_agents)

    status = sub.add_parser("status", help="Summarize the portable harness registries.")
    status.add_argument("--json", action="store_true", help="Emit JSON.")
    status.set_defaults(func=cmd_status)

    prompt = sub.add_parser("prompt", help="Print a Codex-ready prompt for a command.")
    prompt.add_argument("command", help="Command name, without leading slash.")
    prompt.add_argument("arguments", nargs=argparse.REMAINDER, help="Optional command arguments or context.")
    prompt.set_defaults(func=cmd_prompt)

    agent_prompt = sub.add_parser("agent-prompt", help="Print a Codex-ready prompt for an agent role.")
    agent_prompt.add_argument("agent", help="Agent name.")
    agent_prompt.add_argument("arguments", nargs=argparse.REMAINDER, help="Optional role task or context.")
    agent_prompt.set_defaults(func=cmd_agent_prompt)

    source = sub.add_parser("source", help="Print the source command spec.")
    source.add_argument("command", help="Command name, without leading slash.")
    source.add_argument("--path-only", action="store_true", help="Print only the source path.")
    source.set_defaults(func=cmd_source)

    agent_source = sub.add_parser("agent-source", help="Print the source agent role spec.")
    agent_source.add_argument("agent", help="Agent name.")
    agent_source.add_argument("--path-only", action="store_true", help="Print only the source path.")
    agent_source.set_defaults(func=cmd_agent_source)

    run = sub.add_parser("run", help="Launch Codex with the generated workflow prompt.")
    run.add_argument("command", help="Command name, without leading slash.")
    run.add_argument("context", nargs="?", default="", help="Optional context string.")
    run.add_argument("--exec", action="store_true", help="Use `codex exec` (non-interactive) instead of the interactive TUI.")
    run.add_argument("--print", action="store_true", help="Print the prompt without invoking Codex.")
    session = run.add_mutually_exclusive_group()
    session.add_argument("--resume", action="store_true", help="Continue the most recent Codex session (`codex resume --last`). Carries prior session context; warns when not resume_friendly.")
    session.add_argument("--fork", action="store_true", help="Fork the most recent Codex session (`codex fork --last`). Branches from prior context without mutating the original session.")
    run.set_defaults(func=cmd_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
