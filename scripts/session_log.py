#!/usr/bin/env python3
"""
session_log.py: Create a session log skeleton from CLI args.

Called by the orchestrator at session end. Generates the markdown file
with header fields pre-filled. The orchestrator appends section content
via the Write or Edit tool after this script creates the skeleton.

Usage:
    scripts/session_log.py --type reflection --duration 25
    scripts/session_log.py --type decision --duration 40 --model opus

Creates: zk/sessions/YYYY-MM-DD-<type>.md (auto-increments on collision).
Prints the created file path to stdout for the orchestrator to use.

Exit code: 0 on success, 1 on error.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

SESSIONS_DIR = Path("zk/sessions")

VALID_TYPES = {
    "reflection",
    "review",
    "weekly",
    "decision",
    "exploration",
    "energy-audit",
    "reading",
    "curate",
    "introspect",
    "meeting",
    "deep-dive",
    "system-review",
}

SKELETON = """\
---session-log---
session_id: {session_id}
date: {date}
type: {session_type}
duration_estimate: {duration}
model: {model}
---end-session-log-header---

## Agents Dispatched
| Agent | Task | Result | Turns Used |
|-------|------|--------|------------|

## Search Log
| Query | Tool | Hits | Useful |
|-------|------|------|--------|

## Gate Results
| Gate | Score/Pass | Notes |
|------|-----------|-------|

## Questions & Engagement
| Question | Depth | Landed | User Response |
|----------|-------|--------|---------------|

## Frameworks Applied
| Framework | Applied By | Fit Score | Cross-validated |
|-----------|-----------|-----------|-----------------|

## Continuity
- Previous session referenced: none
- Seed planted:
- Callbacks checked:

## Decisions & Branches

## Anomalies

## Harness Assumptions Exercised
"""


def _next_path(session_type: str, today: date) -> tuple[Path, str]:
    """Find the next available path, incrementing on collision."""
    base_id = f"{today.isoformat()}-{session_type}"
    candidate = SESSIONS_DIR / f"{base_id}.md"
    if not candidate.exists():
        return candidate, base_id

    n = 2
    while True:
        sid = f"{base_id}-{n}"
        candidate = SESSIONS_DIR / f"{sid}.md"
        if not candidate.exists():
            return candidate, sid
        n += 1
        if n > 99:
            break
    return candidate, f"{base_id}-{n}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scripts/session_log.py",
        description="Create a session log skeleton.",
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=sorted(VALID_TYPES),
        help="Session type.",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=0,
        help="Estimated session duration in minutes.",
    )
    parser.add_argument(
        "--model",
        default="opus",
        help="Orchestrator model used.",
    )
    args = parser.parse_args(argv)

    # Late-sleep rule: before 03:00, use previous day.
    now = datetime.now()
    if now.hour < 3:
        from datetime import timedelta
        today = (now - timedelta(days=1)).date()
    else:
        today = now.date()

    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    path, session_id = _next_path(args.type, today)

    content = SKELETON.format(
        session_id=session_id,
        date=today.isoformat(),
        session_type=args.type,
        duration=args.duration,
        model=args.model,
    )

    path.write_text(content, encoding="utf-8")
    sys.stdout.write(path.as_posix() + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
