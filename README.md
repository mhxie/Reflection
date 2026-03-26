# Reflection

Reflecting on Reflect Notes with Claude Code.

A structured self-reflection system built as a [Claude Code](https://docs.anthropic.com/en/docs/claude-code) project. It connects to your [Reflect.app](https://reflect.app/) notes via MCP — helping you reflect on what you've written, structure your thoughts, track goals, make decisions, and take action.

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

The orchestrator coordinates a team of 8 specialized agents, each with defined roles and structured communication contracts. Insights are written back to your Reflect daily notes.

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI installed
- [Reflect.app](https://reflect.app/) with the MCP server enabled
- Reflect MCP server running locally (see [Reflect MCP docs](https://reflect.app/mcp))

## Setup

1. **Clone the repo:**
   ```bash
   git clone https://github.com/mhxie/Reflection.git
   cd Reflection
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
   /project:index
   ```

4. **Start reflecting:**
   ```
   /project:reflect    # daily reflection
   /project:weekly     # weekly review
   /project:review     # monthly goal review
   ```

## Commands

| Command | Purpose | Frequency |
|---------|---------|-----------|
| `/project:index` | Build or refresh reflection context from Reflect notes | Monthly |
| `/project:reflect` | Daily reflection with grounded questions | Daily / every 2-3 days |
| `/project:review` | Goal progress review (progressing/neglected/shifted) | Monthly |
| `/project:weekly` | Weekly review with energy + attention audit | Weekly |
| `/project:decision` | Structured decision-making with framework cross-validation | As needed |
| `/project:explore` | Open-ended exploration surfacing forgotten connections | Weekly |
| `/project:energy-audit` | Four-dimension energy assessment | Monthly |

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
| **Librarian** | Recommends resources (books, papers, articles, talks, courses) |

During sessions, you can dispatch actions to any agent: "find notes about X", "compact my notes on Y", "recommend reading on Z", "challenge my assumption about W".

## Architecture

**MCP-first design** — queries Reflect's MCP server on-the-fly using text and vector search. A lightweight local index (~15K tokens) caches only the reflection context needed per session.

Key design decisions:
- **Team-based**: 8 specialized agents with structured handoff contracts and quality gates
- **Protocol-driven**: 15 protocols governing agent behavior, error handling, and evolution
- **Framework-rich**: 23 thinking frameworks with cross-validation pairings
- **Two-way data flow**: reads notes via MCP, writes insights back to Reflect
- **Self-contamination guard**: AI content tagged `#ai-reflection`, excluded from future searches
- **Quality gates**: 3-stage gate architecture with scored rubric and revision loops
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
Reflection/
  CLAUDE.md                        # System persona and orchestrator rules
  .claude/
    agents/                        # 8 agent definitions
    commands/                      # 7 command definitions
    settings.json                  # Enables experimental agent teams
  protocols/                       # 15 system protocols
  frameworks/                      # 23 thinking frameworks
  index/                           # Coaching context (gitignored)
  reflections/                     # Session outputs (gitignored)
  .mcp.json                        # MCP server config (gitignored)
```

## License

MIT
