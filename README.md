# Reflectl

Reflecting on Reflect Notes with Claude Code.

A structured self-reflection system built as a [Claude Code](https://docs.anthropic.com/en/docs/claude-code) project. It connects to your [Reflect.app](https://reflect.app/) notes via MCP — helping you reflect on what you've written, track life eras and directions, surface moments of growth, make decisions, and take action.

## How It Works

```
Reflect.app  <──MCP──>  Claude Code (Orchestrator)
(your notes)                    │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
              Agent Team    Commands    Frameworks (23)
              (8 agents)    (7 commands)    │
                    │           │           ▼
                    ▼           ▼     Cross-validation
              Protocols    Output Files    & Pattern Library
              (15 protocols)    │
                                ▼
                          index/         — reflection context
                          reflections/   — session outputs
```

The orchestrator coordinates a team of 9 specialized agents, each with defined roles and structured communication contracts. Insights are written back to your Reflect daily notes.

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI installed
- [Reflect.app](https://reflect.app/) with the MCP server enabled
- Reflect MCP server running locally (see [Reflect MCP docs](https://reflect.app/mcp))

## Setup

1. **Clone the repo:**
   ```bash
   git clone https://github.com/mhxie/reflectl.git
   cd reflectl
   ```

2. **Configure MCP** — create `.mcp.json` in the project root (gitignored):
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

3. **Build your reflection index:**
   ```bash
   claude
   # then inside Claude Code:
   /index
   ```

4. **Start reflecting:**
   ```
   /reflect         # presents a menu of all session types
   /review          # monthly goal review
   /weekly          # weekly review
   ```

## Commands

| Command | Purpose | Frequency |
|---------|---------|-----------|
| `/reflect` | **Primary entry point** — presents all session types | Daily / every 2-3 days |
| `/index` | Build or refresh reflection context from Reflect notes | Monthly or after life change |
| `/review` | Goal progress review (progressing/neglected/shifted) | Monthly |
| `/weekly` | Weekly review with energy + attention audit | Weekly |
| `/decision` | Structured decision-making with framework cross-validation | As needed |
| `/explore` | Open-ended exploration surfacing forgotten connections | Weekly |
| `/energy-audit` | Four-dimension energy assessment | Monthly |

## Agent Team

| Agent | Role |
|-------|------|
| **Researcher** | Gathers raw context from Reflect notes (progressive disclosure search) |
| **Synthesizer** | Produces structured reflections with pattern recognition taxonomy |
| **Reviewer** | Quality-checks output with scored rubric (0-10, 5 dimensions) |
| **Challenger** | Asks probing questions (depth taxonomy + emotional register detection) |
| **Thinker** | Applies thinking frameworks independently with meta-cognitive checks |
| **Evolver** | Improves the system using OODA methodology + codex external review |
| **Curator** | Note operations — compact, merge, replace, create notes in Reflect |
| **Scout** | Gathers external context from the web — articles, research, recent developments |
| **Librarian** | Recommends resources (books, papers, articles, talks, courses) |

During sessions, you can dispatch actions to any agent: "find notes about X", "compact my notes on Y", "recommend reading on Z", "challenge my assumption about W".

## Architecture

**MCP-first design** — queries Reflect's MCP server on-the-fly using text and vector search. A lightweight local index (~15K tokens) caches only the reflection context needed per session.

Key design decisions:
- **Team-based**: 9 specialized agents with structured handoff contracts and quality gates
- **Era-aware**: tracks life chapters (eras) with themes, directions, and momentum assessment
- **Direction-oriented**: 5 personal directions (Mastery, Impact, Freedom, Connection, Creation) shape what "progress" means
- **Moment tracking**: flags real-life firsts and breakthroughs that mark growth across directions
- **Protocol-driven**: 16 protocols governing agent behavior, error handling, and evolution
- **Framework-rich**: 23 thinking frameworks with cross-validation pairings
- **Two-way data flow**: reads notes via MCP, writes insights back to Reflect
- **Self-contamination guard**: AI content tagged `#ai-reflection`, excluded from future searches
- **Yield tracking**: session scores as visible outputs (Evidence, Insight, Alignment, Momentum, Discovery)
- **Amenity floor**: per-area sustainability minimums to prevent burnout
- **Focus lock**: quarterly commitment with friction — changing focus requires a full review
- **Session continuity**: file-based memory chain connecting sessions over time
- **Self-improving**: Evolver agent + codex review loop for continuous system evolution
- **Bilingual**: handles English and Chinese notes, matches the user's language
- **Privacy by default**: all personal data gitignored

## Frameworks (23)

Organized by question type:

| Question | Frameworks |
|----------|-----------|
| Direction | Ikigai, Regret Minimization, First Principles, Jobs to Be Done, Map of Meaning |
| Constraint | Immunity to Change, Theory of Constraints, Five Whys, Double-Loop Learning |
| Judgment | Pre-Mortem, Dialectical Thinking, Inversion, Second-Order Thinking |
| Priority | Eisenhower Matrix, Pareto Principle, Wardley Mapping |
| Awareness | Johari Window, OODA Loop, Circle of Competence, Cynefin |
| Resilience | Stoic Reflection, Growth Mindset, Map of Meaning |

## Project Structure

```
reflectl/
  CLAUDE.md                        # System persona and orchestrator rules
  .claude/
    agents/                        # 9 agent definitions
    commands/                      # 7 command definitions
    settings.json                  # Enables experimental agent teams
  protocols/                       # 16 system protocols
  frameworks/                      # 23 thinking frameworks
  index/                           # Coaching context (gitignored)
  reflections/                     # Session outputs (gitignored)
  .mcp.json                        # MCP server config (gitignored)
```

## License

MIT
