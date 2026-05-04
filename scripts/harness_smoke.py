#!/usr/bin/env python3
"""
harness_smoke.py: deterministic smoke test for the portable harness helpers.

This intentionally avoids `$OV/` and network access. It only checks the public
repo harness surface: harness_lint.py, atelier.py JSON outputs, source path
lookups, and generated prompts.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


class SmokeFailure(Exception):
    pass


def run(args: list[str]) -> str:
    result = subprocess.run(
        [PYTHON, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SmokeFailure(
            f"`{PYTHON} {' '.join(args)}` failed with exit {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result.stdout


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def check_harness_lint() -> None:
    payload = json.loads(run(["scripts/harness_lint.py", "--json"]))
    counts = payload["counts"]
    expect(counts.get("error", 0) == 0, f"harness_lint.py reports {counts.get('error', 0)} error(s)")
    expect(counts.get("warn", 0) == 0, f"harness_lint.py reports {counts.get('warn', 0)} warn(s)")
    error_or_warn = [f for f in payload["findings"] if f.get("severity") in ("ERROR", "WARN")]
    expect(error_or_warn == [], f"harness_lint.py returned {len(error_or_warn)} error/warn finding(s)")


def check_status() -> None:
    payload = json.loads(run(["scripts/atelier.py", "status", "--json"]))
    registries = payload["registries"]
    expect(registries["commands"] >= 10, "expected at least 10 portable commands")
    expect(registries["agents"] >= 10, "expected at least 10 portable agents")
    expect(registries["models"] >= 3, "expected model identities")
    expect(registries["capabilities"] >= 5, "expected capabilities")
    expect(payload["roots"]["AGENTS.md"]["exists"], "AGENTS.md missing from status")
    expect(payload["roots"]["CLAUDE.md"]["exists"], "CLAUDE.md missing from status")
    # The voices aggregation must surface model names that real agents bind to.
    members = payload.get("agents_by_voices_member", {})
    expect("opus" in members, "agents_by_voices_member should list opus (researcher et al. bind to it)")
    expect("deepseek_pro_max" in members, "agents_by_voices_member should list deepseek_pro_max (paired-leg)")


def check_filtered_json() -> None:
    commands = json.loads(run(["scripts/atelier.py", "commands", "--category", "ops", "--json"]))
    expect("lint" in commands, "ops commands should include lint")
    expect(commands["lint"]["source"] == ".claude/commands/lint.md", "lint source drift")

    # researcher binds voices = {native = "opus", direct = "deepseek_pro_max"},
    # so --member opus must include researcher and the other entries must also
    # bind opus to one of their voice legs.
    agents = json.loads(run(["scripts/atelier.py", "agents", "--member", "opus", "--json"]))
    expect("researcher" in agents, "agents --member opus should include researcher")
    expect(agents["researcher"]["source"] == ".claude/agents/researcher.md", "researcher source drift")
    for name, entry in agents.items():
        voices = entry.get("voices") or {}
        members = list(voices.values()) if isinstance(voices, dict) else []
        expect(
            "opus" in members,
            f"agents --member opus returned `{name}` whose voices is {voices}",
        )

    # external-reviewer binds voices = {direct = "deepseek_pro_max", codex = "codex_gpt55_max"};
    # --member codex_gpt55_max should isolate it (script-driven, no .claude source).
    ext = json.loads(run(["scripts/atelier.py", "agents", "--member", "codex_gpt55_max", "--json"]))
    expect("external-reviewer" in ext, "agents --member codex_gpt55_max should include external-reviewer")


def check_prompts_and_sources() -> None:
    prompt = run(["scripts/atelier.py", "prompt", "hi", "--", "smoke context"])
    expect(".claude/commands/hi.md" in prompt, "hi prompt missing source path")
    expect("AGENTS.md" in prompt, "hi prompt missing AGENTS.md instruction")
    expect("smoke context" in prompt, "hi prompt missing context")

    agent_prompt = run(["scripts/atelier.py", "agent-prompt", "reviewer", "--", "smoke review"])
    expect(".claude/agents/reviewer.md" in agent_prompt, "reviewer prompt missing source path")
    expect("smoke review" in agent_prompt, "reviewer prompt missing context")

    command_source = run(["scripts/atelier.py", "source", "lint", "--path-only"]).strip()
    expect(command_source == ".claude/commands/lint.md", "lint path-only source drift")

    agent_source = run(["scripts/atelier.py", "agent-source", "reviewer", "--path-only"]).strip()
    expect(agent_source == ".claude/agents/reviewer.md", "reviewer path-only source drift")


def check_run_dry() -> None:
    prompt = run(["scripts/atelier.py", "run", "hi", "smoke context", "--print"])
    expect(".claude/commands/hi.md" in prompt, "run --print prompt missing source path")
    expect("AGENTS.md" in prompt, "run --print prompt missing AGENTS.md instruction")
    expect("smoke context" in prompt, "run --print prompt missing context")

    # --resume + --print should not error and should still produce the prompt
    resume_prompt = run(["scripts/atelier.py", "run", "promote", "smoke", "--resume", "--print"])
    expect(".claude/commands/promote.md" in resume_prompt, "run --resume --print missing source path")


def main() -> int:
    checks = [
        ("harness lint", check_harness_lint),
        ("status", check_status),
        ("filtered json", check_filtered_json),
        ("prompts and sources", check_prompts_and_sources),
        ("run dry", check_run_dry),
    ]
    try:
        for label, check in checks:
            check()
            print(f"ok: {label}")
    except SmokeFailure as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("harness_smoke: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())

