# Protocols — Quick Reference

Entry point for all agents. When you need to know how to behave, start here.

## By Situation

- **Session start.** `orchestrator.md` (role as hub) → `session-continuity.md` (cross-session) → `coaching-progressions.md` (depth).
- **During session.** `quality-gates.md` (checkpoints) → `agent-handoff.md` (envelope format) → `error-handling.md` (escalation).
- **Producing output.** `session-scoring.md` (rubric) → `pattern-library.md` (recurring patterns).
- **After session.** `meta-reflection.md` (system health) → `session-log.md` (process log).
- **System evolution.** `harness-assumptions.md` (stale model-era assumptions).

## By Agent

| Agent | Must-read protocols |
|-------|-------------------|
| **Orchestrator** | orchestrator, quality-gates, error-handling, session-continuity, session-log |
| **Researcher** | agent-handoff, error-handling |
| **Synthesizer** | agent-handoff, quality-gates, pattern-library, session-scoring |
| **Reviewer** | quality-gates, agent-handoff |
| **Challenger** | coaching-progressions, error-handling |
| **Thinker** | pattern-library |
| **Curator** | error-handling, agent-handoff, epistemic-hygiene |
| **Scout** | error-handling |
| **Reader / Scholar** | agent-handoff |
| **Evolver** | meta-reflection, session-scoring, harness-assumptions |

Dormant agents (Meeting, Librarian): dispatched only on explicit intent match. Contracts live in `agent-handoff.md`.

## Protocol Dependency Graph

```
orchestrator.md
  ├── agent-handoff.md (communication contracts)
  ├── quality-gates.md (checkpoints) → session-scoring.md (rubric)
  ├── error-handling.md (escalation + emotional)
  └── session-continuity.md (cross-session memory)

coaching-progressions.md (depth adaptation)
pattern-library.md (Moments, trade routes, recurring patterns)

epistemic-hygiene.md (validation-depth taxonomy) → wiki-schema.md (L4 format)
local-first-architecture.md (five-tier vault model)

session-log.md (process recording) → meta-reflection.md (system health)
harness-assumptions.md (model-era assumption registry)
```

Deferred specs (not currently load-bearing): `protocols/specs/`.
