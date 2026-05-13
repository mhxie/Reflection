# Notes Tool — `scripts/notes.py`

> **Status: forward-looking spec.** `scripts/notes.py` is not yet implemented; the `/lint` integration described below activates when the script lands. Until then, this file is the contract a future implementation must satisfy, not a currently-callable tool.

## Purpose

A single CLI for note movement operations on `$OV/`. Solves one problem: moving or renaming a note today forces a manual sweep across every backlinker to fix relative paths. The cost scales with corpus restructure frequency: every tier rename, taxonomy lift, or domain re-org forces the same sweep again.

The vault uses **GitHub-style relative-path markdown links** because notes are browsed on GitHub web, where wikilinks don't render. This tool keeps that format and makes the path-rewrite mechanical.

This protocol is the source of truth for the tool's contract. Implementation will live at `scripts/notes.py`.

## Scope

**In scope.** Note-to-note links inside `$OV/`, in either form:
- `[text](relative/path.md)` — plain
- `[text](<relative/path with spaces.md>)` — angle-bracketed (mandatory when the path contains spaces, parentheses, or other markdown-active chars)
- Optional anchor: `[text](path.md#section)` — anchor preserved on rewrite

**Out of scope.**
- Asset links: `![alt](../assets/foo.bin)`, `![](../assets/img.png)` — assets do not move via this tool. Detected by either `!` image-prefix or path resolving outside `$OV/<note-tier>/`.
- External URLs: `http://`, `https://`, `mailto:` — never rewritten.
- Wikilinks: `[[Title]]` — not used in `$OV/` corpus by policy. Lint flags any introduced.
- URL-encoded internal paths (`%20` for space): not currently in use; tool refuses to introduce them. Use angle brackets instead.
- Cross-vault links into the atelier repo or other repos: not rewritten.
- Drive-side moves: the tool operates on the git working tree. Drive sync is the user's concern; concurrency rule below.

## Operations

```
notes.py mv <src> <dst-dir>/                  # move file, preserve filename
notes.py rename <src> <new-filename>          # rename file in place
notes.py backlinks <file>                     # list files linking to <file>
notes.py check                                # find broken note-to-note links
notes.py index [--rebuild]                    # build/refresh path → backlinks index
```

All operations are **atomic at the git-staging level**: either every edit + the file move land in `git add`, or nothing does. No partial state on the filesystem is acceptable. The tool stages but does not commit; the user reviews the diff and commits.

### `mv <src> <dst-dir>/`

1. Resolve `src` (must exist, must be `.md`, must be inside `$OV`).
2. Compute `dst = <dst-dir>/<basename(src)>`. Refuse if `dst` exists.
3. Find every note linking to `src` (via index, see below).
4. For each backlinker, recompute the relative path from the backlinker's directory to `dst`. Preserve the link's display text and bracket style (plain vs angle).
5. `git mv src dst`. Apply backlink edits. `git add` everything.
6. Report: file moved, N backlinks updated, M files staged.

### `rename <src> <new-filename>`

Same as `mv` but `dst = <dirname(src)>/<new-filename>`. Additionally:
- If the link's display text equals the old filename stem (case-sensitive exact), rewrite display text to the new stem. Otherwise leave display text untouched (it carries human meaning).

### `backlinks <file>`

Read-only. Prints `path:line:col` for each occurrence. Used by humans to inspect blast radius before a move; used by `mv`/`rename` internally.

### `check` (planned `/lint` integration once `scripts/notes.py` ships)

Walks every note-to-note link in `$OV/`. Reports:
- **Broken**: target file does not exist.
- **Wrong-tier**: link from active tier (`wiki/`, `daily-notes/`, etc.) into `archive/` or `cache/`. Warning, not error.
- **Wikilink found**: any `[[X]]` in `$OV/` corpus. Error — corpus policy is markdown-only.

Called by `/lint` as one of its corpus-level passes.

### `index`

