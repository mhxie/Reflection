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
  4. Graph topology (inspired by llm_wiki's graph-insights):
       a. Orphan entry (WARN) — wiki entry with 0 inbound @cite edges
          from other entries, meaning no trust propagates to it.
       b. No outbound cite (INFO) — entry that @cites nothing, meaning
          it does not propagate trust to any other entry.
       c. Shared anchor, no cite (INFO) — two entries reference the same
          @anchor source but have no @cite edge between them: a candidate
          cross-reference that the trust graph is missing.
  5. Manifest drift:
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
    BARE_CITE_RE,
    FENCE_CLOSE_RE,
    FENCE_OPEN_RE,
    WIKI_DIR,
    WikiNote,
    _resolve_cites,
    load_wiki,
)

MANIFEST_PATH = Path("zk/.sync-manifest.json")
VOCABULARY_PATH = Path(__file__).resolve().parent / "wiki_vocabulary.txt"

SEVERITY_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2}

# Path to optional file listing URL prefixes to skip in readwise-missing check.
# One prefix per line. Intended for private repo URLs where git is the evidence.
READWISE_SKIP_FILE = Path(__file__).resolve().parent / "readwise_skip_domains.txt"

# --- Unfounded-term detection regexes ---
# ALL-CAPS acronyms (2+ chars), e.g. SIMD, MVCC, OCC
ACRONYM_RE = re.compile(r"\b([A-Z][A-Z0-9]{1,})\b")
# CamelCase words, e.g. PyArrow, RecordBatch, DataLoader
CAMELCASE_RE = re.compile(r"\b([A-Z][a-z]+(?:[A-Z][a-z0-9]*)+)\b")
# Backtick-wrapped terms, e.g. `take_rows()`, `RecordBatch`
BACKTICK_RE = re.compile(r"`([^`]+)`")

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


