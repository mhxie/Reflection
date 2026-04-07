# Wiki Schema

The structural format for a note that lives under `zk/wiki/`. Location is the certification: a note is a wiki entry by virtue of being in `zk/wiki/`, not by carrying any tag. Wiki entries are parseable by `scripts/trust.py` and have claim-level granularity in the trust graph. Notes outside `zk/wiki/` are alloy by default (see `epistemic-hygiene.md`).

## Why Location, Not Tag

Earlier drafts of this design used a `#compiled-truth` tag to mark notes that followed the schema. The tag is dropped. `zk/` is a real Obsidian vault with hundreds of pre-existing notes; carving out a structural sub-tier by tag inside that vault would conflict with the user's existing tagging conventions and force the trust engine to filter every note in the vault. A dedicated subdirectory is cleaner: `zk/wiki/` is the trust-engine-visible region; everything else in `zk/` is alloy. The trust engine walks one directory; the user has free use of every other tag.

The `#solo-flight` tag survives this rename — it lives orthogonally to the schema and marks unstructured pure-human capture, which is location-independent (see `epistemic-hygiene.md`).

## Session-Visible Markers

Because wiki entries live under `zk/wiki/` and nothing outside that directory participates in the trust graph, a reader scanning a session (the orchestrator, a subagent, or the user skimming chat) has no visible cue that a referenced file is wiki-grade. The file-path prefix `zk/wiki/` is the cue. When agents cite a wiki entry in session output, they cite by path (`zk/wiki/<title>.md`), not by bare note title, so the certification is legible inline. Reflect-only notes continue to be cited as `[[Note Title]]`. A `[[Note Title]]` reference in any session output is alloy by default; a `zk/wiki/...` path reference is wiki-grade. Mixing the two forms in one citation (e.g., `[[zk/wiki/foo]]`) is a schema violation the Reviewer flags.

## Why Claim-Level

Most PKM trust systems assign trust to whole notes. A note like that can contain one well-anchored claim and five confabulated ones, and the whole note inherits the same score. RAGAS faithfulness work shows that atomic-claim granularity is materially more reliable. Graphiti's bi-temporal edge model is the production analog.

reflectl's wiki entries are structured around claims, not paragraphs. Each claim has its own anchor set and its own trust score. Note-level aggregation is a derived view, not the primary unit.

## Note Structure

A wiki entry has three required sections and lives in `zk/wiki/` (see `local-first-architecture.md` for the layer model).

```markdown
# Note Title

## Summary

One- to three-paragraph synthesis. Prose. No anchors here — the synthesis is alloy on top of the claims and is not separately scored.

## Claims

### [C1] One-sentence claim text

Optional body paragraph(s) elaborating the claim. Verbatim quotes from anchors should appear here, attributed.

```anchors
@anchor: s2:gyongyi-vldb-2004 | valid_at: 2026-04-06
@cite: [[PageRank fundamentals]] | valid_at: 2026-04-06
@pass: reviewer | status: verified | at: 2026-04-06
```

### [C2] One-sentence claim text

Body.

```anchors
@anchor: arxiv:2501.13956 | valid_at: 2026-04-06
@anchor: url:https://github.com/getzep/graphiti | valid_at: 2026-04-06
```

## Revision Log

- 2026-04-06: Initial draft. Claims [C1], [C2] anchored from scout brief sources.
- 2026-04-12: [C2] anchor `arxiv:2501.13956` invalidated — paper retracted. See @cite [[Graphiti retraction note]].
```

The `# Title`, `## Summary`, `## Claims`, and `## Revision Log` headings are required. Topic tags (regular Obsidian-style hashtags) are allowed but not required and play no role in the trust engine.

## The Marker Vocabulary

Markers live inside fenced code blocks with the language label `anchors`, one marker per line, pipe-separated key-value pairs. The fenced format is non-negotiable because `scripts/trust.py` parses by fence label, not by inference.

### `@anchor`

An external source. This is a **seed** in the trust graph: only `@anchor` markers contribute initial trust mass to the personalized PageRank.

```
@anchor: <type>:<id> | valid_at: <YYYY-MM-DD> [| invalid_at: <YYYY-MM-DD>] [| weight: <float>]
```

Anchor types and id formats:

| Type | ID format | Example |
|---|---|---|
| `s2` | Semantic Scholar paper ID | `@anchor: s2:649def34f8be52c8b66281af98ae884c09aef38b` |
| `arxiv` | arXiv ID | `@anchor: arxiv:2501.13956` |
| `doi` | DOI | `@anchor: doi:10.14778/3402707.3402711` |
| `isbn` | ISBN-13 | `@anchor: isbn:9780262035613` |
| `url` | full URL | `@anchor: url:https://maggieappleton.com/ai-dark-forest` |
| `gist` | GitHub gist URL | `@anchor: gist:https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f` |

