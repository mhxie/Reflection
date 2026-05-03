#!/usr/bin/env python3
"""
privacy_check.py: Detect private-vault identifier leaks in committed files.

Two automated discovery sources, no manual denylist needed:

  1. Filename stems: multi-word `*.md` stems under PRIVATE_DIRS in `$OV/`.
  2. Wiki-link targets: `[[...]]` references extracted from vault content.
     Catches person names, private note titles, and concepts that may not
     have their own files. Filtered to multi-word ASCII targets and any
     non-ASCII targets to avoid false positives on system vocabulary.

Auto-skip rules (all fully automated):
  - Single ASCII words from wiki-links (too generic: Reflect, Protocol).
  - Terms matching committed file stems (if `frameworks/foo-bar.md` is
    tracked, "Foo Bar" is intentionally public).
  - File paths (contain `/`), dates, noise patterns.
  - Explicit opt-out via `privacy_allowlist.txt` for edge cases.

CLI:
    uv run scripts/privacy_check.py                   human report
    uv run scripts/privacy_check.py --json            machine-readable output
    uv run scripts/privacy_check.py --allow-empty-ov  exit 0 when $OV is unset

Exit code: 0 if no hits, 1 if any hit (treat as ERROR), 2 on IO error or
when the gate cannot meaningfully run (missing/empty $OV without
--allow-empty-ov).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

OV = Path(os.environ.get("OV", "zk"))
ALLOWLIST = Path(__file__).resolve().parent / "privacy_allowlist.txt"
PRIVATE_SLUGS = (
    Path(__file__).resolve().parent.parent / "personal" / "private_slugs.txt"
)

_INFRA_DIRS = {"cache", "assets", ".obsidian"}


def _discover_private_dirs(root: Path) -> list[str]:
    """Auto-discover content subdirectories under $OV/.

    Skips infrastructure dirs (cache mirrors, binary assets, editor
    config) that don't contain user-authored private identifiers.
    """
    if not root.is_dir():
        return []
    return [
        p.name for p in sorted(root.iterdir())
        if p.is_dir() and p.name not in _INFRA_DIRS and not p.name.startswith(".")
    ]

SKIP_STEMS = {"index", "README", "Note Title"}

_WIKILINK_RE = re.compile(r'(?<!\!)\[\[([^\]]+)\]\]')
_DATE_RE = re.compile(r'^\d{4}(-\d{2}(-\d{2})?)?$')
_NOISE_RE = re.compile(r'^[.\s]+$')
_NUMERIC_RE = re.compile(r'^[\d\s,.\-]+$')


def load_allowlist() -> set[str]:
    if not ALLOWLIST.exists():
        return set()
    out: set[str] = set()
    for line in ALLOWLIST.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.add(s)
    return out


def load_private_slugs() -> set[str]:
    """Load single-word private slugs (employer names, codenames) from a
    gitignored sidecar list.

    The multi-word filename-stem and wikilink heuristics deliberately skip
    single ASCII words to avoid flagging system vocabulary (e.g., "Reflect",
    "Protocol"). That floor lets through employer slugs and project
    codenames that happen to be one word. The user maintains this list
    explicitly because no heuristic can reliably tell a generic word from
    a private proper noun. File is gitignored under `personal/`; absent
    file means no slugs configured.
    """
    if not PRIVATE_SLUGS.exists():
        return set()
    out: set[str] = set()
    for line in PRIVATE_SLUGS.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.add(s.lower())
    return out


def collect_titles(root: Path, allowlist: set[str], dirs: list[str]) -> list[str]:
    titles: set[str] = set()
    for sub in dirs:
        p = root / sub
        if not p.exists():
            continue
        for f in p.rglob("*.md"):
            stem = f.stem
            if stem in SKIP_STEMS or len(stem.split()) < 2:
                continue
            if stem in allowlist:
                continue
            titles.add(stem)
    return sorted(titles)


def _is_private_wikilink(target: str) -> bool:
    """Heuristic: is this wiki-link target likely a private identifier?

    Accepts multi-word targets (person names, note titles) and non-ASCII
    targets with enough specificity (3+ chars). Rejects single ASCII
    words, file paths, dates, noise, and short generic CJK terms.
    """
    if len(target) < 2:
        return False
    if '/' in target or target.endswith('.md'):
        return False
    if _DATE_RE.match(target) or _NOISE_RE.match(target):
        return False
    if _NUMERIC_RE.match(target):
        return False
    has_non_ascii = any(ord(c) > 127 for c in target)
    if has_non_ascii:
        non_ascii_count = sum(1 for c in target if ord(c) > 127)
        return non_ascii_count >= 3
    return len(target.split()) >= 2


def collect_wikilinks(root: Path, allowlist: set[str], dirs: list[str]) -> set[str]:
    """Extract [[wiki-link]] targets from vault files as private terms.

    Catches people names, note references, and concepts that may not
    have their own files but still appear as identifiers in the vault.
    Filters to multi-word ASCII targets and any non-ASCII targets to
    avoid false positives on single-word system terms.
    """
    targets: set[str] = set()
    for sub in dirs:
        p = root / sub
        if not p.is_dir():
            continue
        for f in p.rglob("*.md"):
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for m in _WIKILINK_RE.finditer(text):
                target = m.group(1).split("|")[0].strip()
                if target in SKIP_STEMS or target in allowlist:
                    continue
                if _is_private_wikilink(target):
                    targets.add(target)
    return targets


def tracked_files() -> list[str]:
    """Files tracked by git PLUS untracked-but-not-ignored files.

    The privacy gate cares about content about to enter the repo, not just
    content already in HEAD. A brand-new file (e.g., a fresh command under
    .claude/commands/) must be scanned before it is staged, otherwise the
    gate has a trivial bypass: add a leak in a new file and it is invisible
    to `git ls-files`.
    """
    out: set[str] = set()
    for cmd in (
        ["git", "ls-files"],
        ["git", "ls-files", "-o", "--exclude-standard"],
    ):
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            sys.stderr.write(
                f"privacy_check: `{' '.join(cmd)}` failed: {res.stderr}\n"
            )
            sys.exit(2)
        for line in res.stdout.splitlines():
            if line.strip():
                out.add(line)
    return sorted(out)


def committed_stems(files: list[str]) -> set[str]:
    """Derive normalized stems from tracked .md files.

    If `frameworks/immunity-to-change.md` is committed, then
    "immunity to change" is intentionally public and should not
    be flagged when it also appears as a vault wiki-link target.
    """
    stems: set[str] = set()
    for f in files:
        p = Path(f)
        if p.suffix != ".md":
            continue
        raw = p.stem.replace("-", " ").replace("_", " ")
        stems.add(raw.lower())
    return stems


def scan(terms: list[str], files: list[str]) -> list[dict]:
    hits: list[dict] = []
    for f in files:
        try:
            content = Path(f).read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        lines: list[str] | None = None
        for t in terms:
            if t not in content:
                continue
            if lines is None:
                lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                if t in line:
                    hits.append({
                        "file": f,
                        "line": i,
                        "private_title": t,
                    })
                    break
    return hits


def scan_slugs(slugs: set[str], files: list[str]) -> list[dict]:
    """Scan files for single-word private slugs.

    Case-insensitive, word-boundary aware (\\b<slug>\\b) so a slug "foo"
    matches "Foo" and "foo's" but not "foobar" or "tofoo". Private slugs
    are typically employer names or codenames that need this stricter
    boundary check; the multi-word `scan` uses substring match because
    multi-word phrases rarely appear inside other words.
    """
    if not slugs:
        return []
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(s) for s in sorted(slugs)) + r")\b",
        re.IGNORECASE,
    )
    hits: list[dict] = []
    for f in files:
        try:
            content = Path(f).read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        seen_in_file: set[str] = set()
        for i, line in enumerate(content.splitlines(), 1):
            for m in pattern.finditer(line):
                slug = m.group(1).lower()
                if slug in seen_in_file:
                    continue
                seen_in_file.add(slug)
                hits.append({
                    "file": f,
                    "line": i,
                    "private_title": slug,
                })
    return hits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="scripts/privacy_check.py",
        description=(
            "Scan tracked files for private-vault filename leaks. Fails "
            "with exit 1 if any multi-word private filename stem appears "
            "as a literal substring in a committed file."
        ),
    )
    ap.add_argument("--json", action="store_true", help="Emit JSON output.")
    ap.add_argument(
        "--allow-empty-ov",
        action="store_true",
        help=(
            "Exit 0 when the gate would scan vacuously: either $OV is "
            "missing, OR $OV exists but has no private dirs and no "
            "private_slugs.txt. Without this flag, both cases exit 2 "
            "to avoid a placebo green light for fresh clones."
        ),
    )
    args = ap.parse_args(argv)

    if not OV.exists():
        msg = (
            f"privacy_check: {OV} does not exist; cannot scan. "
            "Set $OV or pass --allow-empty-ov to acknowledge an empty gate."
        )
        if args.json:
            print(json.dumps(
                {"zk_missing": True, "titles_scanned": 0, "hits": []},
                indent=2,
            ))
        else:
            sys.stderr.write(msg + "\n")
        return 0 if args.allow_empty_ov else 2

    allowlist = load_allowlist()
    private_slugs = load_private_slugs()
    dirs = _discover_private_dirs(OV)
    if not dirs and not private_slugs and not args.allow_empty_ov:
        msg = (
            f"privacy_check: $OV={OV} contains no private dirs and no "
            "private_slugs.txt is configured; gate would pass vacuously. "
            "Pass --allow-empty-ov to acknowledge."
        )
        if args.json:
            print(json.dumps(
                {
                    "vacuous_gate": True,
                    "ov_dir": OV.as_posix(),
                    "titles_scanned": 0,
                    "hits": [],
                },
                indent=2,
            ))
        else:
            sys.stderr.write(msg + "\n")
        return 2
    titles = collect_titles(OV, allowlist, dirs)
    files = tracked_files()
    repo_stems = committed_stems(files)
    wikilinks = collect_wikilinks(OV, allowlist, dirs)

    def _matches_committed(term: str) -> bool:
        tl = term.lower()
        return any(tl.startswith(s) or s.startswith(tl) for s in repo_stems)

    titles = [t for t in titles if not _matches_committed(t)]
    wikilinks -= {t for t in wikilinks if _matches_committed(t)}
    all_terms = sorted(set(titles) | wikilinks)
    hits = scan(all_terms, files) if all_terms else []
    hits.extend(scan_slugs(private_slugs, files))

    if args.json:
        print(json.dumps({
            "ov_dir": OV.as_posix(),
            "filename_stems": len(titles),
            "wikilink_targets": len(wikilinks),
            "private_slugs": len(private_slugs),
            "terms_scanned": len(all_terms) + len(private_slugs),
            "allowlist_size": len(allowlist),
            "hit_count": len(hits),
            "hits": hits,
        }, indent=2))
    else:
        if not hits:
            print(
                f"privacy_check: clean ({len(all_terms) + len(private_slugs)} "
                f"private terms scanned: {len(titles)} filename stems + "
                f"{len(wikilinks)} wikilink targets + "
                f"{len(private_slugs)} private slugs, 0 leaks)"
            )
            return 0
        files_hit = sorted({h["file"] for h in hits})
        print(
            f"privacy_check: {len(hits)} leak(s) across "
            f"{len(files_hit)} file(s)"
        )
        for h in hits:
            print(f"  {h['file']}:{h['line']}: {h['private_title']!r}")
        print()
        print(
            "Each line shows a private identifier from your $OV vault "
            "(filename stem or [[wikilink]] target) appearing in a tracked "
            "file. Replace with a generic placeholder, or add the term to "
            "scripts/privacy_allowlist.txt if the exposure is deliberate."
        )

    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
