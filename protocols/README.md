# Protocols — Quick Reference

This is the entry point for all agents. When you need to know how to behave, start here.

## By Situation

### Starting a session
1. Read `orchestrator.md` — understand your role as hub
2. Read `session-continuity.md` — connect to previous sessions
3. Read `coaching-progressions.md` — adapt depth to user maturity

### During a session
4. Read `quality-gates.md` — check work before passing it on
5. Read `agent-handoff.md` — format your output for the next agent
6. Read `error-handling.md` — when things break or need escalation

### Producing output
7. Read `session-scoring.md` — score every session
8. Read `pattern-library.md` — recognize recurring patterns

### After a session
9. Read `meta-reflection.md` — assess system health
10. Read `session-log.md` — emit the session process log

### During system evolution
11. Read `harness-assumptions.md` — check for stale model-era assumptions

## By Agent

| Agent | Must-read protocols |
|-------|-------------------|
| **Orchestrator** | orchestrator.md, quality-gates.md, error-handling.md, session-continuity.md, session-log.md |
| **Researcher** | agent-handoff.md, error-handling.md |
| **Synthesizer** | agent-handoff.md, quality-gates.md, pattern-library.md, session-scoring.md |
| **Reviewer** | quality-gates.md, agent-handoff.md |
| **Challenger** | coaching-progressions.md, error-handling.md |
| **Thinker** | pattern-library.md |
| **Curator** | error-handling.md, agent-handoff.md, epistemic-hygiene.md |
| **Scout** | error-handling.md |
| **Reader** | agent-handoff.md |
| **Meeting** | agent-handoff.md |
| **Librarian** | (none required) |
| **Evolver** | meta-reflection.md, session-scoring.md, harness-assumptions.md |

## Protocol Dependency Graph

```
orchestrator.md
  ├── agent-handoff.md (defines communication contracts)
  ├── quality-gates.md (defines checkpoints)
  │     └── session-scoring.md (scoring rubric used by gates)
  ├── error-handling.md (includes escalation rules and emotional escalation)
  └── session-continuity.md (cross-session memory)

coaching-progressions.md (adapts depth)

pattern-library.md (recognizes patterns, Moments, trade routes)

epistemic-hygiene.md (validation-depth taxonomy)
  └── wiki-schema.md (L4 entry format, claim markers, anchors)

local-first-architecture.md (five-tier model, $ZK/ layout)

session-log.md (session process recording)
  └── meta-reflection.md (reads session logs for system health)

harness-assumptions.md (model-era assumption registry)
```