**URL escaping rule.** Marker fields are pipe-separated, so URLs (in `url` and `gist` anchors and in `ref:` fields) must not contain literal pipe characters. If a URL contains `|`, encode it as `%7C` before storing it in the marker. The parser will not try to be clever about pipe placement; it splits on the first occurrence of ` | ` (space-pipe-space) per line, then on `:` for each field's key. Multi-line values are not supported; each marker is exactly one line.

`weight` is optional and defaults to `1.0`. For papers, weight may be set to `s2.influentialCitationCount`-derived values or OpenAlex FWCI when the user wants to bias trust toward higher-quality anchors. v1 trust engine treats all weights as `1.0` unless explicitly set; weighted seeding is a Phase B optional feature.

### `@cite`

An internal pointer to another wiki entry. This is an **edge** in the trust graph: it propagates trust from the cited note's claims to this claim. `@cite` markers do not contribute initial mass.

```
@cite: [[Note Title]] [#Cn] | valid_at: <YYYY-MM-DD> [| invalid_at: <YYYY-MM-DD>]
```

The optional `#Cn` suffix lets a citation point at a specific claim within the cited note (e.g., `[[TrustRank fundamentals]]#C2`). Without the suffix, the citation points at the note as a whole and uses the note-level aggregate score as the upstream signal.

`@cite` markers must resolve. A `@cite` to a note that does not exist in `zk/wiki/`, or a `@cite` with a `#Cn` suffix to a non-existent claim, is a **dangling internal cite** — caught by structural-integrity check, fails the floor.

### `@pass`

A record of an internal agent pass: Reviewer, Challenger, Thinker, or other team agents. **`@pass` markers never accumulate trust.** They serve two purposes:

1. **Audit trail.** They show what scrutiny the claim has survived.
2. **Floor trust eligibility.** A wiki entry that has at least one `@pass: reviewer | status: verified` and passes structural integrity becomes eligible for the claim-level floor trust of 0.1 on its unanchored claims.

```
@pass: <agent> | status: <verified|flagged|inconclusive> | at: <YYYY-MM-DD> [| ref: <session-id-or-note>]
```

`<agent>` is one of: `reviewer`, `challenger`, `thinker`, `scout`, `curator`. The optional `ref` field points at the session reflection or another note where the pass was recorded, for audit.

## Bi-temporal Anchors

Every marker carries `valid_at`, the date the marker was added. Markers can later be invalidated by adding `invalid_at`. The original line is **never deleted**; the invalidation is an additive change. This preserves the answer to "what did the system believe at time T?"

Example evolution:

```
@anchor: arxiv:2501.13956 | valid_at: 2026-04-06
```

Later, after the paper is retracted:

```
@anchor: arxiv:2501.13956 | valid_at: 2026-04-06 | invalid_at: 2026-04-12
```

The `Revision Log` section at the bottom of the note records the change in human-readable form, with a `@cite` to the note that explains the invalidation if there is one.

`scripts/trust.py` filters markers by `invalid_at` when computing current trust: a marker with `invalid_at <= today` is excluded from the graph. The original record is preserved on disk forever. This is the Graphiti-style append-only-but-mutable contract.

The temporal decay function (β = 0.9 per month from Temporal PageRank, Rozenshtein & Gionis 2016) is **deferred to v2**. v1 treats all valid markers as equal weight regardless of age.

## The Trust Propagation Rule

This is the rule that makes the design work. State it bluntly so it never drifts.

> **External anchors are the only seeds of trust. Internal `@cite` edges propagate trust. Internal `@pass` markers never accumulate trust — only floor it.**

In TrustRank terms: `personalization` is the dict of anchor-bearing claim nodes. Non-anchored claims get `0` initial mass. Personalized PageRank then propagates that mass through `@cite` edges. The damping factor (typically `0.85`) handles cycles natively.

`@pass` markers do not become nodes in the graph. They are metadata on existing claim nodes. Their only effect is gating the structural-integrity check that gates the claim-level floor.

This rule is the structural answer to Karpathy's failure mode (`epistemic-hygiene.md` → "Karpathy's failure mode"). Internal agent re-review, no matter how thorough, can never make a claim more trusted than its anchors warrant. It can only hold the line.

## Claim-Level Floor Trust

