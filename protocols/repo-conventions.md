## Purpose

GitHub-canonical conventions for the `Zettel` repo (the synced `$OV` markdown layer). These rules optimize for: clean GitHub UI rendering, efficient agent navigation, sustainable folder browsing, and a plain-markdown vault that stays ecosystem-agnostic (no editor-specific carry-over).

Companion: `protocols/semantic-vocabulary.md` (backlink and tag conventions).

## Image policy

### Placement

Images live in a sibling `images/` subdir of the markdown that references them:

```
wiki/<Topic>.md
wiki/images/<topic>-overview.png

wip/<slug>.md
wip/images/<slug>-architecture.png

agent-findings/<agent>-<topic>-YYYY-MM-DD.md
agent-findings/images/<topic>-architecture.png
```

For nested tiers, the `images/` is sibling to the .md file at any depth:

```
research/<area>/<Topic>.md
research/<area>/images/<topic>-flow.png
```

Reference syntax (relative path from the .md file's directory):

```markdown
![alt text](images/<topic>-overview.png)
```

### Naming

- **Lowercase kebab-case**: `<topic>-overview.png`, not `Topic_Overview.png` or `TopicOverview.png`.
- **Semantic**: the name describes what the image *shows*, not when it was captured. `<vendor>-cart-checkout.png`, not `Pasted image 20260406173547.png`.
- **Date-leading only when the image is time-bound** (a snapshot of a UI, chart, or receipt at a specific moment): `YYYY-MM-DD-<source>-<artifact>.png`. For evergreen diagrams, omit the date.
- **Avoid hashes, raw timestamps, generic names** (`IMG_7913.PNG`, `image1.png`, `screenshot.png`).
- **Topic prefix when many images share a theme**: `<topic>-overview.png`, `<topic>-flow.png`, `<topic>-internals.png`. Readable at a glance in the directory listing.

### Tracking

`$OV/.gitignore` whitelists `**/images/*.{png,jpg,jpeg,gif,svg,webp}`. Place an image under any `images/` subdir and it auto-tracks on next `git add`.

`assets/` (auto-paste collectors, hash-named imports from prior tools) is re-excluded; any `assets/images/<hash>.png` style import stays local. To promote an `assets/` image to GitHub, move it to the right `<tier>/images/` path with a semantic name and update the markdown reference.

### Legacy image refs

Markdown that still points at `assets/images/<hash>.png` will render broken on GitHub. Acceptable for archive content; for active content, promote on next edit by:
1. `cp assets/images/<hash>.png <tier>/images/<semantic-name>.png`
2. Update the `![](path)` reference in the .md.
3. `git add -A`.

### Examples in this file

All filenames, paths, topics, and people referenced in the example blocks above and the table below are placeholders. Replace `<topic>`, `<vendor>`, `<source>`, `<author>`, `<lab>`, `<venue>` with concrete strings when applying the convention; do not commit those concrete strings into protocol or convention files (they belong inside `$OV/`, which is gitignored).

## Folder size — fission rule

**Magic number: 32 entries (files + subdirectories combined).** When a directory's immediate-child count reaches 32, trigger a fission: split into subdirectories along a natural axis. GitHub's tree view truncates long lists and pagination breaks navigation; most file explorers also slow above that range.

The 32 threshold is hard, not "rough". A directory at 32 should be split before the next addition.

### Per-tier split axes

| Tier | Split axis | Result example |
|------|------------|----------------|
| `daily-notes/` | year, then month (two-level grouping keeps every level under 32; filename carries full ISO date) | `daily-notes/YYYY/MM/YYYY-MM-DD.md` |
| `reflections/` | year-month | `reflections/YYYY-MM/YYYY-MM-DD-reflection.md` |
| `agent-findings/` | year-month | `agent-findings/YYYY-MM/<agent>-<slug>.md` |
| `readwise/articles/` | year-month if dated, else first-letter bucket | `readwise/articles/YYYY-MM/<slug>.md` |
| `readwise/authors/` | first-letter bucket: `A/`, `B/`, …, `0-9/`, `中/` (CJK) | `readwise/authors/<X>/<Author Name>.md` |
| `preprints/<class>/` | venue | `preprints/unofficial-reviews/<venue><yy>/` |
| `wiki/` (and any localized shadow wikis from `[paths.wiki_localized]`) | topic cluster (semantic) | `wiki/data-systems/<Topic Title>.md` |
| `research/<area>/labs/` | by org type or first-letter | `research/<area>/labs/<X>/<lab>/` |
| `people/` | first-letter bucket: `A/`, …, `0-9/`, `中/` (CJK) | `people/<X>/<Person Name>.md` |
| `archive/<subdir>` | first-letter bucket or topical sub-grouping (case-by-case) | `archive/<subdir>/<X>/<Item>.md` |

### Rebuilding refs after any move (canonical workflow)

File moves break standard markdown links `[X](path.md)` and image embeds `![](path)`. The relink contract makes reorganization non-destructive:

```
1. Move files via any tool         (cluster_wiki.py / fission.py / manual mv)
2. uv run scripts/relink.py --apply   ← auto-fixes broken refs
3. Commit
```

`scripts/relink.py` builds a global filename → location index across all tracked `.md`/image files, scans every `[text](path)` and `![alt](path)` reference, and rewrites broken paths to the file's current location. Since refs track filename (not path), any reorganization that doesn't rename files is fully recoverable. Use `--dry-run` first to preview changes.

The wikilink converter (`scripts/wikilink_to_md.py`) handles `[[...]]` → standard markdown link conversion when needed. `relink.py` is the steady-state tool for all path moves once links are standard markdown.

### Tier-specific semantic restructures

`scripts/cluster_wiki.py` is the pattern for one-off semantic reorgs of a single tier: hardcode a `{filename: bucket}` map, move files into bucket subdirs, then run relink. Reusable per-tier — copy + adjust the `TOPIC_MAP`.

### Cascading splits

A subdir created during fission can itself reach 32 over time and require its own fission. The rule applies recursively. Calendar splits (year-month, year-quarter) self-bound: a month never exceeds 31 entries.

## Forward-going naming (general)

- **Filenames**: lowercase kebab-case unless a proper noun or canonical title (e.g., wiki entries can use `Title Case With Spaces.md` because they're canonical names).
- **Dates**: ISO `YYYY-MM-DD` only. No `MM/DD/YYYY`, no `Thu, August 8th, 2024`.
- **Tags**: `#kebab-case-tag`, `#中文标签`. No pure-digit tags.

## Documentation hygiene (present-tense protocols)

Protocols, agent specs, and shared docs describe how the system works **now**. Git is the archive for past states; restating "earlier versions used X, now retired" inside live docs creates lint debt and confuses new readers.

- Write rules in present tense. State what the system does, not what it stopped doing.
- When superseding behavior, delete the old description and its justification rather than narrating the change. The diff plus commit message is the audit trail.
- Genuinely-deferred work belongs in a single named roadmap subsection (the pattern: `wiki-schema.md` → Open v2 Items), not as scattered "v1 only" / "Phase B" parentheticals.
- Operational pointers to runtime artifacts the system still encounters (e.g., "`#ai-reflection` may appear on historical notes; treat as alloy") are fine because they describe runtime conditions, not system biography.

This rule is enforced by `protocols/antipatterns.md` → #10 Legacy framing in living docs, scanned by the Evolver self-check and Reviewer System modes on Tier 2+ changes.

## Lint enforcement (planned)

`scripts/repo_lint.py` (TBD) will check:
- folders exceeding 30 .md files
- images outside `images/` subdirs (under tracked tiers)
- non-semantic image names (timestamps, hashes, "Pasted image…")
- non-ISO date strings in new markdown
