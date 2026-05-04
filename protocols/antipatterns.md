## Antipatterns Catalog

Named failure modes that slip past presence-oriented review. Used by the Reviewer (System Diff and System Holistic modes) and the Evolver (Decide phase) on Tier 2+ changes, because evasion is easier when nobody has to name the class of thing they just bypassed.

## How to use in a review

For each antipattern below, write one of:
- `FLAG: <file:line> - <specific finding>`
- `N/A: <one-line reason this change does not touch this class>`

Silent skips are not allowed. A non-trivial change with zero FLAGs and zero justified N/As is itself a rubber-stamp (see `.claude/agents/reviewer.md` -> Adversarial Mandate).

## What a FLAG means

A FLAG is a SHOULD-FIX concern at minimum. It does not auto-block; the Reviewer composes the per-FLAG severity using the Detect criterion plus the change context, then routes through the standard concern list (BLOCKER / SHOULD-FIX / NICE-TO-HAVE) feeding the system review verdict (`.claude/agents/reviewer.md` -> Scoring -> System Review).

When a FLAG fires:
1. **Reviewer:** record severity in the concern list with `file:line`. The Remediate line on the matching catalog entry is the default fix path; deviate only with a one-line reason in the concern entry.
2. **Evolver:** if running the self-check before dispatching the Reviewer, do not silently downgrade a FLAG to N/A; surface it in the handoff so the Reviewer sees the same evidence.
3. **Orchestrator:** treat unresolved BLOCKER FLAGs as a verdict floor breach (forces NEEDS_REVISION). SHOULD-FIX and NICE-TO-HAVE FLAGs surface in the synthesis but do not by themselves block the verdict if the rest of the rubric clears.

## When required

| Tier | Antipattern scan |
|------|------------------|
| 1 (single-file fix) | Optional |
| 2+ (multi-file, protocol, agent, or command changes) | Required |

## Catalog

### 1. Premature abstraction
Introduces a helper, base class, or protocol contract before 3+ concrete call sites exist.
- Detect: new abstraction has fewer than 3 call sites in the same commit.
- Remediate: inline the first 2-3 uses; extract only when the third use confirms the shape.

### 2. Rule duplication
The same rule lives in CLAUDE.md, an agent file, and a protocol simultaneously.
- Detect: grep a noun phrase from the new rule across `CLAUDE.md`, `.claude/agents/`, `protocols/`. More than one hit for the same instruction is a flag.
- Remediate: keep the rule in the most specific location (agent > command > protocol > CLAUDE.md). Cross-reference, do not duplicate.

### 3. Happy-path-only design
Describes success but not failure modes, timeouts, missing inputs, or concurrent access.
- Detect: no section, table, or line addresses what happens when preconditions fail.
- Remediate: name the top 2 failure modes and what the system does about each.

### 4. Implicit contracts
References a type, agent, tool, handoff field, or protocol that is not defined in the current diff or already in the repo.
- Detect: grep each referenced symbol; absence is an implicit contract.
- Remediate: define it in the same change or drop the reference.

### 5. Monotonic growth
Adds a rule, file, or step without identifying what could be retired.
- Detect: net line count strictly positive across `protocols/` + `.claude/agents/` + `CLAUDE.md`, with no deletions.
- Remediate: name what this subsumes or replaces. If genuinely additive, state why nothing could be removed.

### 6. Shadow state
The same fact or threshold is encoded in two or more places.
- Detect: numeric thresholds, file paths, tier counts, model IDs, or scoring cutoffs appearing in multiple files.
- Remediate: one source of truth; others cross-reference.

### 7. Behavior coupled to location
Assumes "if it lives in directory X it will be treated as Y" without enforcement.
- Detect: directory-based semantics (`$OV/wiki/`, `$OV/cache/`, `$OV/reflections/`) without a script or guard that checks them.
- Remediate: add a `scripts/` check, or document the coupling explicitly so it is visible to future changes.

### 8. Scope creep past the stated criterion
The diff includes changes unrelated to the success criterion the Evolver or user stated.
- Detect: files or edits that do not serve the stated criterion.
- Remediate: split into a separate change, or fold back to criterion-only edits.

### 9. Placebo guard
A script, hook, or check runs but does not catch the thing it claims to catch.
- Detect: the guard has no known-failing input in its own test or history; its logic silently passes on missing, empty, or malformed input.
- Remediate: add a known-bad input case, or a fail-loud branch for empty/missing input.

### 10. Legacy framing in living docs
Narrates a past system state inside a forward-living doc instead of describing current behavior. Protocols, agent specs, and shared docs answer "how does the system work?", not "how did it used to work?". Git is the archive for that.
- Detect: the diff introduces (or leaves untouched while editing nearby lines) phrasings such as "earlier version", "previously", "no longer", "legacy ... retired", "deprecated", "formerly", or version-only carve-outs ("in v1 we ...", "for v1") in `protocols/`, `.claude/agents/`, `harness/`, `CLAUDE.md`, `AGENTS.md`, or `README.md`.
- Remediate: state the current rule in present tense and delete the historical narration. Genuinely-deferred work goes in a single dedicated roadmap subsection (the pattern: `wiki-schema.md` → Open v2 Items), not as scattered "v1 only" parentheticals. Operational pointers to runtime artifacts the system still encounters (e.g., "`#ai-reflection` may appear on historical notes; treat as alloy") are not legacy framing because they describe a runtime condition, not system biography.