Once the personalized PageRank has run, apply the floor. **For this check, "passes structural integrity" means items 1-10 of the structural-integrity check below pass.** Item 11 (the `@pass: reviewer | status: verified` requirement) is the second condition in the pseudocode and is not folded into "structural integrity" itself.

```
for each claim Ci in note N:
    if N lives under zk/wiki/
       and N passes structural integrity (items 1-10)
       and N has at least one @pass: reviewer | status: verified
    then:
        Ci.score = max(Ci.score, 0.1)
```

The floor is **claim-level**, not note-level. Every claim in a structurally-valid, reviewer-passed wiki entry gets a baseline 0.1 even if it has zero anchors and zero internal cites. This biases the system to trust well-formed wiki entries more strongly than alloy notes — the structural-integrity work is its own kind of friction, and the floor recognizes it.

A claim with anchors above 0.1 is unaffected by the floor. A claim with anchors below 0.1 (rare but possible after dampening) is raised to 0.1. A claim with no anchors gets exactly 0.1.

If the note loses its structural integrity (a marker becomes unparseable, a `@cite` goes dangling), the floor is removed and unanchored claims drop back to 0.

## Note-Level Aggregation

For v1:

```
N.score = mean(Ci.score for Ci in N.claims)
```

Mean across claims, simple. v2 may explore weighted aggregation (e.g., by claim length, by anchor count, by claim age) but v1 is mean.

The note-level score is a derived view shown in the trust report and used for ranking in search results. Internal `@cite` references that point at a whole note (no `#Cn`) read this aggregate as the upstream signal. Internal `@cite` references that point at a specific claim (`[[Note]]#C2`) read the claim-level score directly.

## Structural Integrity Check

A note **passes structural integrity** if all of the following hold. `scripts/trust.py` (Phase B) enforces a minimum subset of these; the full check is the responsibility of `/lint` Phase 1 (Phase D).

**Required (enforced by trust.py from Phase B onward):**

1. The note's file path is under `zk/wiki/`.
2. The note has a `## Claims` section.
3. Every claim heading matches `### [Cn] <text>` with `n` sequential starting from 1.
4. Every claim has at least one paragraph of body text.
5. Every fenced `anchors` block parses: every line is either blank, a comment, or matches `@anchor:` / `@cite:` / `@pass:` with valid pipe-separated fields.
6. Every `@anchor` has a recognized type and a `valid_at`.
7. Every `@cite` resolves: the target note exists in `zk/wiki/`. If a `#Cn` suffix is given, the target claim exists in the target note.
8. Every `@pass` has a recognized agent and status.
9. `valid_at` is a valid ISO date <= today.
10. If `invalid_at` is present, it is a valid ISO date > the corresponding `valid_at`.

**Required for floor eligibility (in addition to the above):**

11. At least one claim in the note has a `@pass: reviewer | status: verified` marker.

**Recommended (enforced by `/lint` Phase 1, Phase D):**

12. The `## Summary` section exists and is non-empty.
13. The `## Revision Log` section exists.
14. No claim is orphaned: every claim is referenced from `## Summary` or has at least one `@anchor` or `@cite`.
15. URLs in `@anchor` markers reach a 200 (cached / periodic check, not real-time).

## Open v2 Items

Documented here so they do not get lost between sessions.

- **Temporal decay.** β = 0.9 per month from Temporal PageRank. Older anchors carry less weight. Requires per-marker age computation.
- **Signed edges (`contradicts`).** A claim that contradicts another claim is not a positive edge. The literature recommends a separate post-processing penalty rather than a signed PageRank, since signed PageRank breaks the stochastic matrix assumption. Defer until contradictions are common enough to matter.
- **Anchor weight from S2 / OpenAlex.** Use `influentialCitationCount` or FWCI as the seed weight for paper anchors. v1 treats all weights as 1.0. The schema field `weight` already exists for forward compatibility.
- **Note-level aggregation alternatives.** Weighted mean by claim length, anchor count, or claim age. v1 is unweighted mean.
- **Claim invalidation.** Currently a marker can be invalidated. A whole claim cannot — there is no `[Cn]` invalidation syntax. If a claim becomes wrong, the v1 workflow is to invalidate all its markers and add a Revision Log entry. v2 may add `### [Cn] ~~Claim text~~` strikethrough as a structural signal.

## Cross-References

- Tag taxonomy and the validation-depth principle: `epistemic-hygiene.md`
- Where wiki entries live and how they sync: `local-first-architecture.md`
- Trust engine implementation (Phase B): `scripts/trust.py` (deferred)
- Lint integration (Phase D): `.claude/commands/lint.md` (deferred)
