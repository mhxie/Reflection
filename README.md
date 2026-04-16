# reflectl

Your AI-native personal operating system.

Capture what you learn. Reflect on what you think. Research what you don't know. Read deeply. Make decisions. Track goals across life chapters. Crystallize knowledge you trust. All orchestrated by a team of 11 AI agents over a local-first Zettelkasten — your data on your machine, scored by a deterministic trust engine, improving itself every session.

Built on [Claude Code](https://docs.anthropic.com/en/docs/claude-code) with `$ZK/` as the local data layer. [Reflect.app](https://reflect.app/) and [Readwise](https://readwise.io/) are optional capture surfaces; the authoritative knowledge lives on disk.

## What It Does

**Reflect** — Daily check-ins grounded in what you actually wrote. Surfaces forgotten connections, challenges assumptions, tracks your goals across life chapters.

**Read** — Deep-reads articles, saved notes, and transcripts through multiple lenses (critical, structural, practical, dialectical). Multiple readers analyze in parallel, then you discuss what they found.

**Plan** — Goal reviews, decision journals, and energy audits. Tracks what's progressing, what's neglected, and what's emerging. Uses 22 thinking frameworks with cross-validation.

**Act** — Compact redundant notes, deep-dive into a topic with 4 agents working in parallel, triage your notes for cleanup, or curate your Readwise inbox.

**Learn** — Get reading recommendations or introspect to rebuild your self-model.

**Wiki** — Crystallize validated thinking into `$ZK/wiki/` entries with structured claims, external anchors, and bi-temporal markers. A TrustRank pass (`scripts/trust.py`) scores each claim via Personalized PageRank with external anchors as trust seeds. `/lint` enforces corpus-level structure and harness health; `/sync` pushes wiki entries to Reflect for mobile reading.

Session reflections are written to `$ZK/reflections/` as the durable session output. Daily notes are the user's capture stream and are read-only from the system's perspective. Compiled knowledge lives locally in `$ZK/wiki/` and syncs out one-way.

## Getting Started

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- [uv](https://docs.astral.sh/uv/) — Python package manager

**Optional — enhances the system but not required:**
- [Reflect.app](https://reflect.app/) with the [MCP server](https://reflect.app/mcp) — enables mobile capture via daily notes and `/sync` push to Reflect for mobile reading. The system is local-first; everything works without Reflect, you just lose the mobile capture and display surface.
- [Codex CLI](https://github.com/openai/codex) — `npm i -g @openai/codex` — external code reviewer for system evolution audits
- [Gemini CLI](https://github.com/google-gemini/gemini-cli) — `npm i -g @google/gemini-cli` — second external reviewer perspective

Core scripts (`trust.py`, `lint.py`, `staleness.py`, `session_log.py`) are stdlib-only. Semantic search and document conversion deps are managed via `pyproject.toml`.

### Install

```bash
git clone https://github.com/mhxie/reflectl.git ~/reflectl
cd ~/reflectl
uv sync                # install dependencies from pyproject.toml
```

Set `$ZK` to point to your Zettelkasten vault (the directory containing `daily-notes/`, `wiki/`, `reflections/`, etc.):

```bash
echo 'export ZK="$HOME/path/to/zk"' >> ~/.zshrc
source ~/.zshrc
```

If using Reflect, create `.mcp.json` in the project root:

```json
{
  "mcpServers": {
    "reflect": {
      "type": "http",
      "url": "http://127.0.0.1:7676/mcp"
    }
  }
}
```

### First Run

```bash
claude                # open Claude Code in the project
/introspect           # build your self-model from your notes (reads $ZK/daily-notes/)
/reflect              # start your first session
```

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

You can also go direct: `/review`, `/weekly`, `/decision`, `/explore`, `/energy-audit`, `/curate`, `/introspect`, `/sync`, `/lint`, `/promote`, `/paper-review`.

**Knowledge layer commands:**

| Command | What it does |
|---|---|
| `/promote` | Create an L4 wiki entry from L2 source notes: Researcher finds claims + anchors, Curator drafts schema-compliant entry. |
| `/sync` | Push `$ZK/wiki/` entries to Reflect for mobile display. One-way, manifest-tracked, never pulls back. |
| `/lint` | Corpus-level structural check over `$ZK/wiki/` and the sync manifest (parse errors, duplicate titles, slug drift, orphan entries, graph topology). Also checks harness health: CLAUDE.md size and formatting. |
| `/restore` | Emergency wiki recovery from Reflect's append-only archive. Very rarely triggered. |

## The Team

Eleven agents work together during sessions. You don't need to manage them — the orchestrator dispatches automatically. But you can talk to any of them directly:

- *"find notes about X"* — sends Researcher to search your notes
- *"read [[Article]] with critical lens"* — sends Reader to analyze
- *"challenge my assumption about X"* — sends Challenger to probe
- *"compact my notes on Y"* — sends Curator to merge
- *"recommend reading on Z"* — sends Librarian to curate
- *"what's happening in the world on X"* — sends Scout to search the web

## How It Works

```
Capture sources                 Local data layer ($ZK/)              Display
(Reflect, Readwise,  ─sync──>   L4  $ZK/wiki/         ──/sync──>  Reflect
 voice, mobile)                 (trust-scored)                   (mobile read)
                                L3  $ZK/papers/
                                L2  $ZK/daily-notes/, reflections/,
                                    research/, preprints/,
                                    agent-findings/, drafts/, ...
                                L1  $ZK/cache/, $ZK/readwise/

                                        ^
                                        |
                                        v
                                Claude Code (Orchestrator)
                                        |
                    +-----------+-------+-------+-----------+
                    v           v               v           v
              Agent Team    Sessions      Frameworks   Trust engine
              (11 agents)  (12 types)   (22 + xval)  (trust.py,
                    |           |               |       lint.py)
                    v           v               v
              Protocols    $ZK/reflections/   Cross-validation
              (21 rules)   (session outputs) & Pattern Library
```

**Five-tier knowledge model.** Everything under `$ZK/` is classified by depth of crystallization — raw capture (L1), working notes (L2), externally-certified papers (L3), locally-certified wiki entries (L4). Directory = tier; no tags required. Agents read from disk via semantic search and grep, not via MCP. Reflect is demoted to a capture + display surface.

**TrustRank over the wiki.** Wiki entries under `$ZK/wiki/` follow a structured schema: `## Claims` with `[C1]`, `[C2]`... headings, each backed by fenced `anchors` blocks containing `@anchor` (external evidence), `@cite` (internal edge to another wiki entry), and `@pass` (reviewer verification) markers with bi-temporal `valid_at`/`invalid_at` fields. `scripts/trust.py` runs Personalized PageRank with external anchors as seeds; trust mass enters the graph only at external sources and propagates through internal cites. No external anchor, no trust. `scripts/lint.py` enforces structural integrity across the corpus.

**Session reflection.** The orchestrator dispatches agents, gathers findings, runs a quality gate, and writes session output to `$ZK/reflections/`. Daily notes are the user's capture stream and are never written to by the system. All personal data under `$ZK/` is gitignored; only the system configuration (protocols, agents, commands, scripts) is committed.

**Harness engineering.** CLAUDE.md is kept minimal (~7KB) because it is inherited by every subagent; each line costs N tokens times N agents per session. Critical rules live at the top (primacy effect), detailed specifications are loaded on demand from protocols and agent definitions. The Evolver agent has a "subtract before adding" principle and a CLAUDE.md budget gate. `/lint` Phase 0 checks harness health (file size, formatting) alongside the wiki structural pass.

Key design choices:
- **Local-first**: the knowledge layer lives on disk, not in a remote app. MCP is used only as a narrow escape hatch for today's unsynced capture and for pushing finished wiki entries to Reflect.
- **Reflect as append-only archival**: Reflect's MCP has `create_note` and `append_to_daily_note` but no update or delete. That's a drawback for editing, but a feature for recovery: any wiki entry pushed via `/sync` leaves a tamper-evident trail in Reflect's cloud. The rarely-triggered `/restore` command operationalizes this property.
- **Deterministic trust scoring**: TrustRank is a stdlib-only Python pass, not an LLM heuristic. The same input always produces the same score.
- **Era-aware**: tracks life chapters with themes and directions (Mastery, Impact, Freedom, Connection, Creation)
- **Bilingual**: handles English and Chinese notes, matches your language
- **Self-improving**: the Evolver agent evolves the system with harness engineering best practices, reviewed by external AI models (Codex, Gemini) via `scripts/review.sh`
- **Privacy by default**: personal data never leaves your machine

## License

MIT
