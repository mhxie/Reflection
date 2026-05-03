# Atelier

> **A personal workshop, published.** A reflective-thinking system built around [Claude Code](https://docs.anthropic.com/en/docs/claude-code) and a local-first Zettelkasten — covering daily reflection, decision-making, deep reading, goal tracking, and knowledge crystallization. It is not a product, and not aiming to be one. The patterns are reusable; the configuration is bespoke. Read the code, fork what's useful, build your own.

The system surrounds an **œuvre** — the accumulating body of notes, decisions, and reflections, kept locally under `$OV/`. Plain Markdown on disk; nothing leaves your machine. A 12-specialist agent team (le cercle) coordinates session work; a deterministic trust engine (`scripts/trust.py`) scores the wiki layer; `/lint` keeps the corpus self-consistent.

Capture what you learn. Reflect on what you think. Research what you don't know. Read deeply. Make decisions. Track goals across life chapters. Crystallize knowledge you trust.

Drives natively on Claude Code; the same protocols run under [Codex CLI](https://github.com/openai/codex) via `AGENTS.md` and the runtime-adapter contract. Codex is a real second runtime, not a port — but the Claude Code path is the most fully exercised; the Codex path is functional and lighter-tested.

## Who is this for?

Honest framing matters more here than feature lists. Three rough audiences:

1. **Pattern students.** You want to see how someone wired Claude Code to a personal-knowledge-management substrate end-to-end — agent contracts in `harness/agents.toml`, command portability in `harness/commands.toml`, trust scoring in `scripts/trust.py`, the L1–L4 tier model in `protocols/local-first-architecture.md`, the wiki schema in `protocols/wiki-schema.md`. Take the patterns; leave the configuration. **This is the primary audience.**

2. **System forkers.** You want to run something like this for your own thinking. The repo is MIT-licensed, you can fork it. But: a fresh clone has no `$OV/` vault, no `profile/identity.md`, no Readwise inbox, no archetype mnemonics that mean anything to you. The Atelier vocabulary (le cercle, the Painter, le œuvre) is bespoke. Expect to rip and replace; don't expect to clone-and-run.

3. **Maintainer.** Daily use. Self-improving on a weekly cadence via `/system-review` and `scripts/review.sh`.

If you want a turnkey "second brain," this isn't it — it's also not trying to be. The fastest path to disappointment with this kind of system is to inherit someone else's vocabulary, taxonomy, and tier model wholesale; the value lives in writing your own.

## What It Does

**Reflect** — Daily check-ins grounded in what you actually wrote. Surfaces forgotten connections, challenges assumptions, tracks goals across life chapters.

**Read** — Deep-reads articles, saved notes, and transcripts through multiple lenses (critical, structural, practical, dialectical). Multiple readers analyze in parallel; you discuss what they found.

**Plan** — Goal reviews, decision journals, and energy audits. Tracks what's progressing, what's neglected, what's emerging. Uses 22+ thinking frameworks with cross-validation.

**Act** — Compact redundant notes, deep-dive into a topic with 4 agents in parallel, triage notes for cleanup, or curate your Readwise inbox.

**Learn** — Get reading recommendations, or introspect to rebuild your self-model.

**Wiki** — Crystallize validated thinking into `$OV/wiki/` entries with structured claims, external anchors, and bi-temporal markers. `scripts/trust.py` runs Personalized PageRank with external anchors as trust seeds. `/lint` enforces corpus-level structure and harness health.

Session reflections write to `$OV/reflections/`. Daily notes are user-authored — the system reads them but never writes.

## Forking the patterns (the primary use case)

If you read one thing in this repo, read these in order:

1. **`protocols/local-first-architecture.md`** — the L1–L4 tier model. This is the load-bearing idea: directory = certification level, no tags required.
2. **`protocols/wiki-schema.md`** — claim markers (`[C1]`, `@anchor`, `@cite`, `@pass`), bi-temporal `valid_at`/`invalid_at` fields, and how `scripts/trust.py` reads them.
3. **`harness/agents.toml`, `harness/commands.toml`, `harness/models.toml`, `harness/capabilities.toml`** — provider-neutral registries. The Claude Code and Codex runtimes are *adapters*, not first-class consumers. This is the part most worth lifting.
4. **`scripts/trust.py`** — Personalized PageRank with external anchors as seeds. Stdlib-only, deterministic. ~700 lines including the schema parser. Adapt freely.
5. **`scripts/semantic.py`** — pluggable embedder + store backends (BGE-M3 + LanceDB by default). The CLI contract is encoder-agnostic; the embedder choice is yours.
6. **`scripts/lint.py` and `scripts/privacy_check.py`** — quality gates with structured JSON output. Lint enforces wiki schema integrity; privacy_check fails loud on placebo-pass conditions (empty vault, missing config).
7. **`.claude/agents/*.md`** — twelve role specs, each <8KB. Useful as a template for your own agent definitions.

What's deliberately *not* portable: `profile/`, `personal/`, `$OV/wiki/` content, the impressionist vocabulary register (le cercle, the Painter, le œuvre), the bilingual English/Chinese behavior, the Era / Direction taxonomy, and the `/civ`, `/dine`, `/prm` commands which encode a bespoke life-area model. Strip those before adapting.

## Running it (if you want to)

This is the maintainer's daily-use configuration. Running it identically end-to-end is supported, but expect a real onboarding cliff: a fresh clone has no vault, no profile, no notes. Most session commands will guard with "Run `/introspect` first" or warn that `profile/identity.md` is missing. That's working as intended for the maintainer; it's a wall for everyone else.

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (the primary path) or [Codex CLI](https://github.com/openai/codex)
- [uv](https://docs.astral.sh/uv/) — Python package manager (3.11+)
- A `$OV/` directory with at minimum: `daily-notes/`, `wiki/`, `reflections/`. Other tiers (`papers/`, `readwise/`, `cache/`, etc.) are optional.

**Optional:**
- [Gemini CLI](https://github.com/google-gemini/gemini-cli) — second-opinion external reviewer for `/system-review` (`npm i -g @google/gemini-cli`).

### Install

```bash
git clone https://github.com/mhxie/atelier.git ~/atelier
cd ~/atelier
uv sync
echo 'export OV="$HOME/path/to/your/vault"' >> ~/.zshrc
source ~/.zshrc
```

All personal content under `$OV/` is gitignored. Only system configuration (protocols, agents, commands, scripts) is committed.

### First run

Claude Code:

```bash
claude                # open Claude Code in the project
/introspect           # build profile/ from $OV/daily-notes/ — required before most session commands
/reflect              # session menu
```

Codex (functional but less exercised than Claude Code):

```bash
python3 scripts/atelier.py run reflect            # fresh Codex TUI on /reflect
python3 scripts/atelier.py run lint --exec        # one-shot, no TUI
python3 scripts/atelier.py run promote --resume   # continue most recent session
```

Codex reads `AGENTS.md`, picks up the repo-scoped skill under `.agents/skills/`, then adapts `.claude/commands/*.md` through `protocols/runtime-adapters.md`. Several Claude-specific affordances (notably `AskUserQuestion` interactive menus) are emulated rather than native under Codex.

Reflection-type commands (`/reflect`, `/weekly`, `/review`, `/decision`, etc.) default to fresh sessions because reusing a prior session pollutes the new reflection. Continuation-friendly commands (`/promote`) are marked `resume_friendly = true` in `harness/commands.toml`.

## Sessions

Type `/reflect` to get a menu of everything you can do:

| Mode | What happens |
|------|-------------|
| Daily Reflection | Reflects on today's notes, asks questions at increasing depth, surfaces a forgotten connection |
| Weekly Review | Energy + attention audit across the week |
| Explore | Finds hidden connections and open threads across your notes |
| Goal Review | Checks progress on goals — progressing, neglected, or shifted |
| Decision Journal | Structured decision-making with framework cross-validation |
| Energy Audit | Four-dimension assessment (physical, mental, emotional, social) |
| Read & Discuss | Multi-lens reading of an article or note, then interactive discussion |
| Deep Dive | Full briefing on a topic — your notes + web research + resources + framework |
| Compact Notes | Find and merge redundant notes |
| Curate Inbox | Goal-aware triage of your Readwise inbox — score, route, and tag |
| Note Triage | Scan for compaction candidates across your notes |
| Process Meeting | Turn a work meeting transcript into structured notes with action items |

You can also go direct: `/review`, `/weekly`, `/decision`, `/explore`, `/energy-audit`, `/curate`, `/introspect`, `/lint`, `/promote`, `/dine`, `/prm`, `/civ`, `/system-review`.

**Knowledge layer commands:**

| Command | What it does |
|---|---|
| `/promote` | Create an L4 wiki entry from L2 source notes: Researcher finds claims + anchors, Curator drafts schema-compliant entry, orchestrator writes after approval. |
| `/lint` | Corpus-level structural check over `$OV/wiki/` (parse errors, duplicate titles, slug drift, orphan entries, graph topology). Also harness health: CLAUDE.md size and formatting, privacy gate, ingestion hygiene. |

## The Team

Twelve specialist agents (le cercle) work together during sessions. The orchestrator dispatches automatically; you can also talk to any of them directly:

- *"find notes about X"* — sends Researcher (the Observer)
- *"read [[Article]] with critical lens"* — sends Reader
- *"challenge my assumption about X"* — sends Challenger (the Critic)
- *"compact my notes on Y"* — sends Curator (the Collector)
- *"recommend reading on Z"* — sends Librarian (the Cataloguer)
- *"what's happening in the world on X"* — sends Scout (the Flâneur)

Full cercle archetype map (Observer / Colorist / Arbiter / Critic / Structuralist / Collector / Flâneur / Reader / Cataloguer / Scribe / Master / Steward) lives in `protocols/atelier.md`.

## How It Works

```
Capture sources                  Local data layer ($OV/)
(Readwise inbox,                 L4  $OV/wiki/        ─ locally certified
 voice notes,                        (trust-scored canon)
 markdown editor)                L3  $OV/papers/      ─ peer-reviewed
                                 L2  $OV/daily-notes/ + reflections/ +
                                     research/ + preprints/ +
                                     agent-findings/ + drafts/ + …
                                 L1  $OV/cache/, $OV/readwise/

                                         ^
                                         |
                                         v
                            AI runtime (Claude Code or Codex)
                                         |
                     +-----------+-------+-------+-----------+
                     v           v               v           v
                Le Cercle    Sessions     Frameworks    Trust engine
                (12 agents)  (12 types)   (22 + xval)   (trust.py,
                     |           |               |        lint.py)
                     v           v               v
                Protocols    $OV/reflections/   Cross-validation
                (~25 rules)  (session outputs)  & Pattern Library
```

**Five-tier knowledge model.** Everything under `$OV/` is classified by depth of crystallization — raw capture (L1), working notes (L2), externally-certified papers (L3), locally-certified wiki entries (L4). Directory = tier; no tags required. Agents read from disk via semantic search and grep.

**TrustRank over the wiki.** Wiki entries under `$OV/wiki/` follow a structured schema: `## Claims` with `[C1]`, `[C2]`... headings, each backed by fenced `anchors` blocks containing `@anchor` (external evidence), `@cite` (internal edge to another wiki entry), and `@pass` (reviewer verification) markers with bi-temporal `valid_at`/`invalid_at` fields. `scripts/trust.py` runs Personalized PageRank with external anchors as seeds; trust mass enters the graph only at external sources and propagates through internal cites. No external anchor, no trust. `scripts/lint.py` enforces structural integrity across the corpus.

**Session output.** The orchestrator dispatches agents, gathers findings, runs a quality gate, and writes session output to `$OV/reflections/`. Daily notes are user-authored — the system reads them but never writes. All personal data under `$OV/` is gitignored; only system configuration is committed.

**Harness engineering.** `CLAUDE.md` is kept under 8KB because it is inherited by every Claude subagent; each line costs N tokens times N agents per session. `AGENTS.md` and `.agents/skills/atelier/SKILL.md` give Codex the root contract and workflow trigger. `harness/models.toml`, `harness/capabilities.toml`, `harness/commands.toml`, `harness/agents.toml`, and `protocols/runtime-adapters.md` keep provider and runtime assumptions explicit. `scripts/atelier.py` gives Codex command and role discovery plus prompt generation. Critical rules live at the top (primacy effect); detailed specifications load on demand from protocols and agent definitions. The Master of the Atelier (Evolver) has a "subtract before adding" principle and a root-instruction budget gate. `/lint` Phase 0 checks harness health alongside the wiki structural pass.

Key design choices:

- **Local-first**: the knowledge layer lives on disk under `$OV/`, not in a remote app. No external services required.
- **Deterministic trust scoring**: TrustRank is a stdlib-only Python pass, not an LLM heuristic. The same input always produces the same score.
- **Era-aware**: tracks life chapters with themes and directions (Mastery, Impact, Freedom, Connection, Creation).
- **Bilingual**: handles English and Chinese notes; matches your language.
- **Self-improving**: the Master of the Atelier evolves the system, reviewed by external AI models (Codex, Gemini) via `scripts/review.sh`.
- **Privacy by default**: personal data never leaves your machine. `scripts/privacy_check.py` gates committed-file diffs against private filename stems; the Steward (privacy-reviewer agent) catches semantic leaks.

## Vocabulary

The system has a narrative register from the impressionist atelier — *le cercle* (the agents), *the Painter* (you), *the œuvre* (your accumulating body of work), *impression* / *étude* / *tableau* / *série* / *sitting* / *sketch* / *commission*. The register lives in conversation and identity. **Operational keys are unchanged**: slash commands stay `/reflect`, `/promote`, `/lint`, etc.; agent dispatch keys stay `researcher`, `synthesizer`, …; file paths under `$OV/` stay as documented above. Full glossary: `CLAUDE.md` § Vocabulary and `protocols/atelier.md`.

## License

MIT — for the code. The taste, the vocabulary, and the daily-use configuration are not licensed and not portable. Fork the patterns; build your own atelier.
