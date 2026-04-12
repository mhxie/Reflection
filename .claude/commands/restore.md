# /restore — Emergency recovery of wiki entries from Reflect

**Very rarely triggered.** This command exists for a single failure mode: an AI-driven operation (or a finger slip) deleted or corrupted one or more wiki entries under `zk/wiki/` locally, and the only surviving snapshot is the copy that was pushed to Reflect via a prior `/sync`. For ordinary file churn, use `git`.

**Do not run this command reflexively.** It is not a sync verifier, not a daily check, not a health probe. The normal path when something looks wrong is `/lint` + `git status` + `git log`. `/restore` is the last resort after all of those.

## The lossy-pipeline caveat — read before proceeding

`/sync` is lossy for wiki entries by design:

1. `scripts/sync_export.py` strips the fenced ` ```anchors ``` ` blocks (the machine-readable `@anchor`/`@cite`/`@pass` markers that `scripts/trust.py` scores on) and replaces them with a human-readable `**Sources:**` bullet list.
2. Reflect mutates the body on ingestion: auto-prepends an H1, wraps bare URLs in `<...>`, normalizes `---` to `***`.

**What comes back from Reflect is degraded prose, not a drop-in replacement** for the original `zk/wiki/<slug>.md`. Byte-copying the Reflect body into place will fail `trust.py`'s structural-integrity check (missing `anchors` fences, items 5/6/7 of `protocols/wiki-schema.md`), and `/sync` will be blocked until the file is re-authored.

The user is expected to read the recovered prose, reconstruct the `anchors` fences from the `**Sources:**` bullets, and hand-author the final wiki entry. This is a reconstruction workflow, not an automated restore.

## Process

### Phase 1: Confirm intent

Before touching anything, ask the user:

> "/restore is the last-resort recovery path for wiki entries that exist in the sync manifest but are missing locally. It pulls the (lossy) Reflect copy into `zk/cache/restore-<slug>.md` as a reference for hand-reconstruction. It will NOT write to `zk/wiki/`. Do you want to proceed? [y/N]"

If the user hesitates, stop. Suggest `git status` / `git log -- zk/wiki/` / `/lint` first.

### Phase 2: Diagnose

```
Bash: scripts/restore.py diagnose
```

Parse the JSON `plan`. If `missing_count == 0`, stop and report:

> "Nothing to restore: every slug in the manifest has a local file. If a wiki entry looks wrong but is still on disk, use `git` to inspect history, not `/restore`."

If `missing_count > 0`, present the list of missing slugs with their `reflect_note_id` and `synced_at` dates. Ask the user to confirm which slugs to recover — recovery is per-slug, not batch.

### Phase 3: Fetch from Reflect

For each confirmed slug:

1. Call `get_note(id: <reflect_note_id>)` via the Reflect MCP. This is an **orchestrator-only** MCP escape hatch (already documented in CLAUDE.md as one of the three narrow allowed reads).
2. If the note is missing or the body is empty, report the failure and skip. The user deleted the Reflect copy by hand, or `/sync` never actually pushed this slug.
3. Write the body to `zk/cache/restore-<slug>.md` with a prepended header:

   ```
   # RECOVERY SNAPSHOT — not a valid wiki entry

   Source: Reflect note <reflect_note_id>
   Synced at (per manifest): <synced_at>
   Fetched at: <today>

   This file is degraded prose fetched from Reflect's append-only archive.
   It is NOT a drop-in replacement for zk/wiki/<slug>.md because:
     - The `anchors` fences were stripped on /sync (sync_export.py:strip_body)
     - Reflect auto-mutated URLs, H1, and horizontal rules on ingestion

   To recover the wiki entry:
     1. Read the prose below
     2. Hand-author zk/wiki/<slug>.md with proper H1, `## Claims` sections,
        `### [Cn]` headings, and `anchors` fences reconstructed from the
        `**Sources:**` bullets below
     3. Run `scripts/trust.py --note zk/wiki/<slug>.md` and `scripts/lint.py`
        to confirm the rebuilt entry parses cleanly

   ---

   <original reflect body>
   ```

4. Never write directly to `zk/wiki/<slug>.md`. The cache file is a reference, not a restore.

### Phase 4: Report

Tell the user which cache files were written and what to do next:

> "Wrote `zk/cache/restore-<slug>.md` for N slugs. These are prose references, not valid wiki entries. Open each, reconstruct the `anchors` fences by hand from the `**Sources:**` bullets, and save the result to `zk/wiki/<slug>.md`. Then run `scripts/trust.py` and `scripts/lint.py` to verify before `/sync`."

## Rules

1. **One-way.** `/restore` reads from Reflect, writes only to `zk/cache/`. It never writes to `zk/wiki/` and never updates the manifest.
2. **Per-slug confirmation.** Never batch-restore without explicit per-slug approval. Recovery is a reconstruction task, not an import.
3. **Prose is not schema.** What comes back is lossy. The user must re-author the `anchors` fences by hand. This is the whole point of the workflow and is documented in the cache file header.
4. **Covers only `zk/wiki/`.** `/sync` only pushes wiki entries, so `/restore` only recovers wiki entries. L2 content (`zk/reflections/`, `zk/research/`, `zk/drafts/`, `zk/gtd/`, `zk/agent-findings/`, `zk/preprints/`) never crossed the sync boundary and has no Reflect copy to restore from. For that, use `git`.
5. **Daily notes are out of scope.** Daily notes flow Reflect → local continuously as the primary capture path. If a local `zk/daily-notes/<date>.md` is lost, rerun the Obsidian/Reflect sync that populates the mirror, not `/restore`.

## When this has fired historically

Never, as of 2026-04-07. The command exists as a standing insurance policy against a failure mode the append-only architecture was designed to recover from. If you find yourself running this for the first time, file a note in `zk/reflections/` about what caused the loss so the system can evolve.
