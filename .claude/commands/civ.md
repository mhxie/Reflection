# Civilization Report

Read-only life dashboard. Single-pass render from vault signals. No new state files.

## Architecture

Three conceptual layers, inspired by Civ 6:

```
Resources (7 inputs)  →  Civilizations (7 conversion engines)  →  Terminal Values (5 outputs)
时气金识缘心誉           Health..Experience                       意义 成就 幸福 自由 健康
```

**Resources** are what you spend. **Civs** are where you invest them. **Terminal Values** are what you're optimizing for. The dashboard shows all three and whether your resource allocation is actually producing terminal value.

## Resources (7 layers)

Spendable, tradeable inputs. Lower layers supply upper ones. From the user's resource framework note: 金钱, 时间, 能量, 技能 are Tier-1 instrumental; 声誉/信任 is Tier-2. 连接 is instrumental (not terminal), pending Test 1.

| Layer | Token | What it is | Renewable | Compounds | Vault signal |
|---|---|---|---|---|---|
| 0 | **时 Time** | Hours/week allocated | No | No | Not directly tracked; inferred from reflection density per civ |
| 1 | **气 Energy** | Physical + mental reserves | Yes (rest, exercise) | Yes (health habits) | Weight plan progress, sleep signal, exercise mentions |
| 2 | **金 Money** | Financial position | Yes (income) | Yes (investment) | Most recent NW figure from financial plan/reflection |
| 3 | **识 Skills/Knowledge** | Human capital | Yes | Strongly | Wiki count + reading sessions (30d) |
| 4 | **缘 Social Capital** | Relationship goodwill, network | Yes (fragile) | Yes (network effects) | Interaction count estimate (30d) + DL0 from PRM |
| 5 | **心 PsyCap** | Self-efficacy + resilience + hope + optimism (HERO) | Yes (practice) | Yes (mutual reinforcement) | Qualitative: from reflection tone, self-knowledge entries |
| 6 | **誉 Reputation/Optionality** | Trust, credibility, future options | Slowest | Yes | Ownership areas, publications, credentials, role level |

### Stock Sourcing

Each stock from a **specific vault artifact** with a known date. If >30 days stale, flag and prompt for update.

- **金**: Most recent explicit NW/asset figure from financial plan or reflection. Report value + source date.
- **气**: Weight from plan file or daily notes. Sleep pattern (regular/drifting/unknown). Exercise frequency estimate.
- **识**: Wiki count (`ls "$OV"/wiki/*.md | wc -l`) + reading sessions in 30d. Note bulk-sync caveat.
- **缘**: Estimate: distinct social interactions in daily notes + reflections (30d). DL0 count from PRM.
- **心**: Qualitative read from recent reflections: evidence of self-efficacy, resilience, hope, optimism. Report as `high/stable/fragile/unknown`.
- **誉**: Role level + tenure + ownership areas + publications/reviews. From profile + career reflections.
- **时**: Not stockpiled; shown as allocation % across civs based on reflection density.

### Trade Rules (from the user's resource framework note)

- **Instrumental ↔ instrumental OK**: 金 ↔ 时 (buy services), 识 ↔ 时 (learning costs time), 缘 ↔ 时 (invest in people)
- **Never trade terminal for instrumental**: no 健康 for productivity; no 意义 for 金钱 premium; no 自由 for external validation
- **Irreversibility hierarchy**: 健康 (post-60 irreversible) > 父母陪伴 (finite quota) > 备孕 window > relationship depth before transitions > green card process

## Terminal Values (5 outputs)

From the user's resource framework note (provisional, 2026-04-19). The optimization target.

| # | Value | Current weight | Measured by |
|---|---|---|---|
| 1 | **意义 Meaning** | Highest | Identity coherence: are you building what matters to you? Evidence: atelier, systems research identity, "consumer vs creator" |
| 2 | **成就感 Achievement** | Very high (coupled with 意义) | Craft mastery, not external validation. Evidence: ownership, wiki compound, "bugs others would miss" |
| 3 | **幸福感 Wellbeing** | High | Eudaimonic-heavy: relational depth + intellectual engagement + exploration. Evidence: reading sessions, social interactions, flow states |
| 4 | **自由 Autonomy** | High | Optionality, self-determination. Evidence: career mobility, financial runway, epistemic sovereignty |
| 5 | **健康/长寿 Health** | Medium explicit, high instrumental | Physical foundation. Evidence: weight progress, sleep, exercise, medical actions |

