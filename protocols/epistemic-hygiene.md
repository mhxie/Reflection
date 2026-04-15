# Epistemic Hygiene

How reflectl distinguishes well-validated thinking from raw or alloyed thinking, and how it guards against the failure modes specific to AI-augmented reflection.

## The Principle

**The criterion for reasoning priority is validation depth, not origin.** Whether a thought was first written by a human or first uttered by an LLM is the wrong axis. The right axis is: how much friction has this thought survived?

Earlier versions of this system used an `#ai-reflection` / `#ai-generated` / untagged-as-human three-way tag. That model is retired. It encoded a binary that does not survive the admission "I cannot imagine a world without AI assistance" — once any session touches a thought, the thought is alloyed by default. The interesting question is no longer "did a human or an AI produce this," it is "how many independent passes of friction has the claim survived, and against what."

## The Validation-Depth Taxonomy

Three tiers, in increasing order of validation depth.

### Alloy (default, no tag required)

The default state of every thought that has passed through any reflectl session. Mixed authorship, mixed validation. Useful, searchable, citable, but not certified. Most daily-note write-backs, session reflections, routine notes, and the bulk of the user's Obsidian vault live here.

Applies to: anything written collaboratively with the system, anything the system has digested, anything that has been queried about. No tag required — alloy is what you get for free.

### Wiki entry (location-based)

A note that lives under `zk/wiki/` and follows the **wiki schema** (see `wiki-schema.md`): explicit `## Claims` section, each claim carrying its own anchor set, structured `@anchor` / `@cite` / `@pass` markers with bi-temporal `valid_at` / `invalid_at` semantics, and structural integrity verified by lint. **The certification is the location, not a tag.** Anything in `zk/wiki/` is a wiki entry by definition, and the trust engine treats it as one. No `#compiled-truth` tag, no `#wiki` tag — the directory walk is the contract.

Applies to: notes the user wants the system to treat as authoritative in the local-first knowledge layer. These are the only notes that participate in TrustRank propagation.

This design choice (location over tag) has a reason: `zk/` is the user's pre-existing Obsidian vault with hundreds of notes and an established tagging convention. Adding a structural sub-tier by tag would conflict with that convention and force the trust engine to filter every note in the vault. A dedicated subdirectory (`zk/wiki/`) is cleaner — the trust engine walks one directory; the user's other tags stay free.

### `#solo-flight` (rare)

The narrowest, most certified tier: an unstructured free-write the user produced **without any AI assistance whatsoever** — no draft from the system, no prior conversation with the system that fed into it, no LLM-summarized source material. A genuine independent calibration unit.

Applies to: periodic (monthly or quarterly) free-writes the user does deliberately to check for drift between AI-assisted and unassisted thought. Also applies to any captured raw thought the user wants to mark as load-bearing un-touched-by-AI for later comparison. `#solo-flight` is location-independent — it can live in a Reflect daily note, in the Obsidian vault outside `wiki/`, or anywhere else the user captures unmediated thought.

`#solo-flight` is rare on purpose. If everything is solo-flight, the tag means nothing. If nothing is solo-flight, there is no calibration tier and drift cannot be detected.

### What changes for search

Search **no longer excludes** notes tagged `#ai-reflection`. The old exclusion rule was a bug: it conflated "produced by AI" with "low validation," then used the conflation to hide reflection content from itself. Reflection write-backs are alloy by default and can be cited like any other note. The tag `#ai-reflection` may still appear on legacy notes; treat it as a historical alloy marker, not a reason to exclude.

Trust scores from the engine (Phase B), not tag-based exclusion, are the right way to weight what comes back from search. A wiki entry with a high trust score should rank above an alloy note. An alloy note with no contradicting evidence should not be hidden — it should be visible and weighted accordingly.

## The Failure Modes the Design is Bounded By

Two failure modes anchor the design at opposite ends.

### Karpathy's failure mode (the "pure-LLM-OK" drift)

In the LLM Knowledge Bases gist, Andrej Karpathy treats everything in his second brain as acceptable for LLM ingestion and synthesis. There is no zone where the human writer's unmediated voice is preserved as load-bearing. The risk: the second brain becomes a closed loop where the LLM's prior outputs feed the LLM's next outputs, with no external friction to break the cycle. Trust propagates from nothing.

reflectl's structural answer: external anchors are the only seeds of trust. Internal agent passes (Reviewer, Challenger, Thinker) can floor or invalidate trust but never accumulate it. See `wiki-schema.md` → "The Trust Propagation Rule."

### Appleton's failure mode (human centipede epistemology)

Maggie Appleton's Dark Forest essay names the endpoint:

> "If content generated from models becomes our source of truth, the way we know things is simply that a language model once said them, and then they're forever captured in the circular flow of generated information."

The risk: anchors themselves degrade as the source corpus (papers, articles, discussions) becomes increasingly AI-assisted. Even "external validation" stops being independent.

