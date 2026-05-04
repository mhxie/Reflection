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
    expect(payload["counts"] == {"error": 0, "warn": 0, "info": 0}, "harness_lint.py is not clean")
    expect(payload["findings"] == [], "harness_lint.py returned findings")


def check_status() -> None:
    payload = json.loads(run(["scripts/atelier.py", "status", "--json"]))
    registries = payload["registries"]
    expect(registries["commands"] >= 10, "expected at least 10 portable commands")
    expect(registries["agents"] >= 10, "expected at least 10 portable agents")
    expect(registries["model_profiles"] >= 3, "expected model profiles")
    expect(registries["capabilities"] >= 5, "expected capabilities")
    expect(payload["roots"]["AGENTS.md"]["exists"], "AGENTS.md missing from status")
    expect(payload["roots"]["CLAUDE.md"]["exists"], "CLAUDE.md missing from status")


def check_filtered_json() -> None:
    commands = json.loads(run(["scripts/atelier.py", "commands", "--category", "ops", "--json"]))
    expect("lint" in commands, "ops commands should include lint")
    expect(commands["lint"]["source"] == ".claude/commands/lint.md", "lint source drift")

    agents = json.loads(run(["scripts/atelier.py", "agents", "--profile", "core_intelligence", "--json"]))
    expect("researcher" in agents, "core_intelligence agents should include researcher")
    expect(agents["researcher"]["source"] == ".claude/agents/researcher.md", "researcher source drift")


def check_prompts_and_sources() -> None:
    prompt = run(["scripts/atelier.py", "prompt", "reflect", "--", "smoke context"])
    expect(".claude/commands/reflect.md" in prompt, "reflect prompt missing source path")
    expect("AGENTS.md" in prompt, "reflect prompt missing AGENTS.md instruction")
    expect("smoke context" in prompt, "reflect prompt missing context")

    agent_prompt = run(["scripts/atelier.py", "agent-prompt", "reviewer", "--", "smoke review"])
    expect(".claude/agents/reviewer.md" in agent_prompt, "reviewer prompt missing source path")
    expect("smoke review" in agent_prompt, "reviewer prompt missing context")

    command_source = run(["scripts/atelier.py", "source", "lint", "--path-only"]).strip()
    expect(command_source == ".claude/commands/lint.md", "lint path-only source drift")

    agent_source = run(["scripts/atelier.py", "agent-source", "reviewer", "--path-only"]).strip()
    expect(agent_source == ".claude/agents/reviewer.md", "reviewer path-only source drift")


def check_run_dry() -> None:
    prompt = run(["scripts/atelier.py", "run", "reflect", "smoke context", "--print"])
    expect(".claude/commands/reflect.md" in prompt, "run --print prompt missing source path")
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

