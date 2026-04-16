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
6. Read `error-handling.md` — when to escalate vs. handle yourself (includes escalation rules)
7. Read `feedback-loops.md` — calibrate based on user signals
8. Read `cognitive-bias-detection.md` — watch for biases (yours and the user's)

### Producing output
9. Read `session-scoring.md` — score every session
10. Read `pattern-library.md` — recognize recurring patterns
11. Read `values-clarification.md` — when goals feel hollow

### After a session
12. Read `meta-reflection.md` — assess system health
13. Read `session-log.md` — emit the session process log

### During system evolution
14. Read `harness-assumptions.md` — check for stale model-era assumptions

## By Agent

| Agent | Must-read protocols |
|-------|-------------------|
| **Orchestrator** | orchestrator.md, quality-gates.md, error-handling.md, session-continuity.md, session-log.md |
| **Researcher** | agent-handoff.md, error-handling.md |
| **Synthesizer** | agent-handoff.md, quality-gates.md, pattern-library.md, session-scoring.md |
| **Reviewer** | quality-gates.md, agent-handoff.md, cognitive-bias-detection.md |
| **Challenger** | feedback-loops.md, cognitive-bias-detection.md, coaching-progressions.md, error-handling.md |
| **Thinker** | pattern-library.md |
| **Curator** | error-handling.md, agent-handoff.md, epistemic-hygiene.md |
| **Scout** | error-handling.md |
| **Reader** | agent-handoff.md |
| **Meeting** | agent-handoff.md |
| **Librarian** | feedback-loops.md |
| **Evolver** | meta-reflection.md, feedback-loops.md, session-scoring.md, harness-assumptions.md |

## Protocol Dependency Graph

```
orchestrator.md
  ├── agent-handoff.md (defines communication contracts)
  ├── quality-gates.md (defines checkpoints)
  │     └── session-scoring.md (scoring rubric used by gates)
  ├── error-handling.md (includes escalation rules and emotional escalation)
  └── session-continuity.md (cross-session memory)

coaching-progressions.md (adapts depth)
  └── feedback-loops.md (learns from signals)
       └── meta-reflection.md (system-level assessment)

pattern-library.md (recognizes patterns)
  ├── cognitive-bias-detection.md (specific pattern: biases)
  └── values-clarification.md (specific pattern: hollow goals)

epistemic-hygiene.md (validation-depth taxonomy)
  └── wiki-schema.md (L4 entry format, claim markers, anchors)

local-first-architecture.md (five-tier model, $ZK/ layout)

session-log.md (session process recording)
  └── meta-reflection.md (reads session logs for system health)

harness-assumptions.md (model-era assumption registry)
  └── evolver.md (checks during Observe phase)

contradiction-detection.md (4 strategies for surfacing contradictions)
```