reflectl's structural answer: **bi-temporal anchors**. Every `@anchor` carries a `valid_at` timestamp recording when the anchor was added. Later invalidation gets `invalid_at`. This lets the system answer "was this claim externally supported *at the time it was anchored*, even if the anchor has since been superseded?" — which is the right question once the anchor corpus itself can degrade. See `wiki-schema.md` → "Bi-temporal Anchors."

The user's failure mode is not Karpathy's. The user's risk is treating everything as acceptably mixed and losing any anchor — "alloy as surrender." The taxonomy and the trust engine exist to prevent that drift.

## The Three Habits

Three behavioral practices counteract AI-confirmation loops at the human level. These are not enforced by tooling — they are practiced by the user.

### 1. Write-first

If today's daily note is empty when a session starts, the orchestrator gently invites the user to jot their unmediated position before the AI digs in. A nudge, not a gate. The point is to capture a baseline that has not been pre-shaped by what the system might say.

### 2. AI-free zones

When the user declares a topic they want to think through independently, the orchestrator respects it: provide evidence (Researcher) but withhold frameworks and reframes (no Thinker, no Synthesizer interpretation). The user does the thinking; the system stays in the receipts role.

### 3. Solo flight

Periodically (monthly or quarterly), the user reflects without any AI agents at all. The output may get tagged `#solo-flight` if it is a candidate calibration unit. The user then compares the solo-flight output against AI-assisted sessions on similar topics to check for drift. If the two diverge meaningfully, the AI-assisted sessions are biased and the orchestrator should be told why.

## Refinement-arc Hygiene

A subtle failure mode arises when the user refines a strategic or directional claim multiple times in a single session (bet → narrower bet → narrower bet still): progressive narrowing can look like "getting sharper" when it is actually scope reduction to fit what the orchestrator can easily affirm. Each refinement gets called "better than the last," but the orchestrator may not be applying equal rigor to the earlier versions. The orchestrator may be mirroring the user's growing care rather than independently evaluating.

This is distinct from normal iterative thinking. It bites specifically when:
- The user is making a directional or strategic claim (career bet, product strategy, identity thesis)
- The claim is refined 2 or more times within one session
- Each refinement is narrower in scope than the prior
- The orchestrator is the only counterparty

**The rule.** Once a strategic claim is refined twice or more in the same session, the orchestrator must:

1. Label the latest version as "working hypothesis (refinement N)", not "refined position"
2. Auto-dispatch Challenger against the latest version, with the prior version(s) as comparison set, before any write-back
3. Refuse to frame later iterations as monotonically better than earlier ones without running the same rigor against earlier versions
4. Attach explicit disconfirm tests to the working hypothesis, so future sessions can detect when the hypothesis stops holding

**Why this rule exists.** A strategic refinement arc has the same risk profile as an AI-confirmation loop, just at a higher level. Instead of the orchestrator echoing the user's words, the orchestrator echoes the *direction* of the user's refinements. Each step feels like progress because it is monotonically endorsed, but progress-by-endorsement is not progress-by-friction. Friction comes from independent adversarial evaluation (the Challenger's role); the orchestrator's own voice cannot substitute.

See `protocols/orchestrator.md` → Collaboration Triggers → "User refines a strategic/directional claim 2+ times".

## The Sacred Zone

The only truly sacred unit — the only thing that remains uncolored by the system — is **unstructured daily-note free-writes that never become the seed of an AI session**. The moment a session starts on them, they become alloy. There is no way to "un-alloy" a thought after the system has touched it.

This is fine. The taxonomy is honest about it. The point of `#solo-flight` is not to keep most thoughts pure (impossible) but to keep a deliberate calibration tier alive.

## How This Connects to the Rest of the System

- **Tag taxonomy** lives here. The wiki schema (`wiki-schema.md`) defines the structure for files under `zk/wiki/`. The trust engine (Phase B, `scripts/trust.py`) reads only the `zk/wiki/` subtree.
- **Knowledge tiers (L1–L5)** are defined in `local-first-architecture.md` and describe *where* a note lives. They are orthogonal to the validation-depth categories above. Wiki entries live at L4 (`zk/wiki/`). Alloy notes live anywhere from L1 to L3 (Reflect, daily notes, session reflections, the rest of the Obsidian vault, curated receipts). `#solo-flight` notes are usually captured in the L1 daily-note layer in Reflect. To avoid confusion: the L1–L5 axis is "knowledge storage / certification level," the alloy / wiki entry / `#solo-flight` axis is "validation depth."
- **Search behavior** changes: no exclusion rule based on `#ai-reflection`. Use trust scores (when available) or recency + relevance (when not).
- **Curator and Researcher** behavior change is staged for Phase C: Curator writes wiki entries to `zk/wiki/` first; Researcher routes wiki queries to the local layer first.
