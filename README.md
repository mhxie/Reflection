# reflectl

A personal reflection system that reads your notes and helps you think.

Built on [Claude Code](https://docs.anthropic.com/en/docs/claude-code) + [Reflect.app](https://reflect.app/). It connects to your notes via MCP, then coordinates a team of AI agents to help you reflect, read deeply, make decisions, and take action.

## What It Does

**Reflect** — Daily check-ins grounded in what you actually wrote. Surfaces forgotten connections, challenges assumptions, tracks your goals across life chapters.

**Read** — Deep-reads articles and saved notes through multiple lenses (critical, structural, practical, dialectical). Multiple readers analyze in parallel, then you discuss what they found.

**Plan** — Goal reviews, decision journals, and energy audits. Tracks what's progressing, what's neglected, and what's emerging. Uses 23 thinking frameworks with cross-validation.

**Act** — Compact redundant notes, deep-dive into a topic with 4 agents working in parallel, or triage your notes for cleanup.

**Learn** — Get reading recommendations or rebuild your reflection index.

Everything writes back to your Reflect daily notes (with your approval), so insights stay where your notes live.

## Getting Started

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- [Reflect.app](https://reflect.app/) with the [MCP server](https://reflect.app/mcp) running locally

### Install

```bash
git clone https://github.com/mhxie/reflectl.git
cd reflectl
```

Create `.mcp.json` in the project root:

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
/index                # build your reflection profile from your notes
/reflect              # start your first session
```

## Sessions

Type `/reflect` to get a menu of everything you can do:

| Mode | What happens |
|------|-------------|
| **Daily Reflection** | Reflects on today's notes, asks questions at increasing depth, surfaces a forgotten connection |
| **Weekly Review** | Energy + attention audit across the week |
| **Explore** | Finds hidden connections and open threads across your notes |
| **Goal Review** | Checks progress on goals — progressing, neglected, or shifted |
| **Decision Journal** | Structured decision-making with framework cross-validation |
| **Energy Audit** | Four-dimension assessment (physical, mental, emotional, social) |
| **Read & Discuss** | Multi-lens reading of an article or note, then interactive discussion |
| **Deep Dive** | Full briefing on a topic — your notes + web research + resources + framework |
| **Compact Notes** | Find and merge redundant notes |

You can also go direct: `/review`, `/weekly`, `/decision`, `/explore`, `/energy-audit`, `/index`.

## The Team

Ten agents work together during sessions. You don't need to manage them — the orchestrator dispatches automatically. But you can talk to any of them directly:

- *"find notes about X"* — sends Researcher to search your notes
- *"read [[Article]] with critical lens"* — sends Reader to analyze
- *"challenge my assumption about X"* — sends Challenger to probe
- *"compact my notes on Y"* — sends Curator to merge
- *"recommend reading on Z"* — sends Librarian to curate
- *"what's happening in the world on X"* — sends Scout to search the web

## How It Works

```
Reflect.app  <──MCP──>  Claude Code (Orchestrator)
(your notes)                    |
                    +-----------+-----------+
                    v           v           v
              Agent Team    Sessions    Frameworks
              (10 agents)   (9 types)   (23 frameworks)
                    |           |           |
                    v           v           v
              Protocols    reflections/  Cross-validation
              (16 rules)   (outputs)     & Pattern Library
```

Your notes stay in Reflect. The system reads them on-the-fly via MCP, runs sessions with the agent team, and writes insights back to your daily notes. All personal data is gitignored — only the system configuration is committed.

Key design choices:
- **Era-aware** — tracks life chapters with themes and directions (Mastery, Impact, Freedom, Connection, Creation)
- **Bilingual** — handles English and Chinese notes, matches your language
- **Self-improving** — the Evolver agent evolves the system after sessions
- **Privacy by default** — personal data never leaves your machine

## License

MIT
