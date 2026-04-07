#!/usr/bin/env python3
"""
lint.py: Corpus-level structural lints over zk/wiki/ + the sync manifest.

trust.py enforces per-note structural integrity (items 1-10 of
protocols/wiki-schema.md). lint.py layers on checks that are only visible
at the corpus level — things no single-note parser can see:

  1. Per-note parse errors (pass-through from trust.py).
  2. Duplicate titles across wiki entries (breaks @cite title resolution,
     which is how trust.py's edge builder finds targets).
  3. Slug / title alignment (file stem should match the slugified H1 so
     /sync's manifest keys stay stable across renames).
  4. Manifest drift:
       a. Dead manifest entries — slug in zk/.sync-manifest.json whose
          file no longer exists on disk (rename, delete, or never
          committed).
       b. Unsynced wiki entries — file in zk/wiki/ with no manifest row.
          Informational, not a failure.

Cross-note anchor date consistency is intentionally NOT checked: per
protocols/wiki-schema.md, `valid_at` records the date the marker was
added to its home note, so the same paper being anchored from two notes
on different days is the normal case, not a smell.

Output: human table by default, `--json` for machine consumption.
Exit code: 0 if no errors, 1 if any ERROR-level finding, 2 on CLI/IO error.
WARN and INFO findings do not affect the exit code.

CLI:
    scripts/lint.py                 human report over zk/wiki/
    scripts/lint.py --json          structured output
    scripts/lint.py --fix-manifest  prune dead manifest entries after confirm

Paths are project-relative. Run from the repo root.

See also:
    scripts/trust.py               per-note parser + TrustRank scoring
    .claude/commands/lint.md       orchestrator flow
    protocols/wiki-schema.md       schema enforced per-note by trust.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

# trust.py lives next to this file and is importable as a library.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from trust import (  # noqa: E402
    WIKI_DIR,
    WikiNote,
    _resolve_cites,
    load_wiki,
)

MANIFEST_PATH = Path("zk/.sync-manifest.json")

SEVERITY_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2}

SLUG_RE = re.compile(r"[^a-z0-9]+")


class Finding:
    __slots__ = ("severity", "code", "where", "message")

    def __init__(self, severity: str, code: str, where: str, message: str):
        self.severity = severity
        self.code = code
        self.where = where
        self.message = message

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "code": self.code,
            "where": self.where,
            "message": self.message,
        }


def slugify(title: str) -> str:
    """Mirror the convention used by zk/wiki/*.md filenames: lowercase,
    non-alnum → `-`, collapse runs, strip leading/trailing hyphens."""
    s = SLUG_RE.sub("-", title.lower()).strip("-")
    return s


def load_manifest() -> tuple[dict, list[Finding]]:
    findings: list[Finding] = []
    if not MANIFEST_PATH.exists():
        findings.append(
            Finding(
                "INFO",
                "manifest-missing",
                MANIFEST_PATH.as_posix(),
                "manifest not found — treat every wiki entry as never synced",
            )
        )
        return {"schema": 1, "entries": {}}, findings
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        findings.append(
            Finding(
                "ERROR",
                "manifest-unreadable",
                MANIFEST_PATH.as_posix(),
                f"cannot parse manifest: {e}",
            )
        )
        return {"schema": 1, "entries": {}}, findings
    if not isinstance(data, dict) or "entries" not in data:
        findings.append(
            Finding(
                "ERROR",
                "manifest-malformed",
                MANIFEST_PATH.as_posix(),
                "manifest missing `entries` key",
            )
        )
        return {"schema": 1, "entries": {}}, findings
    if not isinstance(data["entries"], dict):
        findings.append(
            Finding(
                "ERROR",
                "manifest-malformed",
                MANIFEST_PATH.as_posix(),
                f"manifest `entries` must be an object, got {type(data['entries']).__name__}",
            )
        )
        # Return a safe empty entries dict so downstream checks don't crash.
        return {"schema": data.get("schema", 1), "entries": {}}, findings
    return data, findings


def check_parse_errors(notes: list[WikiNote]) -> list[Finding]:
    findings: list[Finding] = []
    for note in notes:
        for err in note.parse_errors:
            findings.append(
                Finding(
                    "ERROR",
                    "parse-error",
                    note.path.as_posix(),
                    err,
                )
            )
    return findings


def check_duplicate_titles(notes: list[WikiNote]) -> list[Finding]:
    findings: list[Finding] = []
    by_title: dict[str, list[Path]] = {}
    for note in notes:
        if not note.title:
            continue
        by_title.setdefault(note.title, []).append(note.path)
    for title, paths in by_title.items():
        if len(paths) > 1:
            for p in paths:
                others = [q.as_posix() for q in paths if q != p]
                findings.append(
                    Finding(
                        "ERROR",
                        "duplicate-title",
                        p.as_posix(),
                        f"title `{title}` also used by: {', '.join(others)} (breaks @cite target resolution)",
                    )
                )
    return findings


def check_slug_alignment(notes: list[WikiNote]) -> list[Finding]:
    findings: list[Finding] = []
    for note in notes:
        if not note.title:
            continue
        expected = slugify(note.title)
        actual = note.path.stem
        if actual != expected:
            findings.append(
                Finding(
                    "WARN",
                    "slug-mismatch",
                    note.path.as_posix(),
                    f"filename stem `{actual}` does not match slugified title `{expected}` — "
                    f"rename the file or adjust the H1 so /sync manifest keys stay stable",
                )
            )
    return findings


def check_manifest_drift(
    notes: list[WikiNote], manifest: dict
) -> list[Finding]:
    findings: list[Finding] = []
    entries = manifest.get("entries", {}) or {}
    wiki_slugs = {note.path.stem for note in notes}

    for slug in entries.keys():
        if slug not in wiki_slugs:
            findings.append(
                Finding(
                    "WARN",
                    "manifest-dead-entry",
                    f"{MANIFEST_PATH.as_posix()}#{slug}",
                    f"manifest references slug `{slug}` but zk/wiki/{slug}.md does not exist "
                    f"(rename, delete, or orphaned stub) — re-run with --fix-manifest to prune",
                )
            )

    for slug in wiki_slugs:
        if slug not in entries:
            findings.append(
                Finding(
                    "INFO",
                    "unsynced-entry",
                    f"zk/wiki/{slug}.md",
                    "wiki entry not yet synced to Reflect — run /sync to push",
                )
            )
    return findings


def run_lints(notes: list[WikiNote], manifest: dict) -> list[Finding]:
    findings: list[Finding] = []
    # Resolve @cite targets so dangling-cite errors land on the source note
    # before we read parse_errors. trust.py's scoring does this implicitly;
    # lint.py calls it explicitly because we don't score here.
    _resolve_cites(notes)
    findings.extend(check_parse_errors(notes))
    findings.extend(check_duplicate_titles(notes))
    findings.extend(check_slug_alignment(notes))
    findings.extend(check_manifest_drift(notes, manifest))
    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f.severity, 99), f.code, f.where))
    return findings


def fix_manifest(manifest: dict, notes: list[WikiNote]) -> list[str]:
    """Remove manifest entries whose slug no longer maps to a wiki file.
    Returns the list of pruned slugs. Caller is responsible for writing
    the manifest back to disk."""
    wiki_slugs = {note.path.stem for note in notes}
    entries = manifest.get("entries", {}) or {}
    dead = [slug for slug in entries.keys() if slug not in wiki_slugs]
    for slug in dead:
        del entries[slug]
    manifest["entries"] = entries
    return dead


def format_table(findings: list[Finding]) -> str:
    if not findings:
        return "lint: clean (no findings)\n"

    counts = {"ERROR": 0, "WARN": 0, "INFO": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    lines = []
    lines.append(
        f"lint report — {counts['ERROR']} error, {counts['WARN']} warn, {counts['INFO']} info"
    )
    lines.append("")
    for f in findings:
        lines.append(f"[{f.severity:5s}] {f.code}")
        lines.append(f"    where:   {f.where}")
        lines.append(f"    message: {f.message}")
        lines.append("")
    return "\n".join(lines)


def format_json(findings: list[Finding]) -> str:
    payload = {
        "wiki_dir": WIKI_DIR.as_posix(),
        "manifest_path": MANIFEST_PATH.as_posix(),
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
        prog="scripts/lint.py",
        description="Corpus-level structural lints over zk/wiki/ and the sync manifest.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON for orchestrator consumption.",
    )
    parser.add_argument(
        "--fix-manifest",
        action="store_true",
        help="Prune dead entries from zk/.sync-manifest.json and re-run lints.",
    )
    args = parser.parse_args(argv)

    try:
        notes = load_wiki(date.today(), only=None)
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 2

    manifest, manifest_findings = load_manifest()

    if args.fix_manifest:
        dead = fix_manifest(manifest, notes)
        if dead:
            MANIFEST_PATH.write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
            sys.stderr.write(
                f"lint: pruned {len(dead)} dead manifest entries: {', '.join(dead)}\n"
            )
        else:
            sys.stderr.write("lint: no dead manifest entries to prune\n")

    findings = manifest_findings + run_lints(notes, manifest)
    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f.severity, 99), f.code, f.where))

    if args.json:
        sys.stdout.write(format_json(findings))
    else:
        sys.stdout.write(format_table(findings))

    return 1 if any(f.severity == "ERROR" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