def title_to_stem(title: str) -> str:
    """Wiki filenames use the H1 title verbatim as the file stem (title-case
    with spaces).  This function is the identity transform, but exists as a
    named contract so the slug-alignment check documents its expectation."""
    return title


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
        expected = title_to_stem(note.title)
        actual = note.path.stem
        if actual != expected:
            findings.append(
                Finding(
                    "WARN",
                    "slug-mismatch",
                    note.path.as_posix(),
                    f"filename stem `{actual}` does not match title `{expected}` — "
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


def check_graph_topology(notes: list[WikiNote]) -> list[Finding]:
    """Graph-level checks over the @cite / @anchor network.

    Inspired by llm_wiki's graph-insights: detect orphan entries, entries
    with no outbound cites, and entries that share @anchor sources but lack
    @cite edges between them.
    """
    findings: list[Finding] = []
    ok_notes = [n for n in notes if n.integrity_ok() and n.title]

    if len(ok_notes) < 2:
        # With fewer than 2 entries the graph topology checks are vacuous.
        return findings

    # Build cite edge sets (note-level, not claim-level).
    # inbound[path] = set of paths that cite this note
    # outbound[path] = set of paths this note cites
    title_to_path: dict[str, Path] = {}
    for n in ok_notes:
        if n.title is not None:
            title_to_path[n.title] = n.path
    inbound: dict[Path, set[Path]] = {n.path: set() for n in ok_notes}
    outbound: dict[Path, set[Path]] = {n.path: set() for n in ok_notes}

    for note in ok_notes:
        for claim in note.claims:
            for c in claim.cites:
                target_title = c.fields.get("_cite_title", "")
                target_path = title_to_path.get(target_title)
                if target_path and target_path != note.path:
                    outbound[note.path].add(target_path)
                    inbound[target_path].add(note.path)

    # 1. orphan-entry: no inbound @cite edges from any other note.
    for note in ok_notes:
        if not inbound[note.path]:
            findings.append(
                Finding(
                    "WARN",
                    "orphan-entry",
                    note.path.as_posix(),
                    f"no other wiki entry cites `{note.title}` — "
                    f"add @cite markers from related entries to enable trust propagation",
                )
            )

    # 2. no-outbound-cite: entry cites nothing.
    for note in ok_notes:
        if not outbound[note.path]:
            findings.append(
                Finding(
                    "INFO",
                    "no-outbound-cite",
                    note.path.as_posix(),
                    f"`{note.title}` does not @cite any other wiki entry",
                )
            )

    # 3. shared-anchor-no-cite: two entries share an @anchor source but
    #    have no @cite edge between them (in either direction).
    #    This is the "surprising connection" signal from llm_wiki.
    anchor_to_notes: dict[str, set[Path]] = {}
    for note in ok_notes:
        for claim in note.claims:
            for a in claim.anchors:
                node_id = a.fields.get("_node_id", "")
                if node_id:
                    anchor_to_notes.setdefault(node_id, set()).add(note.path)

    reported_pairs: set[tuple[str, str]] = set()
    for anchor_id, paths in anchor_to_notes.items():
        if len(paths) < 2:
            continue
        sorted_paths = sorted(paths, key=lambda p: p.as_posix())
        for i, pa in enumerate(sorted_paths):
            for pb in sorted_paths[i + 1:]:
                pair_key = (pa.as_posix(), pb.as_posix())
                if pair_key in reported_pairs:
                    continue
                # Check if there's a cite edge in either direction.
                if pb in outbound[pa] or pa in outbound[pb]:
                    continue
                reported_pairs.add(pair_key)
                title_a = next(n.title for n in ok_notes if n.path == pa)
                title_b = next(n.title for n in ok_notes if n.path == pb)
                findings.append(
                    Finding(
                        "INFO",
                        "shared-anchor-no-cite",
                        f"{pa.as_posix()} + {pb.as_posix()}",
                        f"`{title_a}` and `{title_b}` share @anchor `{anchor_id}` "
                        f"but are not @cite-linked — consider adding a cross-reference",
                    )
                )

    return findings


def load_vocabulary() -> set[str]:
    """Load the term allowlist from wiki_vocabulary.txt.

    Returns a set of lowercased terms. Missing file returns an empty set
    (the check degrades gracefully rather than erroring).
    """
    if not VOCABULARY_PATH.exists():
        return set()
    terms: set[str] = set()
    for line in VOCABULARY_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        terms.add(stripped.lower())
    return terms


def _strip_anchors_and_cites(lines: list[str]) -> list[str]:
    """Return only prose lines from a claim body, excluding fenced
    ``anchors`` blocks and bare @cite lines.  These regions contain
    structured identifiers that should not be scanned for jargon."""
    result: list[str] = []
    in_fence = False
    for line in lines:
        if FENCE_OPEN_RE.match(line):
            in_fence = True
            continue
        if in_fence:
            if FENCE_CLOSE_RE.match(line):
                in_fence = False
            continue
        if BARE_CITE_RE.match(line):
            continue
        result.append(line)
    return result


def _has_inline_explanation(text: str, term: str, window: int = 80) -> bool:
    """Heuristic: does *term* appear within *window* characters before
    an opening parenthesis that likely contains a definition?

    Examples that pass:
        "SIMD (Single Instruction, Multiple Data)"
        "OCC (optimistic concurrency control)"
    """
    idx = 0
    term_lower = term.lower()
    text_lower = text.lower()
    while True:
        pos = text_lower.find(term_lower, idx)
        if pos == -1:
            return False
        after = text[pos + len(term): pos + len(term) + window]
        # Look for " (" pattern near the term
        paren_pos = after.find("(")
        if paren_pos != -1 and paren_pos < 40:
            return True
        idx = pos + 1


def check_unfounded_terms(notes: list[WikiNote]) -> list[Finding]:
    """INFO-level check: flag technical terms in wiki claim bodies that are
    not (a) in the vocabulary allowlist, (b) matching a wiki entry title,
    or (c) explained inline with a parenthetical definition.

    This is a readability nudge, not a gate. It helps ensure that every
    non-trivial technical term is grounded somewhere a CS-undergrad reader
    can find it.
    """
    findings: list[Finding] = []
    vocab = load_vocabulary()
    if not vocab:
        findings.append(
            Finding(
                "INFO",
                "vocabulary-missing",
                VOCABULARY_PATH.as_posix() if VOCABULARY_PATH.exists() else "scripts/wiki_vocabulary.txt",
                "vocabulary allowlist not found or empty; unfounded-term check skipped",
            )
        )
        return findings

    # Build a set of wiki entry titles (lowercased) for cross-reference
    wiki_titles_lower: set[str] = set()
    for note in notes:
        if note.title:
            wiki_titles_lower.add(note.title.lower())

    ok_notes = [n for n in notes if n.integrity_ok() and n.title]

    for note in ok_notes:
        # Collect all prose lines from claims (excluding anchors/cites)
        prose_lines: list[str] = []
        for claim in note.claims:
            prose_lines.extend(_strip_anchors_and_cites(claim.body_lines))
            # Also include claim title text (after the [Cn] prefix)
            prose_lines.append(claim.title)

        prose_text = "\n".join(prose_lines)

        # Extract candidate terms
        candidates: dict[str, str] = {}  # lowered -> original form

        # 1. ALL-CAPS acronyms (2+ chars)
        for m in ACRONYM_RE.finditer(prose_text):
            raw = m.group(1)
            candidates.setdefault(raw.lower(), raw)

        # 2. CamelCase words
        for m in CAMELCASE_RE.finditer(prose_text):
            raw = m.group(1)
            candidates.setdefault(raw.lower(), raw)

        # 3. Backtick-wrapped terms: only flag CamelCase class/type names.
        #    Backtick formatting already signals "this is code" to the reader,
        #    so snake_case identifiers, function calls, config keys, etc. are
        #    self-grounding. CamelCase terms in backticks are the exception:
        #    they name concepts (classes, protocols) that may need explanation.
        for m in BACKTICK_RE.finditer(prose_text):
            raw = m.group(1).strip()
            # Strip trailing () or (...) for calls like RecordBatch() or DataLoader(shuffle=True)
            name = re.sub(r"\(.*\)$", "", raw)
            # Only interested in CamelCase terms from backtick context
            if not CAMELCASE_RE.match(name):
                # Also check dotted paths for CamelCase final component
                if "." in name:
                    parts = name.split(".")
                    final = parts[-1]
                    if CAMELCASE_RE.match(final):
                        candidates.setdefault(final.lower(), final)
                continue
            candidates.setdefault(name.lower(), name)

        # Check each candidate
        unfounded: list[str] = []
        for term_lower, term_orig in sorted(candidates.items()):
            # (a) In vocabulary allowlist?
            if term_lower in vocab:
                continue

            # (b) Matches a wiki entry title? (case-insensitive substring)
            if any(term_lower in wt for wt in wiki_titles_lower):
                continue

            # Also check if any wiki title is a substring of the term
            if any(wt in term_lower for wt in wiki_titles_lower):
                continue

            # (c) Explained inline with parenthetical definition?
            if _has_inline_explanation(prose_text, term_orig):
                continue

            # Skip schema marker names (@anchor, @cite, etc.)
            if term_orig.startswith("@"):
                continue

            # Skip HTTP header names (e.g. If-Match, If-None-Match)
            if term_orig.startswith("If-"):
                continue

            # Skip very short terms (single char, or 2-char that might be
            # a column name, variable, etc.)
            if len(term_orig) <= 2:
                continue

            unfounded.append(term_orig)

        if unfounded:
            # Group into a single finding per note to avoid noise
            term_list = ", ".join(sorted(unfounded))
            findings.append(
                Finding(
                    "INFO",
                    "unfounded-term",
                    note.path.as_posix(),
                    f"{len(unfounded)} term(s) not in vocabulary allowlist "
                    f"and not matching any wiki entry: {term_list}. "
                    f"Consider adding a wiki entry, an inline explanation, "
                    f"or adding to scripts/wiki_vocabulary.txt if common knowledge.",
                )
            )

    return findings


def check_readwise_backfill(notes: list[WikiNote]) -> list[Finding]:
    """WARN on url: and gist: anchors missing a readwise: field.

    Per protocols/wiki-schema.md § Anchor Evidence Resolution, the readwise:
    field is recommended (not required) on url: and gist: anchors.  Its
    absence means the evidence is harder to retrieve if the URL goes down.
    """
    # Load skip prefixes from file (private repo URLs where git is the evidence)
    skip_prefixes: list[str] = []
    if READWISE_SKIP_FILE.exists():
        for line in READWISE_SKIP_FILE.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                skip_prefixes.append(stripped)
    findings: list[Finding] = []
    ok_notes = [n for n in notes if n.integrity_ok()]
    for note in ok_notes:
        for claim in note.claims:
            for a in claim.anchors:
                atype = a.fields.get("_anchor_type", "")
                aid = a.fields.get("_anchor_id", "")
                if atype in ("url", "gist") and "readwise" not in a.fields and not any(d in aid for d in skip_prefixes):
                    findings.append(
                        Finding(
                            "WARN",
                            "readwise-missing",
                            note.path.as_posix(),
                            f"[C{claim.number}] {atype}: anchor at line {a.line_no} "
                            f"has no `readwise:` field — evidence harder to retrieve "
                            f"if the URL goes down (save to Readwise with tag "
                            f"`anchor-evidence` and backfill the document ID)",
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
    findings.extend(check_graph_topology(notes))
    findings.extend(check_readwise_backfill(notes))
    findings.extend(check_unfounded_terms(notes))
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
