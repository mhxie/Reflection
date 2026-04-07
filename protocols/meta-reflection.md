# Meta-Reflection Protocol

Reflect on the reflection process itself. This is how the system becomes self-aware of its own quality and evolves deliberately.

## When to Run

- After every 5th session (automatically triggered by session count)
- When session scores trend downward for 3+ sessions
- When the user explicitly asks "how is the system doing?"
- During Evolver runs

## The Meta-Reflection Process

### Step 1: Gather Session Data
Read all session outputs from the last 5-10 sessions in `zk/reflections/`:
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

## Bottleneck: [identified constraint]
## Prescribed Evolution: [specific action]
## Evolution Applied: [what was changed, or pending]
```

## The Double-Loop on the System

This is Double-Loop Learning applied to the reflection system itself:
- **Single-loop:** "How do we improve this session?" → adjust within existing framework
- **Double-loop:** "Are we asking the right kind of questions? Is our session structure right?" → question the framework itself

Don't just optimize within the current paradigm — periodically question the paradigm.
