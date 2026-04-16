# Meta-Reflection Protocol

Reflect on the reflection process itself. This is how the system becomes self-aware of its own quality and evolves deliberately.

## When to Run

- After every 5th session (automatically triggered by session count)
- When session scores trend downward for 3+ sessions
- When the user explicitly asks "how is the system doing?"
- During Evolver runs

## The Meta-Reflection Process

### Step 1: Gather Session Data
Read session logs from the last 5-10 sessions in `zk/sessions/`:
- Agent dispatch patterns (which agents run, how many turns they use)
- Search effectiveness (hit rates, useful-signal rates from Search Log)
- Gate pass rates (from Gate Results)
- Question landing rates (from Questions & Engagement)
- Framework fit scores (from Frameworks Applied)
- Anomaly frequency and types
- Harness assumptions exercised

Also read reflection outputs from `zk/reflections/`:
- Score cards (overall scores, per-dimension scores)
- Session meta (engagement levels, questions that landed)
- Patterns identified
- Frameworks used

### Step 2: System Health Assessment

| Dimension | Health Check |
|-----------|-------------|
| **Research Quality** | Are searches returning relevant results? Gap frequency? |
| **Synthesis Depth** | What insight levels are being achieved? (Summary vs. Implication) |
| **Question Quality** | Are Challenger's questions getting engaged responses? |
| **Framework Fit** | Are frameworks being applied specifically or generically? |
| **Continuity** | Are sessions connecting to each other? |
| **User Engagement** | Are responses getting longer/shorter? More/less thoughtful? |
| **Note Coverage** | Are we surfacing notes from across the archive or just recent ones? |
| **Epistemic Independence** | Is the ratio of AI-tagged to user-written content in daily notes shifting? Are AI write-backs becoming the primary record? |
| **Search Effectiveness** | Are semantic.py queries returning useful results? Hit rate trend across sessions? |
| **Agent Utilization** | Are all agents being used? Any chronically idle? Any over-dispatched? |
| **Gate Health** | What percentage of sessions pass Gate 3 on first try? Revision loop frequency? |

### Step 3: Identify System Bottleneck

Apply Theory of Constraints to the system itself:
- What is the ONE thing limiting session quality right now?
- Is it search quality? Synthesis depth? Question relevance? Framework selection?
- Focus improvement on the bottleneck, not everything at once.

### Step 4: Prescribe Evolution

Based on the bottleneck:

| Bottleneck | Evolution Target | Action |
|-----------|-----------------|--------|
| Weak search results | Researcher prompts | Improve query patterns |
| Generic synthesis | Synthesizer patterns | Add new insight patterns |
| Questions not landing | Challenger taxonomy | Adjust question types |
| Frameworks feel forced | Thinker selection | Improve selection criteria |
| Sessions don't connect | Continuity protocol | Strengthen reading chain |
| Low engagement | Coaching style | Adjust tone in CLAUDE.md |
| Stale index | Index command | Add incremental refresh |

### Step 5: Document & Track

Write a meta-reflection report:

```markdown
# Meta-Reflection — YYYY-MM-DD

## Sessions Reviewed: N (date range)

## System Health
| Dimension | Score | Trend | Notes |
|-----------|-------|-------|-------|
| Research | X/10 | ↑↓→ | |
| Synthesis | X/10 | ↑↓→ | |
| Questions | X/10 | ↑↓→ | |
| Frameworks | X/10 | ↑↓→ | |
| Continuity | X/10 | ↑↓→ | |
| Engagement | X/10 | ↑↓→ | |
| Search Effectiveness | X/10 | ↑↓→ | |
| Agent Utilization | X/10 | ↑↓→ | |
| Gate Health | X/10 | ↑↓→ | |

## Bottleneck: [identified constraint]
## Prescribed Evolution: [specific action]
## Evolution Applied: [what was changed, or pending]
```

## Step 6: Governing Variables Audit (Double-Loop)

Single-loop asks "how do we improve this session?" Double-loop asks "are we measuring the right things and questioning the right assumptions?" Every meta-reflection must answer these three questions to prevent the system from optimizing confidently in the wrong direction.

1. Rubric validity: Is the scoring rubric measuring what matters? Read the last 5 session metas. Are high-scoring sessions actually the ones the user found most valuable? If scores and user engagement diverge, the rubric needs recalibration before any other evolution.
2. Ontology completeness: Were there any session anomalies that didn't fit the symptom-source table in evolver.md? If yes, the table needs updating before any other evolution, because unclassifiable failures repeat silently.
3. Complexity audit: Count protocols, agents, frameworks. Compare to session count. If protocols exceed 3x session count, trigger a pruning review before any additive changes, because the system's default failure mode is monotonic growth.
