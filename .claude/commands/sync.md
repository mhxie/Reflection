# /sync — Push `zk/wiki/` entries to Reflect for mobile display

One-way sync from the local wiki layer to Reflect. Wiki entries live under `zk/wiki/*.md` and are the authoritative L4 knowledge layer (see `protocols/local-first-architecture.md`). Reflect is a display surface for mobile reading — not a source of truth and not pulled back.

**Scope:** only `zk/wiki/*.md`. Daily notes, reflections, drafts, and everything else in `zk/` do not sync. `/sync` does not pull edits from Reflect back into the vault.

## What to sync

| Source | Target in Reflect | Title |
|---|---|---|
| `zk/wiki/<slug>.md` | standalone note via `create_note` | H1 of the wiki file |

## Process

### Phase 1: Preflight

1. Check that `.mcp.json` is configured and the Reflect MCP is reachable. If not, stop cleanly: "Reflect MCP not reachable. Skipping sync. Nothing is lost — wiki entries are authoritative on disk."
2. Read the sync manifest at `zk/.sync-manifest.json` (gitignored). If it doesn't exist, treat every wiki entry as new.
   ```json
   {
     "schema": 1,
     "entries": {
       "<slug>": {
         "reflect_note_id": "<id returned by create_note>",
         "synced_at": "YYYY-MM-DD",
         "content_sha256": "<hash of stripped body at last sync>"
       }
     }
   }
   ```
3. Run `Bash: scripts/sync_export.py manifest zk/wiki/ --synced-at <today>` to get the list of wiki entries with deterministic sha256 hashes and titles. **The LLM must never compute hashes or strip markdown itself** — `sync_export.py` is the single source of truth for the stripped body and its hash (Gemini flagged LLM non-determinism here as a blocker). For each entry in the JSON output, compare `sha256` with `entries[slug].content_sha256` in the manifest.
4. Categorize:
   - **new** — slug not in manifest
   - **changed** — slug in manifest, hash differs
   - **unchanged** — slug in manifest, hash matches → skip
5. Run `Bash: scripts/trust.py --json` and filter entries where `integrity_ok: false` (or with non-empty `parse_errors`). Do not sync failing entries; warn the user.
6. Run `Bash: scripts/lint.py --json` as a corpus-level preflight. Parse the JSON and split ERROR findings by code:
   - **`parse-error`** — ignore here; step 5 already handles per-note parse failures by skipping the broken note and syncing the rest. Blocking the whole sync on one bad note would regress that behavior.
   - **`duplicate-title`, `manifest-unreadable`, `manifest-malformed`** (and any other ERROR code that is not `parse-error`) — **stop the sync** and surface them verbatim. These are corpus-level failures that silently corrupt the manifest or the trust graph if pushed.
   - **WARN and INFO findings** — advisory only. Show a one-line summary and continue. For a full breakdown and remediation, tell the user to run `/lint` directly.

### Phase 2: Obtain the stripped body (deterministic)

Do not strip markdown in the LLM. Instead call:

```
Bash: scripts/sync_export.py body zk/wiki/<slug>.md --synced-at <today>
```

`sync_export.py` does the following deterministically, and the LLM never re-derives it:

1. **Strips the leading H1.** Reflect auto-prepends the note subject as an H1 on ingestion, so leaving our own produces a duplicate title. The script drops the first `# ` line (and any blank lines immediately after it).
2. Keeps: intro prose, `## Claims` heading, each `### [Cn]` heading and its prose body, `## Revision Log`, `## Notes for ...` sections.
3. For each claim, collects its `@anchor`, `@cite`, and `@pass` lines from the fenced `anchors` block (using the same positional scoping as `scripts/trust.py` — each fenced block belongs to the most recent `### [Cn]` heading) and renders them under the claim as a human-readable `**Sources:**` bullet list. The raw marker format `@anchor: arxiv:2501.13956 | valid_at: 2026-04-06` is prettified to `arxiv:2501.13956 (valid from 2026-04-06)`; bi-temporal markers with both `valid_at` and `invalid_at` render as `(valid YYYY-MM-DD — YYYY-MM-DD)`.
4. Drops the fenced ` ```anchors ` blocks entirely.
5. Appends a top-level "Synced from ... Local is authoritative" footer.

**Known Reflect ingestion mutations** (cosmetic, do not affect trust or searchability): Reflect wraps bare URLs in `<...>` angle brackets, normalizes `---` horizontal rules to `***`, and auto-prepends the subject as an H1 (the reason step 1 exists). These are why the new-entry verify step checks `body non-empty`, not byte-exact match — byte-exact comparison would always fail.

The output of `sync_export.py body` is the exact byte stream whose sha256 was computed in Phase 1 and is what you pass to `create_note` in Phase 3. Capture it to a temporary file under `zk/cache/sync-<slug>.md` so the LLM can feed it into the MCP call without re-encoding.

### Phase 3: Write to Reflect

For each **new** entry:
1. `create_note(subject: "<H1 title>", contentMarkdown: "<stripped body>")`
2. **Verify:** immediately `get_note(id)` and confirm the body is non-empty. If empty, the parameter name was wrong — stop and report. This is the silent-empty-note failure mode CLAUDE.md warns about.
3. Record in manifest under the slug: `reflect_note_id`, `synced_at`, `content_sha256`.

For each **changed** entry:

Reflect MCP has no update API. The user is expected to have deleted the old Reflect note by hand before re-running `/sync`. `create_note` with an existing title returns the existing note unchanged (same ID); with no existing title it creates a fresh note (new ID). The **returned note ID** is the recovery signal — not the body (Reflect mutates bodies on ingestion: auto-prepends an H1, wraps URLs in `<...>`, normalizes `---` to `***`, etc., so byte-exact body comparison would always fail).

1. Call `create_note(subject: "<H1 title>", contentMarkdown: "<stripped body>")`.
2. Compare the returned `id` with `entries[slug].reflect_note_id` in the manifest:
   - **New ID (different from manifest):** the user successfully deleted the old note; `create_note` created a fresh one. Run the empty-body check via `get_note(new_id)` (silent-empty-note guard) and if the body is non-empty, **update the manifest** with the new `reflect_note_id`, `synced_at`, and `content_sha256`. Treat as success.
   - **Same ID as manifest (stale stub):** the user forgot to delete the old Reflect note, so `create_note` returned the existing stub unchanged. Skip this entry, do **not** update the manifest hash, and report:
     > "<slug> has local edits but the old Reflect note (`<id>`) is still present. Delete it by hand in Reflect and re-run `/sync`."
   - **Empty body on the new-ID path:** the parameter name was wrong — stop and report (same silent-empty-note check as the new-entry path).

### Phase 4: Report

Present a summary:
```
/sync summary
  New entries synced:    N
  Unchanged (skipped):   M
  Changed (needs manual replace): K — [list slugs]
  Failing trust parse (skipped):  F — [list slugs with errors]
  Reflect MCP reachable:  yes/no
```

## Error handling

- **Reflect MCP down:** exit cleanly in Phase 1. No partial writes, no manifest mutation.
- **`create_note` empty-body detected:** stop the loop, do not update the manifest, report the slug that failed.
- **Title collision (existing Reflect note with same title but no manifest entry):** `create_note` returns the existing note. You cannot tell from the body alone whether it's a benign prior sync (idempotent re-adoption) or a conflicting note the user wrote by hand, because Reflect mutates bodies on ingestion. Record the returned ID in the manifest alongside the current stripped-body hash and warn the user: "<slug> collided with an existing Reflect note (`<id>`); adopted it into the manifest. If this is not the copy you expected, delete it by hand in Reflect and re-run `/sync`."
- **Structural-integrity failure:** already filtered in Phase 1. Print the file path and parse errors so the user can fix the source.
- **`scripts/trust.py` missing or errors:** skip the trust filter but still perform the sync. Warn: "Trust engine unavailable — syncing without parse verification."

## Idempotency

Re-running `/sync` with no changes must be a no-op. The manifest is the idempotency ledger. Deleting the manifest forces a full re-sync attempt (which will hit title collisions on everything already in Reflect — use the collision path to reconcile).

## Rules

1. **One-way.** Never read from Reflect to update `zk/wiki/`. Manual edits in Reflect are lost on the next `/sync` of a changed entry.
2. **Markers are for the trust engine, not for humans.** The Sources footer is the human-readable rendering; the markers stay only in the local file.
3. **Manifest is gitignored.** Add `zk/.sync-manifest.json` to `.gitignore` if it isn't already.
4. **Ask before destructive action.** If a collision requires asking the user to delete a Reflect note by hand, stop and tell them — don't guess.
