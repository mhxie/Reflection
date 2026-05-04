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

Exit code: 0 if no ERROR-level findings, 1 if any ERROR-level finding.
argparse returns 2 on CLI usage errors.
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


def check_models(agents: dict[str, dict[str, str]]) -> list[Finding]:
    """Validate harness/models.toml schema + cross-check bindings if present.

    harness/models.toml (committed) holds tier semantics: profile names with
    rationale + invocation pattern, and agent->profile assignments. The
    binding values (claude_code, codex, direct_api, direct_api_base,
    api_env, direct_api_extras, direct_api_timeout, codex_reasoning_effort)
    live in profile/models.toml (gitignored). When the binding file is
    present, this check cross-validates schema integrity end-to-end; when
    absent, only the schema half is enforced.
    """
    findings: list[Finding] = []
    data, err = _load_toml(ROOT / "harness" / "models.toml")
    if err:
        return [err]
    assert data is not None

    profiles = data.get("profiles", {})
    agent_map = data.get("agents", {})
    if not isinstance(profiles, dict) or not profiles:
        findings.append(
            Finding("ERROR", "models-profiles", "harness/models.toml", "no model profiles declared")
        )
    if not isinstance(agent_map, dict) or not agent_map:
        findings.append(
            Finding("ERROR", "models-agents", "harness/models.toml", "no agent model mappings declared")
        )
        return findings

    for profile_name, profile in sorted(profiles.items()):
        if not isinstance(profile, dict):
            findings.append(
                Finding("ERROR", "models-profile-shape", "harness/models.toml", f"profile `{profile_name}` is not a table")
            )
            continue
        # Schema-side required keys: rationale + invocation pattern. The
        # provider/model bindings live in profile/models.toml.
        for key in ("rationale", "invocation"):
            if not profile.get(key):
                findings.append(
                    Finding(
                        "ERROR",
                        "models-profile-field",
                        "harness/models.toml",
                        f"profile `{profile_name}` is missing `{key}`",
                    )
                )
        invocation = profile.get("invocation")
        if invocation is not None and invocation not in ("single", "dual", "shadow"):
            findings.append(
                Finding(
                    "ERROR",
                    "models-invocation-value",
                    "harness/models.toml",
                    f"profile `{profile_name}` has invocation=`{invocation}` (must be 'single', 'dual', or 'shadow')",
                )
            )
        # Binding-shaped keys must NOT appear in the committed schema; they
        # belong to profile/models.toml. Catches accidental leakage of
        # provider names back into the public file.
        leaked_binding_keys = sorted(
            k for k in profile
            if k in ("claude_code", "codex", "codex_reasoning_effort",
                     "direct_api", "direct_api_base", "direct_api_extras",
                     "direct_api_timeout", "api_env",
                     "shadow_api", "shadow_api_base", "shadow_api_extras",
                     "shadow_api_timeout", "shadow_api_env")
        )
        for k in leaked_binding_keys:
            findings.append(
                Finding(
                    "ERROR",
                    "models-binding-in-schema",
                    "harness/models.toml",
                    f"profile `{profile_name}` has binding key `{k}` (move to profile/models.toml)",
                )
            )

    for agent_name, fields in sorted(agents.items()):
        entry = agent_map.get(agent_name)
        if not isinstance(entry, dict):
            findings.append(
                Finding(
                    "ERROR",
                    "models-agent-missing",
                    "harness/models.toml",
                    f"agent `{agent_name}` from {fields['path']} has no profile mapping",
                )
            )
            continue
        profile = entry.get("profile")
        if profile not in profiles:
            findings.append(
                Finding(
                    "ERROR",
                    "models-profile-missing",
                    "harness/models.toml",
                    f"agent `{agent_name}` references unknown profile `{profile}`",
                )
            )

    extra_agents = sorted(set(agent_map) - set(agents))
    for agent_name in extra_agents:
        findings.append(
            Finding(
                "WARN",
                "models-agent-extra",
                "harness/models.toml",
                f"profile mapping exists for `{agent_name}` but no .claude agent file was found",
            )
        )

    findings.extend(_check_model_bindings(agents, profiles))
    return findings