Builds a path → backlinks map at `$OV/.notes-index.json` (gitignored — regenerable, not source of truth). Schema:

```json
{
  "built_at": "2026-05-07T...",
  "by_target": {
    "people/<Person Name>.md": [
      {"file": "daily-notes/2025/2025-12/2025-12-24.md", "line": 1, "col": 14, "form": "angle"}
    ]
  }
}
```

Index is **lazy**: any operation that needs it rebuilds if older than `find $OV -name '*.md' -newer .notes-index.json` shows changes.

## Path-resolution rules

Relative paths are resolved from the **directory of the file containing the link**, not from `$OV` root. This is the standard markdown / GitHub behavior.

When rewriting:
- Compute `os.path.relpath(dst, dirname(backlinker))`.
- Use forward slashes always (POSIX), never backslashes, regardless of host OS.
- If `relpath` contains spaces, parentheses, square brackets, or backticks → wrap in angle brackets `(<...>)`. Otherwise plain.
- Never URL-encode. Angle brackets handle every case the corpus needs.

## Encoding and Unicode

Filenames may contain CJK, accented Latin, parentheses, spaces. The tool reads and writes UTF-8, byte-exact. Git's octal-escape display (`\345\215\260\345\272\246`) is presentation only; the tool operates on raw Unicode bytes.

Test fixtures must cover: a CJK-prefixed parenthesized stem, an ASCII stem with a space, and a Unicode stem containing an en-dash. Fixture filenames must be synthetic — never copy stems from `$OV/`.

## Atomicity and failure modes

| Failure | Behavior |
|---|---|
| `dst` exists | Refuse. Print conflict. No filesystem change. |
| Backlink rewrite fails mid-loop (permission, encoding) | Roll back: `git restore --staged --worktree` on every file touched this operation. Original `src` restored. Exit non-zero. |
| `git mv` fails (file not tracked) | Print error, suggest `git add` first. No other change. |
| Index stale during `mv` | Rebuild before computing backlinks. |
| Concurrent Drive sync edit lands during operation | Detected via `git status --porcelain` before/after — if working tree changes between snapshot and apply, abort with "drive sync detected, retry". |

## Display-text policy

Display text is human meaning, not a path artifact. Default: **never rewrite display text**.

Two exceptions:
- `rename`: if display text exactly equals the old filename stem (no extension), rewrite to new stem. This catches `[Old Name](path)` → `[New Name](newpath)` cases.
- Future option `--rewrite-display`: opt-in flag for `mv` if the user wants stem-following behavior across moves too.

`mv` never rewrites display text by default — moving a file does not change its title.

## Integration points

- `/lint` will call `notes.py check` (once implemented) and surface broken links + wikilink violations as a corpus-level pass.
- The orchestrator does NOT call `mv` or `rename` autonomously. These are user-initiated. Agents may *suggest* moves (Forgetter, Curator) but execution is user-approved.
- `scripts/semantic.py` is unaffected — it operates on file content, not paths. Index drift from a move is corrected on next semantic-index rebuild.
- `scripts/people.py` resolution by name continues to work — name-to-path lookup is filename-stem based, not link-based.

## What this tool does NOT do

- Promote / demote between L-tiers. That's user judgment + `/promote`.
- Resolve title collisions. That's user cleanup, optionally Forgetter-assisted.
- Rewrite asset paths on note moves. Asset references stay; user manages assets separately.
- Touch the atelier repo. This is a `$OV/`-only tool.
- Mutate without staging. Always stages, never commits.

## Cross-references

- [[local-first-architecture.md]] — `$OV/` tier model
- [[raw-indexing.md]] — wikilink-style indexes (separate convention; this tool does not produce them)
- [[drive-zk-ingestion.md]] — file movement during ingestion uses `mv`-default rules; this tool inherits the same atomicity contract
- `scripts/lint.py` — corpus-level lint; will call `notes.py check` once the implementation lands
