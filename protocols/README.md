# Protocols — Quick Reference

This is the entry point for all agents. When you need to know how to behave, start here.

## By Situation

### Starting a session
1. Read `orchestrator.md` — understand your role as hub
2. Read `session-continuity.md` — connect to previous sessions
3. Read `context-management.md` — budget your context window
4. Read `coaching-progressions.md` — adapt depth to user maturity

### During a session
5. Read `quality-gates.md` — check work before passing it on
6. Read `agent-handoff.md` — format your output for the next agent
7. Read `escalation.md` — when to escalate vs. handle yourself
8. Read `feedback-loops.md` — calibrate based on user signals
9. Read `cognitive-bias-detection.md` — watch for biases (yours and the user's)

### Producing output
10. Read `session-scoring.md` — score every session
11. Read `pattern-library.md` — recognize recurring patterns
12. Read `integration.md` — connect insights to action
13. Read `values-clarification.md` — when goals feel hollow

### After a session
14. Read `meta-reflection.md` — assess system health
15. Read `error-handling.md` — when things went wrong

## By Agent

| Agent | Must-read protocols |
|-------|-------------------|
| **Orchestrator** | orchestrator.md, quality-gates.md, escalation.md, session-continuity.md |
| **Researcher** | agent-handoff.md, error-handling.md, context-management.md |
| **Synthesizer** | agent-handoff.md, quality-gates.md, pattern-library.md, session-scoring.md |
| **Reviewer** | quality-gates.md, agent-handoff.md, cognitive-bias-detection.md |
| **Challenger** | feedback-loops.md, cognitive-bias-detection.md, coaching-progressions.md, escalation.md |
| **Thinker** | pattern-library.md, context-management.md |
| **Curator** | error-handling.md, agent-handoff.md |
| **Librarian** | context-management.md, feedback-loops.md |
| **Evolver** | meta-reflection.md, feedback-loops.md, session-scoring.md |

## Protocol Dependency Graph

```
orchestrator.md
  ├── agent-handoff.md (defines communication contracts)
  ├── quality-gates.md (defines checkpoints)
  │     └── session-scoring.md (scoring rubric used by gates)
  ├── escalation.md (when gates fail)
  ├── error-handling.md (when things break)
  └── session-continuity.md (cross-session memory)

coaching-progressions.md (adapts depth)
  └── feedback-loops.md (learns from signals)
       └── meta-reflection.md (system-level assessment)

pattern-library.md (recognizes patterns)
  ├── cognitive-bias-detection.md (specific pattern: biases)
  ├── values-clarification.md (specific pattern: hollow goals)
  └── integration.md (connects patterns to action)

context-management.md (standalone — token budgets)
```