def _check_model_bindings(
    agents: dict[str, dict[str, str]],
    profiles: dict[str, Any],
) -> list[Finding]:
    """Cross-check profile/models.toml bindings against schema + frontmatter.

    Soft check: if the bindings file is missing, return silently. Absence is
    the expected state on fresh clones (the file is gitignored, machine-local)
    and the smoke test asserts zero findings — emitting INFO here would break
    that contract. When present, verify (a) every schema profile has a
    binding entry, (b) every agent's claude_code_model matches its
    .claude/agents/<name>.md frontmatter `model:` field.
    """
    findings: list[Finding] = []
    bindings_path = ROOT / "profile" / "models.toml"
    if not bindings_path.exists():
        return findings
    data, err = _load_toml(bindings_path)
    if err:
        return [err]
    assert data is not None
    binding_profiles = data.get("profiles", {}) or {}
    binding_agents = data.get("agents", {}) or {}

    for profile_name in sorted(profiles):
        if profile_name not in binding_profiles:
            findings.append(
                Finding(
                    "WARN",
                    "models-binding-profile-missing",
                    "profile/models.toml",
                    f"schema profile `{profile_name}` has no binding entry",
                )
            )
            continue

        # Schema-declared invocation imposes binding requirements.
        invocation = (profiles.get(profile_name) or {}).get("invocation")
        binding = binding_profiles.get(profile_name) or {}
        if invocation == "dual":
            for key in ("direct_api", "direct_api_base", "api_env"):
                if not binding.get(key):
                    findings.append(
                        Finding(
                            "ERROR",
                            "models-dual-binding-incomplete",
                            "profile/models.toml",
                            f"profile `{profile_name}` is invocation='dual' but binding has no `{key}`",
                        )
                    )
        if invocation == "shadow":
            for key in ("shadow_api", "shadow_api_base", "shadow_api_env"):
                if not binding.get(key):
                    findings.append(
                        Finding(
                            "ERROR",
                            "models-shadow-binding-incomplete",
                            "profile/models.toml",
                            f"profile `{profile_name}` is invocation='shadow' but binding has no `{key}`",
                        )
                    )

    for agent_name, fields in sorted(agents.items()):
        entry = binding_agents.get(agent_name)
        if not isinstance(entry, dict):
            continue
        claude_model = entry.get("claude_code_model")
        frontmatter_model = fields.get("model")
        if claude_model and frontmatter_model and claude_model != frontmatter_model:
            findings.append(
                Finding(
                    "WARN",
                    "models-claude-drift",
                    fields["path"],
                    f"frontmatter model `{frontmatter_model}` differs from binding `{claude_model}`",
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


def check_agent_registry(agents: dict[str, dict[str, str]]) -> list[Finding]:
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

    models, model_err = _load_toml(ROOT / "harness" / "models.toml")
    if model_err:
        findings.append(model_err)
        models = {}
    model_profiles = (models or {}).get("profiles", {})
    model_agents = (models or {}).get("agents", {})

    required_fields = (
        "source",
        "model_profile",
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
        model_profile = entry.get("model_profile")
        expected_profile = model_agents.get(name, {}).get("profile") if isinstance(model_agents.get(name), dict) else None
        if model_profile != expected_profile:
            findings.append(
                Finding(
                    "ERROR",
                    "agents-registry-model-drift",
                    "harness/agents.toml",
                    f"agent `{name}` model profile `{model_profile}` differs from harness/models.toml `{expected_profile}`",
                )
            )
        if model_profile not in model_profiles:
            findings.append(
                Finding(
                    "ERROR",
                    "agents-registry-model-profile",
                    "harness/agents.toml",
                    f"agent `{name}` references unknown model profile `{model_profile}`",
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
        if name not in agents:
            findings.append(
                Finding(
                    "WARN",
                    "agents-registry-entry-extra",
                    "harness/agents.toml",
                    f"registry agent `{name}` has no .claude agent source",
                )
            )
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


def run_lints() -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(check_root_files())
    agents, agent_findings = load_claude_agents()
    findings.extend(agent_findings)
    commands, command_findings = load_claude_commands()
    findings.extend(command_findings)
    findings.extend(check_models(agents))
    findings.extend(check_capabilities())
    findings.extend(check_agent_registry(agents))
    findings.extend(check_commands(commands))
    findings.extend(check_harness_readme())
    findings.extend(check_atelier_skill())
    findings.extend(check_scripts_zk_paths())
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
    args = parser.parse_args(argv)

    findings = run_lints()
    if args.json:
        sys.stdout.write(format_json(findings))
    else:
        sys.stdout.write(format_table(findings))
    return 1 if any(f.severity == "ERROR" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