**连接 (Connection)** is instrumental (Tier-1), not terminal. It supports 幸福感 + some 意义. Three consistency tests pending (see the user's resource framework note).

**Stage weighting** (Rule 4): the user's current life stage biases the terminal-value weighting per `profile/identity.md`. The Researcher reads identity.md for the actual stage label, age range, and weighting; re-evaluate at major stage transitions.

### Terminal Value Signals

The Researcher assesses each terminal value qualitatively from recent reflections:

- **意义**: Is the user doing identity-coherent work? Building, not just consuming? Evidence of craft, creation, or "constraint creates meaning" moments.
- **成就感**: Craft milestones, ownership earned, technical depth built. Not promotions or titles.
- **幸福感**: Flow states, intellectual engagement, relational warmth, exploration. Diverse sources, not monocultural.
- **自由**: Options expanding or contracting? Job lock, financial constraints, immigration gates.
- **健康/长寿**: Trend toward or away from targets. Sleep, weight, medical actions.

Report each as: `rising` | `stable` | `declining` | `neglected` | `unknown`

## Civilizations (7 conversion engines)

Civs convert resources into terminal values. Each civ has a primary terminal output.

| Civ | Layer | Primary terminal output | Key resources consumed |
|---|---|---|---|
| **Health** | Foundation | 健康/长寿 | 时, 气, 金 (medical) |
| **Finance** | Foundation | 自由 (optionality) | 时, 金, 识 (financial literacy) |
| **Immigration** | Enabler | 自由 (gates mobility, housing, family) | 时, 金 (legal fees), 誉 (credentials for EB-1B) |
| **Relationships** | Enabler | 幸福感 (instrumental 连接 → terminal 幸福) | 时, 气, 缘 |
| **Career** | Expression | 成就感 + 意义 | 时, 气, 识, 缘, 誉 |
| **Learning** | Expression | 意义 + 成就感 | 时, 气, 识 |
| **Experience** | Expression | 幸福感 + 意义 (memories) | 时, 金, 气 |

## Civ 6 Mechanics

### Governors (♛/○)

**Governed** (♛) = has a dedicated plan/system artifact. **Ungoverned** (○) = no infrastructure. The Researcher checks for plan files referenced in directions.md or reflections.

### Ages (per civ)

| Age | Condition | Symbol |
|---|---|---|
| **Golden** | Accelerating + at least 1 wonder in window | `★` |
| **Normal** | Steady, or accelerating without wonder | `·` |
| **Dark** | Coasting/declining/blocked, or declared goal with 0 activity | `◆` |
| **Heroic** | Was Dark last period, now accelerating with wonder | `✦` |

### Era Score

Self-estimated composite percentile vs peer cohort (read the user's peer-cohort definition from `profile/identity.md`, set during `/introspect`). Not competition; a self-check on whether you're living up to your own potential in context.

| Tier | Percentile | Era | Meaning |
|---|---|---|---|
| **Legendary** | Top 1% | Heroic `✦` | Across-the-board excellence; rare and unsustainable long-term |
| **Elite** | Top 5% | Golden `★` | Strong in most areas; firing on most cylinders |
| **Strong** | Top 20% | Normal+ `·` | Solid foundation; clear growth trajectory |
| **Average** | Top 50% | Normal `·` | Holding ground; no major wins or losses |
| **Below** | Under 50% | Dark `◆` | Falling behind your own baseline or peer trajectory |

**Anchoring with hard data where available:**
- 金: Use actual percentile data (NW percentile from the user's percentile data note, income from tax returns)
- 誉: Role level + tenure vs age cohort; publication count for field
- 气: BMI/weight vs age-cohort norms; sleep quality vs guidelines
- 识/缘/心: Self-assessed; no external benchmark. Update estimate when running `/civ`.

**The Researcher proposes a tier** based on: resource stocks, terminal value trends, civ ages, wonders, emergencies, and 知行 alignment. The user confirms or overrides. The system never assigns a tier silently.

**Signals that push tier up:**
- Multiple terminal values rising
- Wonders completed; governors established
- Emergencies resolved before deadline
- Dedication alignment (focus matches activity)

**Signals that push tier down:**
- Terminal values declining or neglected
- Ungoverned Dark civs
- Emergencies missed; stale goals accumulating
- 知行 gap (declared priority, 0 activity)

### Emergencies (⚡)

Deadlines <90 days from today. Scan directions.md and reflections for dates + deadline language. Report: `description (Nd) → affected civs`

### Dedications

Quarterly focus = current Dedication. Aligned activity is a positive era signal. 知行合一 check evaluates adherence.

## Prerequisites

1. `profile/identity.md` missing → "Run `/introspect` first." Stop.
2. `profile/directions.md` missing → "Run `/introspect` first." Stop.
3. `Last built:` >7 days → warn, continue.

## Dispatch

Single pass, two dispatches:
1. **Researcher**: gathers signals, reads stocks, computes era score, assesses terminal values.
2. **Synthesizer**: renders compact tree.

## Data Contract

All reads local. No hardcoded regex; derive terms from profile files at runtime.

### Researcher collects:

1. **Profile context**: era, goals, completed, stale, insights, employer, partner, key people.
2. **Term derivation**: per civ, extract nouns from goal lines, build ephemeral regex.
3. **Resource stocks**: read each of 7 tokens per Stock Sourcing rules. Flag stale.
4. **Per-civ signals**: goal inventory, reflection scan (30d/60d), governor check, age classification.
5. **Terminal value assessment**: qualitative read of each of 5 values from recent reflections.
6. **Emergencies**: deadlines <90d from today.
7. **Era score**: propose a tier (Legendary/Elite/Strong/Average/Below) per the Era Score percentile table; list signals_up and signals_down from the bullet lists in that section. The user confirms or overrides the proposed tier.
8. **Constraints**: directed edges between civs. Immigration as strategic resource.
9. **Wonders** (60d): 3-5 accomplishments from strikethrough, completed goals, milestone language.
10. **知行合一**: declared focus vs actual activity distribution.

### Handoff Format

```
era: { current, theme, dedication, phase_context }

resources:
  时: { allocation: { civ: N% per civ based on reflection density } }
  气: { weight, sleep, exercise_freq, source, as_of, stale }
  金: { value, source, as_of, stale }
  识: { wiki, reading_sessions_30d, bulk_synced }
  缘: { interactions_30d_est, dl0, prm_date, stale }
  心: { level: high/stable/fragile/unknown, evidence }
  誉: { level, day, ownership_areas, publications }

terminal_values:
  意义: { status: rising/stable/declining/neglected, evidence }
  成就感: { status, evidence }
  幸福感: { status, evidence }
  自由: { status, evidence }
  健康: { status, evidence }

civilizations:
  [per civ]: { layer, age, governor, key_evidence (2-3 lines), wins, terminal_output }

strategic_resource:
  immigration: { status, constraints_on, evidence }

emergencies: [{ description, deadline, days_remaining, affected_civs, action_evidence }]

era_score: { proposed_tier, reasoning (2-3 sentences), signals_up: [...], signals_down: [...] }

constraints: [directed edges]
wonders: [...]
alignment: { dedication, top_alignment, top_gap, undeclared }
gaps: [...]
```

## Synthesizer: Compact Tree

~25 lines. Orchestrator handles drill-down from brief in context.

```
## Civ Report (YYYY-MM-DD)
_Era · Phase · Dedication: [focus]_

Resources:  金 $NNK (MM-DD)  气 NNkg·[sleep]  识 Nw·Nr  缘 ~Ni·DL0:N  心 [level]  誉 LN·Nown
[stale flags if any]

Terminal Values:  意义 [↑→↓]  成就 [↑→↓]  幸福 [↑→↓]  自由 [↑→↓]  健康 [↑→↓]

Foundation
├─ Health       [age][gov]  [≤8 words]
└─ Finance      [age][gov]  [≤8 words]

Enabler
├─ Immigration  [age][gov]  [≤8 words]  ⊳ gates: [list]
└─ Relationships [age][gov]  [≤8 words]

Expression
├─ Career       [age][gov]  [≤8 words]  → 成就+意义
├─ Learning     [age][gov]  [≤8 words]  → 意义+成就
└─ Experience   [age][gov]  [≤8 words]  → 幸福+意义

⚡ [emergency (Nd)] · [emergency (Nd)]
Era: [proposed tier] (Top N%). [1-line reasoning]. Confirm? [highest-leverage action to tier up]
知行: [dedication] → [aligned] | gap: [gap]
Next: [foundation] → [enabler] → [expression]

> Expand: civ name, resource, terminal value, "era score", "constraints", "wonders"
```

### Drill-Down Templates

**Civ:**
```
### [Civ] [age][gov] ([layer]) → [terminal output]
Goals: [list]
Evidence: [2-3 sentences citing [[Sources]]]
Wins: [list or "none"]
Governor: [plan name] or "none (signal_up if built)"
Resources consumed: [which tokens]
Terminal output: [which values, rising/stable/declining]
Next: [one action]
```

**Resource:**
```
### [Token] ([Chinese name])
Stock: [value] (as of MM-DD) [stale flag if applicable]
Trades: [what this resource can be exchanged for]
Spending on: [current civ allocations]
Bottleneck: [what limits this resource]
```

**Terminal Value:**
```
### [Value] ([Chinese])
Status: [rising/stable/declining/neglected]
Fed by: [which civs produce this]
Evidence: [2-3 sentences from recent reflections]
Risk: [what would cause decline]
```

**Era Score:** Proposed tier with reasoning, signals_up and signals_down lists, and "to reach next tier: [specific actions]"

Other sections (constraints, wonders, full 知行) on request. Each drill-down ≤15 lines.

## Style

- No em dashes. Colons, semicolons, parentheses, or restructure.
- No H1. Start with `##`.
- Citations (`[[Title]]`) in drill-downs only.
- Default English. Chinese for token/value names and natural expressions.
- No vibes-based scores. Stocks are grounded in artifacts; terminal values in reflection evidence.

## Frequency

Ad hoc. Identical output on unchanged vault.

## Evolution

Persistent era score ledger and historical snapshots are out of scope. If demand emerges, evolve toward `<paths.civ>/` state directory. The 3 pending consistency tests in the user's resource framework note may change the terminal value structure; the dashboard adapts when those resolve.
