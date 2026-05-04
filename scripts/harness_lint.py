#!/usr/bin/env python3
"""
harness_lint.py: portability checks for the Claude Code and Codex harness.

This script checks the repo-level contracts that let Atelier run under both
Claude Code and Codex:

  1. Codex has a root AGENTS.md.
  2. Shared runtime rules point to CLAUDE.md and runtime-adapters.md.
  3. Agent model frontmatter is represented in harness/models.toml.
  4. Capability names referenced by shared protocols are mapped to Codex tools
     in harness/capabilities.toml.
  5. Tracked command specs are represented in harness/commands.toml.
  6. Tracked agent specs are represented in harness/agents.toml.
  7. The harness reference doc exists.
  8. Codex has a repo-scoped Atelier skill for workflow discovery.
  9. Intent/agent registry coherence: every `intents.<name>.agents[*]`
     resolves to an agent in `harness/agents.toml`; pattern values in
     both registries are drawn from the allowed set; `agents.<name>.used_by`
     is consistent with the intents/commands walk; orphans flagged.
 10. Every `intents.<name>.mode` is reachable from the Sub-mode procedures
     map in `.claude/commands/hi.md`; every `intents.<name>.profile_reads`
     filename exists at `profile/<name>`.

Exit code: 0 if no ERROR-level findings, 1 if any ERROR-level finding.
argparse returns 2 on CLI usage errors.

Fixers (mutating, off by default):
  --fix-used-by  Regenerate `used_by` lists in `harness/agents.toml` from the
                 intents+commands walk. Idempotent. Use after editing
                 `harness/intents.toml` or after a command adds/drops an
                 agent dispatch. Default lint runs are read-only.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEVERITY_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2}

# Allowed coordination-pattern values for both `agents.<name>.pattern` (in
# harness/agents.toml) and `intents.<name>.pattern` (in harness/intents.toml).
# Definitions live in protocols/orchestrator.md → "Coordination Patterns".
ALLOWED_PATTERNS = frozenset({
    "orchestrator-subagent",
    "generator-verifier",
    "agent-team",
    "shared-state",
    "solo",
})

# Patterns matching agent-name mentions in command source files. Anchored on
# word boundaries; case-insensitive at usage time. Built dynamically from the
# loaded agent registry so new agents are picked up automatically. Multi-word
# stems are listed before single-word stems so they match greedily.
def _build_agent_name_re(agent_names: list[str]) -> re.Pattern[str]:
    by_len = sorted(set(agent_names), key=lambda s: -len(s))
    parts = [n.replace("-", "[- ]") for n in by_len]
    return re.compile(r"\b(" + "|".join(parts) + r")\b", re.IGNORECASE)

# A line counts as a dispatch context only if it mentions one of these tokens.
# Filters incidental prose mentions (e.g., `readwise reader-list-documents`
# CLI commands, "Reader persona" prose) from the used_by walk; only lines
# that look like real dispatch sites contribute. Per-line scope keeps the
# heuristic local — a CLI fragment one line above a real dispatch will not
# accidentally tag the agent.
DISPATCH_CONTEXT_RE = re.compile(
    r"\b(dispatch(?:es|ed|ing)?|subagent_type|agent|cercle)\b|\*\*",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    where: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "where": self.where,
            "message": self.message,
        }


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_toml(path: Path) -> tuple[dict[str, Any] | None, Finding | None]:
    try:
        return tomllib.loads(_read(path)), None
    except FileNotFoundError:
        return None, Finding("ERROR", "missing-file", rel(path), f"`{rel(path)}` is missing")
    except tomllib.TOMLDecodeError as exc:
        return None, Finding("ERROR", "invalid-toml", rel(path), str(exc))


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
FIELD_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*$", re.MULTILINE)


def parse_agent_frontmatter(path: Path) -> dict[str, str]:
    text = _read(path)
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for key, value in FIELD_RE.findall(match.group(1)):
        fields[key] = value
    return fields


def load_claude_agents() -> tuple[dict[str, dict[str, str]], list[Finding]]:
    findings: list[Finding] = []
    agents: dict[str, dict[str, str]] = {}
    agent_dir = ROOT / ".claude" / "agents"
    if not agent_dir.exists():
        return agents, [
            Finding("ERROR", "missing-agent-dir", ".claude/agents", "Claude agent directory is missing")
        ]

    for path in sorted(agent_dir.glob("*.md")):
        fields = parse_agent_frontmatter(path)
        name = fields.get("name")
        if not name:
            findings.append(
                Finding("ERROR", "agent-frontmatter", rel(path), "missing `name` in frontmatter")
            )
            continue
        agents[name] = {
            "path": rel(path),
            "model": fields.get("model", ""),
            "tools": fields.get("tools", ""),
        }
    return agents, findings


def git_list(paths: list[str], *, others: bool = False) -> tuple[list[str], Finding | None]:
    cmd = ["git", "ls-files"]
    if others:
        cmd.extend(["-o", "--exclude-standard"])
    cmd.extend(paths)
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        return [], Finding(
            "ERROR",
            "git-ls-files",
            "git",
            f"`{' '.join(cmd)}` failed: {res.stderr.strip()}",
        )
    return sorted(line for line in res.stdout.splitlines() if line.strip()), None


def load_claude_commands() -> tuple[dict[str, str], list[Finding]]:
    tracked, err = git_list([".claude/commands"])
    if err:
        return {}, [err]
    untracked, err = git_list([".claude/commands"], others=True)
    if err:
        return {}, [err]

    command_paths = sorted(
        p for p in set(tracked) | set(untracked)
        if p.endswith(".md") and p.startswith(".claude/commands/")
    )
    commands: dict[str, str] = {}
    findings: list[Finding] = []
    for path in command_paths:
        name = Path(path).stem
        if name in commands:
            findings.append(
                Finding(
                    "ERROR",
                    "command-duplicate",
                    path,
                    f"duplicate command stem `{name}` also appears at `{commands[name]}`",
                )
            )
            continue
        commands[name] = path
    return commands, findings


def check_root_files() -> list[Finding]:
    findings: list[Finding] = []

    agents_path = ROOT / "AGENTS.md"
    claude_path = ROOT / "CLAUDE.md"
    runtime_path = ROOT / "protocols" / "runtime-adapters.md"

    if not agents_path.exists():
        findings.append(
            Finding("ERROR", "missing-agents-md", "AGENTS.md", "Codex root instructions are missing")
        )
    else:
        text = _read(agents_path)
        if "CLAUDE.md" not in text:
            findings.append(
                Finding("ERROR", "agents-contract", "AGENTS.md", "AGENTS.md must point Codex to CLAUDE.md")
            )
        if "protocols/runtime-adapters.md" not in text:
            findings.append(
                Finding(
                    "ERROR",
                    "agents-contract",
                    "AGENTS.md",
                    "AGENTS.md must point Codex to protocols/runtime-adapters.md",
                )
            )

    if not claude_path.exists():
        findings.append(
            Finding("ERROR", "missing-claude-md", "CLAUDE.md", "Claude Code root instructions are missing")
        )
    else:
        size = claude_path.stat().st_size
        if size > 15_000:
            findings.append(
                Finding(
                    "ERROR",
                    "claude-size",
                    "CLAUDE.md",
                    f"CLAUDE.md is {size} bytes; hard ceiling is 15000 bytes",
                )
            )
        elif size > 8_192:
            findings.append(
                Finding(
                    "WARN",
                    "claude-size",
                    "CLAUDE.md",
                    f"CLAUDE.md is {size} bytes; target is under 8192 bytes",
                )
            )
        bold_count = _read(claude_path).count("**")
        if bold_count:
            findings.append(
                Finding(
                    "INFO",
                    "claude-bold",
                    "CLAUDE.md",
                    f"CLAUDE.md contains {bold_count} bold markers",
                )
            )

    if not runtime_path.exists():
        findings.append(
            Finding(
                "ERROR",
                "missing-runtime-adapters",
                rel(runtime_path),
                "runtime adapter protocol is missing",
            )
        )

    return findings


def check_models(agents: dict[str, dict[str, str]]) -> tuple[list[Finding], dict[str, Any]]:
    """Validate harness/models.toml schema + cross-check bindings if present.

    Schema model: `harness/models.toml` (committed) declares model identities
    as `[models.X]` entries (opus, sonnet, deepseek_pro_max, ...). Each entry
    is allowed to be an empty table — the docstring above the entry carries
    the rationale, and the binding values (claude_code, codex, direct_api,
    direct_api_base, api_env, direct_api_extras, direct_api_timeout,
    codex_reasoning_effort) live in `profile/models.toml` (gitignored).

    Agent voices membership lives in `harness/agents.toml` as a keyed inline
    table `voices = {native = "X", direct = "Y"}` (or single-leg variants)
    and is validated in `check_agent_registry`. Returns the schema models
    dict so callers can cross-check voices references without re-reading.
    """
    findings: list[Finding] = []
    data, err = _load_toml(ROOT / "harness" / "models.toml")
    if err:
        return [err], {}
    assert data is not None

    models = data.get("models", {})
    if not isinstance(models, dict) or not models:
        findings.append(
            Finding("ERROR", "models-empty", "harness/models.toml", "no model identities declared")
        )
        return findings, {}

    # Forbid the legacy `[profiles.*]` / `[agents.*]` blocks: those belonged
    # to the pre-refactor schema and a re-introduction would silently fork
    # the registry. Hard error, not warn.
    if "profiles" in data:
        findings.append(
            Finding(
                "ERROR",
                "models-legacy-profiles",
                "harness/models.toml",
                "legacy `[profiles.*]` block present; the schema now uses `[models.*]` only",
            )
        )
    if "agents" in data:
        findings.append(
            Finding(
                "ERROR",
                "models-legacy-agent-map",
                "harness/models.toml",
                "legacy `[agents.*]` block present; agent->voices bindings now live in harness/agents.toml",
            )
        )

    binding_keys = {
        "claude_code", "codex", "codex_reasoning_effort",
        "direct_api", "direct_api_base", "direct_api_extras",
        "direct_api_timeout", "api_env",
    }

    for model_name, entry in sorted(models.items()):
        if not isinstance(entry, dict):
            findings.append(
                Finding("ERROR", "models-model-shape", "harness/models.toml", f"model `{model_name}` is not a table")
            )
            continue
        # Binding-shaped keys must NOT appear in the committed schema; they
        # belong in profile/models.toml. Catches accidental leakage of
        # provider names back into the public file.
        leaked = sorted(k for k in entry if k in binding_keys)
        for k in leaked:
            findings.append(
                Finding(
                    "ERROR",
                    "models-binding-in-schema",
                    "harness/models.toml",
                    f"model `{model_name}` has binding key `{k}` (move to profile/models.toml)",
                )
            )

    findings.extend(_check_model_bindings(agents, models))
    return findings, models


def _check_model_bindings(
    agents: dict[str, dict[str, str]],
    models: dict[str, Any],
) -> list[Finding]:
    """Cross-check profile/models.toml bindings against the schema, and
    cross-check `.claude/agents/<name>.md` frontmatter `model:` against the
    role's native voice leg in `harness/agents.toml`.

    Soft check on bindings: if the bindings file is missing, return silently.
    Absence is the expected state on fresh clones (the file is gitignored,
    machine-local). When present, verify every schema model has a binding.
    """
    findings: list[Finding] = []

    # Cross-check Claude frontmatter `model:` against the native voice leg
    # for every role declared in harness/agents.toml. Drift here means the
    # Anthropic-side dispatch (Agent tool) and the harness's declared native
    # voice disagree, which silently routes to the wrong model.
    harness_path = ROOT / "harness" / "agents.toml"
    if harness_path.exists():
        h_data, _ = _load_toml(harness_path)
        if h_data is not None:
            registry = h_data.get("agents", {}) or {}
            for agent_name, frontmatter in agents.items():
                entry = registry.get(agent_name)
                if not isinstance(entry, dict):
                    continue
                voices = entry.get("voices")
                if not isinstance(voices, dict):
                    continue
                native_id = voices.get("native")
                fm_model = frontmatter.get("model")
                if native_id and fm_model and native_id != fm_model:
                    bindings_path = ROOT / "profile" / "models.toml"
                    expected_native = native_id
                    if bindings_path.exists():
                        b_data, _ = _load_toml(bindings_path)
                        if b_data is not None:
                            binding = (b_data.get("models", {}) or {}).get(native_id, {}) or {}
                            cc = binding.get("claude_code")
                            if isinstance(cc, str):
                                expected_native = cc
                    if fm_model != expected_native:
                        findings.append(
                            Finding(
                                "WARN",
                                "models-claude-drift",
                                frontmatter.get("path", f".claude/agents/{agent_name}.md"),
                                f"frontmatter model `{fm_model}` differs from native voice `{native_id}` (expected `{expected_native}` per profile/models.toml)",
                            )
                        )

    bindings_path = ROOT / "profile" / "models.toml"
    if not bindings_path.exists():
        return findings
    data, err = _load_toml(bindings_path)
    if err:
        return [err]
    assert data is not None
    binding_models = data.get("models", {}) or {}

    for model_name in sorted(models):
        if model_name not in binding_models:
            findings.append(
                Finding(
                    "WARN",
                    "models-binding-missing",
                    "profile/models.toml",
                    f"schema model `{model_name}` has no binding entry",
                )
            )
    return findings


def check_capabilities() -> list[Finding]:
    findings: list[Finding] = []
    data, err = _load_toml(ROOT / "harness" / "capabilities.toml")
    if err:
        return [err]
    assert data is not None

    capabilities = data.get("capabilities", {})
    if not isinstance(capabilities, dict) or not capabilities:
        return [
            Finding("ERROR", "capabilities-missing", "harness/capabilities.toml", "no capabilities declared")
        ]

    for cap_name, cap in sorted(capabilities.items()):
        if not isinstance(cap, dict):
            findings.append(
                Finding("ERROR", "capability-shape", "harness/capabilities.toml", f"capability `{cap_name}` is not a table")
            )
            continue
        for key in ("description", "codex"):
            if not cap.get(key):
                findings.append(
                    Finding(
                        "ERROR",
                        "capability-field",
                        "harness/capabilities.toml",
                        f"capability `{cap_name}` is missing `{key}`",
                    )
                )

    return findings


def check_agent_registry(
    agents: dict[str, dict[str, str]],
    models: dict[str, Any],
) -> list[Finding]:
    """Validate harness/agents.toml registry shape + voices bindings.

    Each agent declares a `voices` keyed inline table mapping leg name
    (`native`/`direct`/`codex`) to model identity; every model identity
    referenced must exist in `harness/models.toml`. Source paths must match the discovered
    `.claude/agents/*.md` file (one exception: script-driven agents like
    `external-reviewer` declare a non-`.claude/agents/` source and have no
    Claude-side spec). Codex prompt should reference the source path so
    Codex emulators can route discovery.
    """
    findings: list[Finding] = []
    data, err = _load_toml(ROOT / "harness" / "agents.toml")
    if err:
        return [err]
    assert data is not None

    registry = data.get("agents", {})
    if not isinstance(registry, dict) or not registry:
        return [
            Finding("ERROR", "agents-registry-missing", "harness/agents.toml", "no agents declared")
        ]

    required_fields = (
        "source",
        "voices",
        "status",
        "description",
        "codex_prompt",
    )

    for name, fields in sorted(agents.items()):
        entry = registry.get(name)
        if not isinstance(entry, dict):
            findings.append(
                Finding(
                    "ERROR",
                    "agents-registry-entry-missing",
                    "harness/agents.toml",
                    f"agent `{name}` from `{fields['path']}` has no registry entry",
                )
            )
            continue
        for field in required_fields:
            if not entry.get(field):
                findings.append(
                    Finding(
                        "ERROR",
                        "agents-registry-field",
                        "harness/agents.toml",
                        f"agent `{name}` is missing `{field}`",
                    )
                )
        source = entry.get("source")
        if source != fields["path"]:
            findings.append(
                Finding(
                    "ERROR",
                    "agents-registry-source-drift",
                    "harness/agents.toml",
                    f"agent `{name}` source `{source}` differs from discovered path `{fields['path']}`",
                )
            )
        voices = entry.get("voices")
        if voices is not None:
            if not isinstance(voices, dict) or not voices:
                findings.append(
                    Finding(
                        "ERROR",
                        "agents-voices-shape",
                        "harness/agents.toml",
                        f"agent `{name}` voices must be a non-empty inline table mapping leg name to model identity",
                    )
                )
            else:
                allowed_legs = {"native", "direct", "codex"}
                for leg_name, model_ref in voices.items():
                    if leg_name not in allowed_legs:
                        findings.append(
                            Finding(
                                "ERROR",
                                "agents-voices-leg-name",
                                "harness/agents.toml",
                                f"agent `{name}` voices leg `{leg_name}` not in {sorted(allowed_legs)}",
                            )
                        )
                        continue
                    if not isinstance(model_ref, str):
                        findings.append(
                            Finding(
                                "ERROR",
                                "agents-voices-leg-shape",
                                "harness/agents.toml",
                                f"agent `{name}` voices leg `{leg_name}` value `{model_ref!r}` is not a string",
                            )
                        )
                        continue
                    if model_ref not in models:
                        findings.append(
                            Finding(
                                "ERROR",
                                "agents-voices-unknown-model",
                                "harness/agents.toml",
                                f"agent `{name}` voices leg `{leg_name}` references unknown model `{model_ref}` (not in harness/models.toml)",
                            )
                        )
        kinds = entry.get("kinds")
        if kinds is None:
            findings.append(
                Finding(
                    "ERROR",
                    "agents-kinds-missing",
                    "harness/agents.toml",
                    f"agent `{name}` is missing `kinds` field (must be a non-empty list of 'system' or 'app')",
                )
            )
        elif not isinstance(kinds, list) or not kinds:
            findings.append(
                Finding(
                    "ERROR",
                    "agents-kinds-shape",
                    "harness/agents.toml",
                    f"agent `{name}` kinds must be a non-empty list",
                )
            )
        else:
            for kind in kinds:
                if kind not in ("system", "app"):
                    findings.append(
                        Finding(
                            "ERROR",
                            "agents-kinds-unknown",
                            "harness/agents.toml",
                            f"agent `{name}` kinds value `{kind!r}` not in {{'system', 'app'}}",
                        )
                    )
        rationale = entry.get("dispatch_rationale")
        allowed_rationales = {"context-isolation", "model-tier", "parallelization", "tool-isolation"}
        if rationale is None:
            findings.append(
                Finding(
                    "ERROR",
                    "agents-dispatch-rationale-missing",
                    "harness/agents.toml",
                    f"agent `{name}` is missing `dispatch_rationale` field; declare why a subagent is worth the overhead vs. inline orchestration",
                )
            )
        elif not isinstance(rationale, list) or not rationale:
            findings.append(
                Finding(
                    "ERROR",
                    "agents-dispatch-rationale-shape",
                    "harness/agents.toml",
                    f"agent `{name}` dispatch_rationale must be a non-empty list",
                )
            )
        else:
            for value in rationale:
                if value not in allowed_rationales:
                    findings.append(
                        Finding(
                            "ERROR",
                            "agents-dispatch-rationale-unknown",
                            "harness/agents.toml",
                            f"agent `{name}` dispatch_rationale value `{value!r}` not in {sorted(allowed_rationales)}",
                        )
                    )
        prompt = str(entry.get("codex_prompt", ""))
        if source and str(source) not in prompt:
            findings.append(
                Finding(
                    "WARN",
                    "agents-registry-prompt-source",
                    "harness/agents.toml",
                    f"agent `{name}` Codex prompt does not mention `{source}`",
                )
            )

    for name, entry in sorted(registry.items()):
        if not isinstance(entry, dict):
            findings.append(
                Finding(
                    "ERROR",
                    "agents-registry-entry-shape",
                    "harness/agents.toml",
                    f"agent `{name}` is not a table",
                )
            )
            continue
        source = str(entry.get("source", ""))
        status = entry.get("status", "")
        is_script_driven = status == "script-driven"
        if name not in agents and not is_script_driven:
            findings.append(
                Finding(
                    "WARN",
                    "agents-registry-entry-extra",
                    "harness/agents.toml",
                    f"registry agent `{name}` has no .claude agent source",
                )
            )
        # Script-driven agents (e.g., external-reviewer → scripts/review.sh)
        # legitimately have a non-.claude/agents/ source. Validate voices
        # voices but skip the Claude-side source-path checks for them.
        if is_script_driven:
            voices = entry.get("voices")
            if isinstance(voices, dict):
                for leg_name, model_ref in voices.items():
                    if isinstance(model_ref, str) and model_ref not in models:
                        findings.append(
                            Finding(
                                "ERROR",
                                "agents-voices-unknown-model",
                                "harness/agents.toml",
                                f"agent `{name}` voices leg `{leg_name}` references unknown model `{model_ref}`",
                            )
                        )
            if source and not (ROOT / source).exists():
                findings.append(
                    Finding(
                        "ERROR",
                        "agents-registry-source-missing",
                        "harness/agents.toml",
                        f"script-driven agent `{name}` source `{source}` does not exist",
                    )
                )
            continue
        if not source.startswith(".claude/agents/") or not source.endswith(".md"):
            findings.append(
                Finding(
                    "ERROR",
                    "agents-registry-source-shape",
                    "harness/agents.toml",
                    f"agent `{name}` source must be a `.claude/agents/*.md` path",
                )
            )
            continue
        source_path = ROOT / source
        if not source_path.exists():
            findings.append(
                Finding(
                    "ERROR",
                    "agents-registry-source-missing",
                    "harness/agents.toml",
                    f"agent `{name}` source `{source}` does not exist",
                )
            )
        if Path(source).stem != name:
            findings.append(
                Finding(
                    "WARN",
                    "agents-registry-name-drift",
                    "harness/agents.toml",
                    f"registry key `{name}` differs from source stem `{Path(source).stem}`",
                )
            )

    return findings


def check_commands(commands: dict[str, str]) -> list[Finding]:
    findings: list[Finding] = []
    data, err = _load_toml(ROOT / "harness" / "commands.toml")
    if err:
        return [err]
    assert data is not None

    command_map = data.get("commands", {})
    if not isinstance(command_map, dict) or not command_map:
        return [
            Finding("ERROR", "commands-missing", "harness/commands.toml", "no commands declared")
        ]

    required_fields = ("source", "category", "status", "description", "codex_prompt")

    for name, path in sorted(commands.items()):
        entry = command_map.get(name)
        if not isinstance(entry, dict):
            findings.append(
                Finding(
                    "ERROR",
                    "commands-entry-missing",
                    "harness/commands.toml",
                    f"command `{name}` from `{path}` has no manifest entry",
                )
            )
            continue
        for field in required_fields:
            if not entry.get(field):
                findings.append(
                    Finding(
                        "ERROR",
                        "commands-field",
                        "harness/commands.toml",
                        f"command `{name}` is missing `{field}`",
                    )
                )
        source = entry.get("source")
        if source != path:
            findings.append(
                Finding(
                    "ERROR",
                    "commands-source-drift",
                    "harness/commands.toml",
                    f"command `{name}` source `{source}` differs from discovered path `{path}`",
                )
            )
        prompt = str(entry.get("codex_prompt", ""))
        if entry.get("status") == "alias":
            pass  # alias prompts intentionally reference the target's source, not their own
        elif source and str(source) not in prompt:
            findings.append(
                Finding(
                    "WARN",
                    "commands-prompt-source",
                    "harness/commands.toml",
                    f"command `{name}` Codex prompt does not mention `{source}`",
                )
            )

    for name, entry in sorted(command_map.items()):
        if not isinstance(entry, dict):
            findings.append(
                Finding(
                    "ERROR",
                    "commands-entry-shape",
                    "harness/commands.toml",
                    f"command `{name}` is not a table",
                )
            )
            continue
        source = str(entry.get("source", ""))
        if name not in commands:
            findings.append(
                Finding(
                    "WARN",
                    "commands-entry-extra",
                    "harness/commands.toml",
                    f"manifest command `{name}` has no tracked .claude command source",
                )
            )
        if not source.startswith(".claude/commands/") or not source.endswith(".md"):
            findings.append(
                Finding(
                    "ERROR",
                    "commands-source-shape",
                    "harness/commands.toml",
                    f"command `{name}` source must be a `.claude/commands/*.md` path",
                )
            )
            continue
        source_path = ROOT / source
        if not source_path.exists():
            findings.append(
                Finding(
                    "ERROR",
                    "commands-source-missing",
                    "harness/commands.toml",
                    f"command `{name}` source `{source}` does not exist",
                )
            )
        if Path(source).stem != name:
            findings.append(
                Finding(
                    "WARN",
                    "commands-name-drift",
                    "harness/commands.toml",
                    f"manifest key `{name}` differs from source stem `{Path(source).stem}`",
                )
            )

    return findings


def check_harness_readme() -> list[Finding]:
    path = ROOT / "harness" / "README.md"
    if not path.exists():
        return [
            Finding(
                "ERROR",
                "harness-readme-missing",
                rel(path),
                "portable harness reference is missing",
            )
        ]
    text = _read(path)
    findings: list[Finding] = []
    for needle in ("commands.toml", "agents.toml", "models.toml", "capabilities.toml", "scripts/atelier.py"):
        if needle not in text:
            findings.append(
                Finding(
                    "ERROR",
                    "harness-readme-reference",
                    rel(path),
                    f"harness README must reference `{needle}`",
                )
            )
    return findings


def check_atelier_skill() -> list[Finding]:
    findings: list[Finding] = []
    path = ROOT / ".agents" / "skills" / "atelier" / "SKILL.md"
    if not path.exists():
        return [
            Finding(
                "ERROR",
                "skill-missing",
                rel(path),
                "repo-scoped Codex skill for Atelier workflows is missing",
            )
        ]

    fields = parse_agent_frontmatter(path)
    if fields.get("name") != "atelier":
        findings.append(
            Finding("ERROR", "skill-name", rel(path), "skill frontmatter must set `name: atelier`")
        )
    description = fields.get("description", "")
    if not description or "/hi" not in description:
        findings.append(
            Finding(
                "ERROR",
                "skill-description",
                rel(path),
                "skill description must mention Atelier workflow triggers",
            )
        )

    text = _read(path)
    for needle in ("harness/commands.toml", "harness/agents.toml", "scripts/atelier.py", "protocols/runtime-adapters.md"):
        if needle not in text:
            findings.append(
                Finding(
                    "ERROR",
                    "skill-reference",
                    rel(path),
                    f"skill must reference `{needle}`",
                )
            )
    return findings


def check_scripts_zk_paths() -> list[Finding]:
    """Flag hardcoded `"zk"` literals (path or string-default) in scripts/.

    Vault-rooted paths must go through `scripts/_paths.vault_root()` so
    they fail loud when $OV is unset and never silently create stray
    relative `zk/` directories. Two patterns are flagged:

      - `Path("zk/...")` literal (the original failure mode)
      - bare-string `"zk"` or `["zk"]` defaults (the failure mode that
        bit semantic.py — wrapped in `walk_markdown` it became a relative
        path resolved against the script's cwd)

    The only allowed mentions are in `_paths.py` (the helper's own
    docstring explains the antipattern) and `harness_lint.py` (this
    check's own remediation message).
    """
    findings: list[Finding] = []
    scripts_dir = ROOT / "scripts"
    if not scripts_dir.is_dir():
        return findings
    skip = {"_paths.py", "harness_lint.py"}
    # Patterns covering the four common forms of the antipattern:
    #   (1) Path("zk/...")         — Path constructor with literal
    #   (2) = "zk"                 — bare-string assignment (excludes
    #       `==` comparisons via the `=` in the lookbehind class)
    #   (3) ["zk"]                 — list/dict literal
    #   (4) / "zk"                 — operator-form path construction
    #       (e.g., `(REPO_ROOT / "zk").resolve()`); this is the form
    #       that lived for months in fission/relink/wikilink_to_md and
    #       6 oneoff/ scripts before the lint caught it.
    patterns = [
        re.compile(r'Path\("zk/'),
        re.compile(r'(?<![\w.=])= "zk"(?![\w/])'),
        re.compile(r'\["zk"\]'),
        re.compile(r'/ "zk"(?![\w/])'),
    ]
    # Only top-level scripts/; `scripts/oneoff/` is gitignored (one-off
    # migration scripts that hardcode private vault content) and excluded
    # from steady-state lint coverage by convention.
    for path in sorted(scripts_dir.glob("*.py")):
        if path.name in skip:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if any(p.search(line) for p in patterns):
                findings.append(
                    Finding(
                        "ERROR",
                        "scripts-hardcoded-zk",
                        f"{rel(path)}:{lineno}",
                        "use vault_root() from _paths instead of a hardcoded zk literal",
                    )
                )
    return findings


def load_intents() -> tuple[dict[str, dict[str, Any]], list[Finding]]:
    """Load harness/intents.toml; return ({}, [finding]) on missing/invalid.

    The file is required harness state in Wave 1A onward. Missing rows are
    treated as a load failure, not a silent pass — an empty `[intents]`
    table (comment-only file or accidental wipe) means `/hi` would route
    nothing, which is never the intended state.
    """
    findings: list[Finding] = []
    path = ROOT / "harness" / "intents.toml"
    if not path.exists():
        findings.append(
            Finding(
                "ERROR",
                "intents-missing-file",
                "harness/intents.toml",
                "intent registry is missing",
            )
        )
        return {}, findings
    data, err = _load_toml(path)
    if err:
        return {}, [err]
    assert data is not None
    intents = data.get("intents", {})
    if not isinstance(intents, dict):
        return {}, [
            Finding(
                "ERROR",
                "intents-shape",
                "harness/intents.toml",
                "[intents] table missing or not a table",
            )
        ]
    if not intents:
        # File exists, parses, but has no rows. Wave 1A makes the intent
        # registry required harness state; an empty registry is a load
        # failure, not a silent pass.
        findings.append(
            Finding(
                "ERROR",
                "intents-empty-registry",
                "harness/intents.toml",
                "[intents] table is empty (no intent rows declared)",
            )
        )
        return {}, findings
    return intents, findings


def _expected_used_by(
    intents: dict[str, dict[str, Any]],
    commands: dict[str, str],
    harness_agents: dict[str, Any] | None = None,
) -> dict[str, list[str]]:
    """Compute the expected `used_by` list per agent.

    Walks three registries:
      1. `intents.<name>.agents[*]` (harness/intents.toml)
      2. agent-name mentions inside each `commands.<name>` source file
         (via dynamic AGENT_NAME_RE built from the registry)
      3. references to a script-driven agent's `source` path (e.g.,
         `scripts/review.sh` for external-reviewer) inside command sources

    Returns a dict keyed by agent name; values are sorted lists of strings
    of the form `"intents.<name>"` / `"commands.<name>"`. Agents with no
    references map to an empty list (orphan signal).
    """
    expected: dict[str, set[str]] = {}
    agent_names = list((harness_agents or {}).keys())
    name_re = _build_agent_name_re(agent_names) if agent_names else None

    # Map non-.md `source` paths back to the agent name (script-driven agents).
    script_sources: dict[str, str] = {}
    for agent_name, entry in (harness_agents or {}).items():
        if not isinstance(entry, dict):
            continue
        source = entry.get("source")
        if isinstance(source, str) and not source.endswith(".md"):
            script_sources[source] = agent_name

    for intent_name, entry in intents.items():
        if not isinstance(entry, dict):
            continue
        for agent_name in entry.get("agents", []) or []:
            if not isinstance(agent_name, str):
                continue
            expected.setdefault(agent_name, set()).add(f"intents.{intent_name}")

    for command_name, source in commands.items():
        source_path = ROOT / source
        if not source_path.exists():
            continue
        try:
            text = source_path.read_text(encoding="utf-8")
        except OSError:
            continue
        seen: set[str] = set()
        if name_re is not None:
            for line in text.splitlines():
                if not DISPATCH_CONTEXT_RE.search(line):
                    continue
                for match in name_re.finditer(line):
                    stem = match.group(1).lower().replace(" ", "-")
                    seen.add(stem)
        # Script-driven agents: search for references to their source path.
        for script_path, agent_name in script_sources.items():
            if script_path in text:
                seen.add(agent_name)
        for stem in seen:
            expected.setdefault(stem, set()).add(f"commands.{command_name}")

    return {name: sorted(refs) for name, refs in expected.items()}


def check_intents_registry(
    intents: dict[str, dict[str, Any]],
    claude_agents: dict[str, Any],
    harness_agents: dict[str, Any],
) -> list[Finding]:
    """Validate intent rows: agent references resolve, pattern values valid,
    and overlapping patterns at the same priority are flagged.

    Agent references must resolve against BOTH registries:
      - `claude_agents` from `load_claude_agents()` (`.claude/agents/*.md`):
        canonical for Claude Code subagent dispatch.
      - `harness_agents` from `harness/agents.toml` `[agents]` table:
        canonical for Codex parity (Codex emulates roles by reading this
        registry, not by walking the .claude tree).

    A row is fully valid only when both registries know the agent. Missing
    in either registry is an ERROR with a distinct code so operators can
    see which surface is broken.
    """
    findings: list[Finding] = []
    if not intents:
        return findings

    for intent_name, entry in sorted(intents.items()):
        if not isinstance(entry, dict):
            findings.append(
                Finding(
                    "ERROR",
                    "intents-entry-shape",
                    "harness/intents.toml",
                    f"intent `{intent_name}` is not a table",
                )
            )
            continue
        # (a) agent references valid in BOTH registries
        agents_field = entry.get("agents", []) or []
        if not isinstance(agents_field, list):
            findings.append(
                Finding(
                    "ERROR",
                    "intents-agent-shape",
                    "harness/intents.toml",
                    f"intent `{intent_name}` `agents` must be a list",
                )
            )
        else:
            for agent_name in agents_field:
                if not isinstance(agent_name, str):
                    findings.append(
                        Finding(
                            "ERROR",
                            "intents-agent-missing-claude",
                            "harness/intents.toml",
                            f"intent `{intent_name}` has non-string agent entry `{agent_name!r}`",
                        )
                    )
                    continue
                if agent_name not in claude_agents:
                    findings.append(
                        Finding(
                            "ERROR",
                            "intents-agent-missing-claude",
                            "harness/intents.toml",
                            f"intent `{intent_name}` references agent `{agent_name}` not in .claude/agents/ (Claude Code dispatch will fail)",
                        )
                    )
                if agent_name not in harness_agents:
                    findings.append(
                        Finding(
                            "ERROR",
                            "intents-agent-missing-harness",
                            "harness/intents.toml",
                            f"intent `{intent_name}` references agent `{agent_name}` not in harness/agents.toml (Codex parity broken)",
                        )
                    )
        # (c) intent pattern value valid
        pattern_value = entry.get("pattern")
        if pattern_value is None:
            findings.append(
                Finding(
                    "ERROR",
                    "intents-pattern-missing",
                    "harness/intents.toml",
                    f"intent `{intent_name}` is missing required `pattern` field",
                )
            )
        elif not isinstance(pattern_value, str):
            findings.append(
                Finding(
                    "ERROR",
                    "intents-pattern-invalid",
                    "harness/intents.toml",
                    f"intent `{intent_name}` pattern must be a string, got {type(pattern_value).__name__}",
                )
            )
        elif pattern_value not in ALLOWED_PATTERNS:
            findings.append(
                Finding(
                    "ERROR",
                    "intents-pattern-invalid",
                    "harness/intents.toml",
                    f"intent `{intent_name}` pattern=`{pattern_value}` not in {sorted(ALLOWED_PATTERNS)}",
                )
            )

    # (f) priority collisions: only exact-duplicate phrases at same priority
    by_priority: dict[int, list[tuple[str, set[str]]]] = {}
    for intent_name, entry in intents.items():
        if not isinstance(entry, dict):
            continue
        priority = entry.get("priority")
        if not isinstance(priority, int):
            continue
        patterns = entry.get("patterns", []) or []
        if not isinstance(patterns, list):
            continue
        normalized = {p.lower() for p in patterns if isinstance(p, str) and p.strip()}
        if not normalized:
            continue
        by_priority.setdefault(priority, []).append((intent_name, normalized))

    for priority, rows in by_priority.items():
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                name_a, set_a = rows[i]
                name_b, set_b = rows[j]
                overlap = sorted(set_a & set_b)
                if overlap:
                    findings.append(
                        Finding(
                            "WARN",
                            "intents-priority-collision",
                            "harness/intents.toml",
                            f"intents `{name_a}` and `{name_b}` share priority={priority} and overlapping patterns: {overlap}",
                        )
                    )

    return findings


def check_intents_mode_mapping(
    intents: dict[str, dict[str, Any]],
) -> list[Finding]:
    """Verify every `intents.<name>.mode` is reachable from `.claude/commands/hi.md`.

    The orchestrator only knows what to do with a matched intent if `hi.md`
    documents the procedure for that mode (either an inline section or a path
    to an external command file). Without this check, a new intent row could
    land with no executable instruction — the dual-path drift problem
    (advertised but unreachable).

    Implementation: parse the block delimited by `<!-- sub-mode-procedures-map -->`
    and `<!-- /sub-mode-procedures-map -->` markers in `hi.md`, extract every
    table cell wrapped in backticks, and verify each `intents.*.mode` value
    appears as a literal token. Marker-bounded so the check is robust to other
    files re-using the table format.
    """
    findings: list[Finding] = []
    if not intents:
        return findings

    hi_path = ROOT / ".claude" / "commands" / "hi.md"
    if not hi_path.exists():
        return [
            Finding(
                "ERROR",
                "intents-mode-hi-missing",
                rel(hi_path),
                "`.claude/commands/hi.md` is missing; cannot verify intent mode mappings",
            )
        ]
    text = _read(hi_path)
    block_re = re.compile(
        r"<!--\s*sub-mode-procedures-map\s*-->(.*?)<!--\s*/sub-mode-procedures-map\s*-->",
        re.DOTALL,
    )
    block_match = block_re.search(text)
    if not block_match:
        return [
            Finding(
                "ERROR",
                "intents-mode-map-block-missing",
                rel(hi_path),
                "missing `<!-- sub-mode-procedures-map -->` ... `<!-- /sub-mode-procedures-map -->` block in hi.md",
            )
        ]
    block_text = block_match.group(1)
    # Tokens are anything wrapped in backticks within the table block.
    backtick_re = re.compile(r"`([^`\n]+)`")
    documented_modes = {m.strip() for m in backtick_re.findall(block_text)}

    for intent_name, entry in sorted(intents.items()):
        if not isinstance(entry, dict):
            continue
        mode = entry.get("mode")
        if not isinstance(mode, str) or not mode.strip():
            findings.append(
                Finding(
                    "ERROR",
                    "intents-mode-missing",
                    "harness/intents.toml",
                    f"intent `{intent_name}` has no `mode` field",
                )
            )
            continue
        if mode not in documented_modes:
            findings.append(
                Finding(
                    "ERROR",
                    "intents-mode-unmapped",
                    "harness/intents.toml",
                    f"intent `{intent_name}` mode=`{mode}` not in `.claude/commands/hi.md` Sub-mode procedures map",
                )
            )

    return findings


def check_intents_profile_reads(
    intents: dict[str, dict[str, Any]],
) -> list[Finding]:
    """Verify every `profile_reads` filename exists at `profile/<name>`.

    A renamed `profile/identity.md` would silently degrade routing context —
    the orchestrator's pre-read step would fail open. ERROR rather than WARN
    because silent degradation of a routing precondition is harder to debug
    than a noisy false positive on a fresh clone.
    """
    findings: list[Finding] = []
    if not intents:
        return findings
    profile_dir = ROOT / "profile"
    for intent_name, entry in sorted(intents.items()):
        if not isinstance(entry, dict):
            continue
        reads = entry.get("profile_reads", []) or []
        if not isinstance(reads, list):
            findings.append(
                Finding(
                    "ERROR",
                    "intents-profile-reads-shape",
                    "harness/intents.toml",
                    f"intent `{intent_name}` `profile_reads` must be a list",
                )
            )
            continue
        for fname in reads:
            if not isinstance(fname, str):
                findings.append(
                    Finding(
                        "ERROR",
                        "intents-profile-reads-shape",
                        "harness/intents.toml",
                        f"intent `{intent_name}` `profile_reads` has non-string entry `{fname!r}`",
                    )
                )
                continue
            target = profile_dir / fname
            if not target.exists():
                findings.append(
                    Finding(
                        "ERROR",
                        "intents-profile-reads-missing",
                        "harness/intents.toml",
                        f"intent `{intent_name}` references `profile/{fname}` which does not exist",
                    )
                )
    return findings


def check_agent_pattern_and_used_by(
    intents: dict[str, dict[str, Any]],
    commands: dict[str, str],
) -> list[Finding]:
    """Validate `pattern` and `used_by` on every agent in harness/agents.toml.

    Three checks: (b) pattern in allowed set, (d) used_by drift relative
    to walked expectation, (e) orphan (empty used_by) WARN.
    """
    findings: list[Finding] = []
    data, err = _load_toml(ROOT / "harness" / "agents.toml")
    if err:
        return [err]
    assert data is not None
    registry = data.get("agents", {})
    if not isinstance(registry, dict):
        return findings

    expected = _expected_used_by(intents, commands, registry)

    for name, entry in sorted(registry.items()):
        if not isinstance(entry, dict):
            continue
        # (b) pattern value valid
        pattern_value = entry.get("pattern")
        if pattern_value is None:
            findings.append(
                Finding(
                    "ERROR",
                    "agents-pattern-invalid",
                    "harness/agents.toml",
                    f"agent `{name}` is missing `pattern` field",
                )
            )
        elif pattern_value not in ALLOWED_PATTERNS:
            findings.append(
                Finding(
                    "ERROR",
                    "agents-pattern-invalid",
                    "harness/agents.toml",
                    f"agent `{name}` pattern=`{pattern_value}` not in {sorted(ALLOWED_PATTERNS)}",
                )
            )
        # (d) used_by drift
        stored = entry.get("used_by")
        if not isinstance(stored, list):
            findings.append(
                Finding(
                    "ERROR",
                    "agents-used-by-shape",
                    "harness/agents.toml",
                    f"agent `{name}` is missing `used_by` field (must be a list)",
                )
            )
            stored_set: set[str] = set()
        else:
            stored_set = {s for s in stored if isinstance(s, str)}
        expected_set = set(expected.get(name, []))
        missing = sorted(expected_set - stored_set)
        extra = sorted(stored_set - expected_set)
        if missing or extra:
            parts: list[str] = []
            if missing:
                parts.append(f"missing {missing}")
            if extra:
                parts.append(f"extra {extra}")
            findings.append(
                Finding(
                    "WARN",
                    "agents-used-by-drift",
                    "harness/agents.toml",
                    f"agent `{name}` used_by drift: " + "; ".join(parts) +
                    " (run `python3 scripts/harness_lint.py --fix-used-by`)",
                )
            )
        # (e) orphan
        if not stored_set and not expected_set:
            findings.append(
                Finding(
                    "WARN",
                    "agents-orphan",
                    "harness/agents.toml",
                    f"agent `{name}` has no callers (no intent or command dispatches it)",
                )
            )

    return findings


def fix_used_by() -> int:
    """Rewrite `used_by` lists in harness/agents.toml from the walk.

    Read-modify-write of the agents.toml file. Idempotent: re-running with
    no upstream changes is a no-op. Preserves all other formatting verbatim
    by editing only the `used_by = [...]` block.
    """
    # Refuse to regenerate from partial data. Either load failure (missing
    # intents.toml, invalid TOML, missing command tree) would silently drop
    # references on the rewrite, corrupting the file we are trying to repair.
    intents, intent_findings = load_intents()
    intent_errors = [f for f in intent_findings if f.severity == "ERROR"]
    if intent_errors:
        for f in intent_errors:
            sys.stderr.write(f"harness_lint --fix-used-by: aborting: {f.where}: {f.message}\n")
        sys.stderr.write("harness_lint --fix-used-by: fix the intent registry and retry\n")
        return 2
    commands, command_findings = load_claude_commands()
    command_errors = [f for f in command_findings if f.severity == "ERROR"]
    if command_errors:
        for f in command_errors:
            sys.stderr.write(f"harness_lint --fix-used-by: aborting: {f.where}: {f.message}\n")
        sys.stderr.write("harness_lint --fix-used-by: fix the command registry and retry\n")
        return 2
    agents_path = ROOT / "harness" / "agents.toml"
    if not agents_path.exists():
        sys.stderr.write("harness_lint: harness/agents.toml not found\n")
        return 1
    data, err = _load_toml(agents_path)
    if err:
        sys.stderr.write(f"harness_lint: {err.message}\n")
        return 1
    assert data is not None
    registry = data.get("agents", {})
    if not isinstance(registry, dict):
        sys.stderr.write("harness_lint: harness/agents.toml has no [agents] table\n")
        return 1
    expected = _expected_used_by(intents, commands, registry)

    text = agents_path.read_text(encoding="utf-8")
    new_text = text
    changed_agents: list[str] = []
    # Rewrite each agent's used_by block in place. We match the table header
    # and the existing used_by = [...] block (multi-line), and replace the
    # block contents only — preserving all other fields and ordering.
    for name in sorted(registry.keys()):
        refs = expected.get(name, [])
        formatted = _format_used_by_block(refs)
        # Pattern: `[agents.<name>]` ... `used_by = [...]` (multi-line)
        # Match the table block from its header up to the next `[agents.` or
        # end of file, then within that match replace the used_by block.
        section_re = re.compile(
            rf"(\[agents\.{re.escape(name)}\][^\[]*?)(used_by\s*=\s*\[[^\]]*\])",
            re.DOTALL,
        )

        def _sub(match: re.Match[str], formatted: str = formatted) -> str:
            return match.group(1) + formatted

        new_section, count = section_re.subn(_sub, new_text, count=1)
        if count == 0:
            sys.stderr.write(
                f"harness_lint: --fix-used-by: could not locate `used_by` block for `{name}` (skipped)\n"
            )
            continue
        if new_section != new_text:
            new_text = new_section
            changed_agents.append(name)

    if new_text == text:
        print("harness_lint --fix-used-by: no changes")
        return 0
    agents_path.write_text(new_text, encoding="utf-8")
    print(f"harness_lint --fix-used-by: updated {len(changed_agents)} agent(s): {', '.join(changed_agents)}")
    return 0


def _format_used_by_block(refs: list[str]) -> str:
    """Format a `used_by = [...]` TOML block (matches existing style)."""
    if not refs:
        return "used_by = []"
    lines = ["used_by = ["]
    for ref in refs:
        lines.append(f'    "{ref}",')
    lines.append("]")
    return "\n".join(lines)


MAX_DOC_INDIRECTION_DEPTH = 3
DOC_LINT_ROOTS = (".claude/", "protocols/", "harness/", "scripts/")
DOC_LINT_TOPS = ("AGENTS.md", "CLAUDE.md", "README.md")

# Instruction-level cross-document references. We only count refs that LOOK
# like an instruction to read another file (markdown link, explicit "see/per/
# follow/refer X.md", or arrow `-> X.md`). Bare backticked path mentions in
# prose (footnotes, cross-references, "this is documented alongside X.md")
# are NOT counted; they are passive mentions, not redirections. The goal is
# to catch instruction chains a reader has to follow ("read this, which says
# read that, which says read that"), not every textual mention.
DOC_REF_PATTERNS = [
    re.compile(r"\[[^\]]+\]\(([\w./-]+\.md)\)"),          # markdown link
    re.compile(r"(?:see|per|read|follow|refer to)\s+`?([\w./-]+\.md)`?", re.IGNORECASE),
    re.compile(r"(?:->|→)\s*`?([\w./-]+\.md)`?"),          # arrow pointer
]


def _doc_files() -> list[Path]:
    """Committed .md files we walk for indirection-depth checks."""
    files: list[Path] = []
    for top in DOC_LINT_TOPS:
        p = ROOT / top
        if p.exists():
            files.append(p)
    for root in DOC_LINT_ROOTS:
        base = ROOT / root
        if not base.exists():
            continue
        for p in base.rglob("*.md"):
            files.append(p)
    return files


def _build_doc_graph() -> dict[Path, set[Path]]:
    """Map each committed .md file to the set of other .md files it references."""
    files = _doc_files()
    file_set = {f.resolve() for f in files}
    graph: dict[Path, set[Path]] = {f.resolve(): set() for f in files}
    for src in files:
        try:
            text = src.read_text(encoding="utf-8")
        except OSError:
            continue
        src_dir = src.parent
        for pat in DOC_REF_PATTERNS:
            for match in pat.finditer(text):
                ref = match.group(1)
                if ref.startswith("$OV/") or ref.startswith("//"):
                    continue
                for candidate in (ROOT / ref, src_dir / ref):
                    resolved = candidate.resolve()
                    if resolved in file_set and resolved != src.resolve():
                        graph[src.resolve()].add(resolved)
                        break
    return graph


def check_doc_indirection_depth() -> list[Finding]:
    """Forbid indirection chains deeper than MAX_DOC_INDIRECTION_DEPTH hops
    or any cycle in the cross-document reference graph. A "hop" is one
    `.md` file referencing another. Three hops max: `a.md -> b.md -> c.md`
    is allowed; `a.md -> b.md -> c.md -> d.md` is not.
    """
    findings: list[Finding] = []
    graph = _build_doc_graph()

    def find_long_path_or_cycle(start: Path) -> tuple[list[Path] | None, list[Path] | None]:
        """DFS from start. Return (long_path, cycle_path)."""
        stack: list[tuple[Path, list[Path]]] = [(start, [start])]
        while stack:
            node, path = stack.pop()
            for nxt in graph.get(node, set()):
                if nxt in path:
                    cycle = path[path.index(nxt):] + [nxt]
                    return None, cycle
                new_path = path + [nxt]
                if len(new_path) > MAX_DOC_INDIRECTION_DEPTH:
                    return new_path, None
                stack.append((nxt, new_path))
        return None, None

    flagged: set[tuple[str, ...]] = set()
    for start in sorted(graph.keys()):
        long_path, cycle = find_long_path_or_cycle(start)
        if cycle is not None:
            key = tuple(p.relative_to(ROOT).as_posix() for p in cycle)
            if key in flagged:
                continue
            flagged.add(key)
            findings.append(
                Finding(
                    "ERROR",
                    "doc-indirection-cycle",
                    key[0],
                    f"cross-document reference cycle: {' -> '.join(key)}",
                )
            )
        elif long_path is not None:
            key = tuple(p.relative_to(ROOT).as_posix() for p in long_path)
            if key in flagged:
                continue
            flagged.add(key)
            findings.append(
                Finding(
                    "ERROR",
                    "doc-indirection-depth",
                    key[0],
                    f"cross-document indirection chain too deep ({len(key)} hops, max {MAX_DOC_INDIRECTION_DEPTH}): {' -> '.join(key)}",
                )
            )
    return findings


def run_lints() -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(check_root_files())
    agents, agent_findings = load_claude_agents()
    findings.extend(agent_findings)
    commands, command_findings = load_claude_commands()
    findings.extend(command_findings)
    model_findings, models = check_models(agents)
    findings.extend(model_findings)
    findings.extend(check_capabilities())
    findings.extend(check_agent_registry(agents, models))
    findings.extend(check_commands(commands))
    findings.extend(check_harness_readme())
    findings.extend(check_atelier_skill())
    findings.extend(check_scripts_zk_paths())
    intents, intent_findings = load_intents()
    findings.extend(intent_findings)
    # Resolve intent agent references against both registries:
    #   - `agents` is from load_claude_agents() (.claude/agents/*.md filesystem
    #     walk); canonical for Claude Code subagent dispatch.
    #   - `harness_agents_data` is from harness/agents.toml; canonical for
    #     Codex parity. A broken reference in either is an error.
    harness_agents_raw, _ = _load_toml(ROOT / "harness" / "agents.toml")
    harness_agents_data = (harness_agents_raw or {}).get("agents", {}) or {}
    findings.extend(check_intents_registry(intents, agents, harness_agents_data))
    findings.extend(check_intents_mode_mapping(intents))
    findings.extend(check_intents_profile_reads(intents))
    findings.extend(check_agent_pattern_and_used_by(intents, commands))
    findings.extend(check_doc_indirection_depth())
    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f.severity, 99), f.code, f.where, f.message))
    return findings


def format_table(findings: list[Finding]) -> str:
    if not findings:
        return "harness_lint: clean (no findings)\n"

    counts = {"ERROR": 0, "WARN": 0, "INFO": 0}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1

    lines = [
        f"harness lint report: {counts['ERROR']} error, {counts['WARN']} warn, {counts['INFO']} info",
        "",
    ]
    for finding in findings:
        lines.append(f"[{finding.severity:5s}] {finding.code}")
        lines.append(f"    where:   {finding.where}")
        lines.append(f"    message: {finding.message}")
        lines.append("")
    return "\n".join(lines)


def format_json(findings: list[Finding]) -> str:
    payload = {
        "counts": {
            "error": sum(1 for f in findings if f.severity == "ERROR"),
            "warn": sum(1 for f in findings if f.severity == "WARN"),
            "info": sum(1 for f in findings if f.severity == "INFO"),
        },
        "findings": [f.to_dict() for f in findings],
    }
    return json.dumps(payload, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scripts/harness_lint.py",
        description="Check Claude Code and Codex harness portability.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    parser.add_argument(
        "--fix-used-by",
        action="store_true",
        help="Regenerate `used_by` lists in harness/agents.toml from the intents/commands walk, then exit. Mutating; off by default.",
    )
    args = parser.parse_args(argv)

    if args.fix_used_by:
        return fix_used_by()

    findings = run_lints()
    if args.json:
        sys.stdout.write(format_json(findings))
    else:
        sys.stdout.write(format_table(findings))
    return 1 if any(f.severity == "ERROR" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
