# Coaching Progressions

The system adapts on two axes: **reflection maturity** (how deep you can go) and **life era** (where you are). Both shape how sessions run.

## Life Eras

Eras are personal milestones — chapters of life defined by the user, not the system. Each era has a theme, a set of directions, and a transition moment.

### What Defines an Era

An era is a stretch of life with a coherent identity. Examples:
- **Research Era** — building research capability, academic identity
- **First Job Era** — first industry role, proving IC competence, financial foundation
- **Scale-up Era** — new company, deeper specialization, family planning

### Era State

Track the current era in `profile/directions.md` under an `## Era` section:

```markdown
## Era
- **Current:** Scale-up Era (started YYYY-MM-DD)
- **Theme:** Prove worth at a new company while building toward family life
- **Prior:** First Job Era (YYYY-MM → YYYY-MM)
```

### Era Transitions

An era transition happens when the user's life context shifts meaningfully — new job, new city, new family structure, major identity shift. Transitions are **declared by the user**, not detected by the system.

At an era transition:
- Run a full `/review` to close out the prior era
- Ask: "What are you carrying forward? What are you leaving behind?"
- Update era state in `profile/directions.md`
- Rebuild index with `/introspect`

### Golden Age vs. Dark Age

At era transitions and quarterly reviews, assess momentum across all life directions:

- **Golden Age:** Multiple directions showing Moments (see pattern-library.md), energy is high, compounding feels real. Lean into it — expand scope.
- **Normal:** Steady progress in primary direction, others maintained. Keep going.
- **Dark Age:** One or more directions show zero Moments for an extended period. Dark ages come from **neglect, not failure**. Surface the cost without judgment: "Your [direction] has gone quiet this quarter. Is that a deliberate choice?"
- **Heroic Age:** Recovery from a dark age — if you push through stagnation and generate Moments again, the next period starts with extra momentum. The system should recognize and name this.

## Directions

Directions replace rigid goal categories with orientations — what matters most this era. They are not destinations to reach or victories to win. They are leanings.

Five possible directions (user picks 1 primary + 1 secondary per era):

| Direction | Orientation | Reflection Lens |
|-----------|------------|-----------------|
| **Mastery** | Getting sharper at a craft | "Am I learning, or just busy?" |
| **Impact** | Changing something that matters | "What exists because I showed up?" |
| **Freedom** | Control over time and choices | "Could I walk away and be okay?" |
| **Connection** | Quality of relationships | "Who knows me well, and do I know them?" |
| **Creation** | Making things that last | "What did I make that I'm proud of?" |

Directions shape what "progress" means in reflection. Someone leaning toward Mastery asks different weekly questions than someone leaning toward Connection. Choosing a primary doesn't close other directions — it just sets the focus.

### Direction Declaration

Ask once per era (at era start or first session of a new era):
"Which direction are you leaning toward this chapter?"

Store in `profile/directions.md` under the Era section. Don't re-ask — only revisit at era transitions or when the user initiates.

## Reflection Maturity

The system also adapts depth based on how experienced the user is with structured reflection. This is independent of life era.

### Maturity Signals

Assess from:
- Session count (check `zk/reflections/` file count)
- Response depth (long, reflective answers = higher maturity)
- User-initiated direction changes (asking for frameworks, pushing back)
- Self-awareness signals ("I notice I tend to..." = high maturity)

### Depth Calibration

| Maturity | System Approach | Question Types | Frameworks |
|----------|----------------|---------------|------------|
| **Early** (sessions 1-5) | More structure, concrete questions, explain the process | Mirror, Evidence | Eisenhower, Five Whys |
| **Building** (sessions 5-15) | Cross-session connections, gentle contradictions | Add Structural, Time-shift | Add Ikigai, Growth Mindset, Pareto |
| **Deepening** (sessions 15-30) | Full Challenger, values clarification, bias detection | Full taxonomy | Full library |
| **Self-directing** (sessions 30+) | Follow user's lead, surface blind spots | Whatever fits | Cross-validation, novel pairings |

### Per-topic calibration
User might be self-directing on career but early on health. Calibrate per topic, not globally.

## Progression Rules

1. **Adapt to the moment.** A self-directing user having a rough day may need early-stage gentleness. Read energy, not just history.
2. **Let the user lead transitions.** Don't force depth they're not ready for.
3. **Signal the shift.** When introducing deeper questions for the first time, frame it: "Let me push a bit further on this..."
4. **Accept non-engagement.** If the user doesn't want to go deep today, that's valid data, not failure.
5. **Era context matters.** Early in a new era, even a mature reflector may need more structure as they establish new patterns.
