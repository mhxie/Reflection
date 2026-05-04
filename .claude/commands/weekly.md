# Weekly Review

> Also reachable via `/hi <natural language>` (e.g., `/hi weekly review`, `/hi this week`).
> See `harness/intents.toml` `[intents.weekly]` for the full pattern list. Both paths
> execute this same procedure.

Run a structured weekly review covering the past 7 days. Deeper than daily reflection, lighter than a full goal review.

Daily `/hi` does not run every day. `/weekly` is also the catch-all for any signals that didn't make it into a daily reflection — Apple Health, support pulse, dining, health-cadence checks, key events. Treat it as the weekly checkpoint, not just a synthesis of dailies.

## Run Cue

When to invoke:
- **Default**: weekly, on Sunday evening or Monday morning local time.
- **Soft cue / Hard floor**: the orchestrator surfaces a cue inside `/hi` based on weekly staleness. The authoritative thresholds and routing logic live with the cue surface, not duplicated here.
- **Manual**: user can invoke directly anytime.

## Prerequisites

1. Check if `profile/identity.md` exists. If not: "Run `/introspect` first to build your self-model." Stop.
2. Check `Last built:` date. If >7 days stale, warn and continue.

## Context Loading

1. **Read profile files:** `profile/identity.md` + `profile/directions.md`

2. **Read all reflections from the past 7 days** from `$OV/reflections/` directory.

3. **Read the past 7 daily notes from the vault:**
   - `Read $OV/daily-notes/<today>.md` through `Read $OV/daily-notes/<7-days-ago>.md` (7 local reads). For any file that is missing or empty, note it and continue — the user may not have written that day. Daily notes are user-authored; the system never writes to them.
   - Focus on themes, moods, accomplishments, and struggles.

4. **Search for recent activity in the vault:**
   - Build the recency window: `Bash: find "$OV"/daily-notes "$OV"/reflections "$OV"/gtd -type f -name "*.md" -mtime -7 2>/dev/null | sort`
   - Grep the recency window for progress markers: `Bash: find "$OV"/daily-notes "$OV"/reflections "$OV"/gtd -type f -name "*.md" -mtime -7 -print0 | xargs -0 grep -HnE "progress|进展" 2>/dev/null`. Using `find -print0 | xargs -0` is safe when `find` returns nothing (xargs with no input simply exits); never use `grep $(find ...)`, which silently scans the current directory on empty input.

## The Weekly Review Framework

### 1. Apple Health Snapshot
Apple Health is not in the local mirror — ask the user to paste this week's key metrics. Prompt explicitly so the user knows what to look up; do not skip if they forget. Default fields (Chinese for matching the user's reading style):

- 睡眠: 平均时长 + 平均入睡时间 (sleep drift 是标准跟踪项)
- 步数: 每日均值 + 趋势 (上 / 持平 / 下)
- 锻炼: Exercise minutes 周总 + Active energy 周总
- 心血管: 静息心率 (RHR) + HRV (avg)
- (可选) VO2 Max / Stand hours / Mindful minutes / 体重 (若 Apple Health 自动同步)

Suggested phrasing: "翻一下 Apple Health 这周的 summary, 把以下数据贴过来 (没有的填 -):". Accept either pasted numbers or screenshot description. Do not invent data if user skips; mark fields as "未提供" in the output instead.

The data feeds directly into Energy Audit (sleep / RHR / HRV → recovery; steps / Exercise → activity floor) and Goal Progress #energy.

### 2. Missed Daily Signals (Backfill)

**Do not invent data. If user doesn't recall, mark `(none surfaced)` and move on.** Backfill is best-effort.

Daily `/hi` may not run every day. Detect missing days from the past 7 by checking `$OV/reflections/`:

```
# macOS/BSD date syntax; Linux: replace `date -v-${d}d +%Y-%m-%d` with `date -d "${d} days ago" +%Y-%m-%d`
Bash: for d in $(seq 0 6); do date_str=$(date -v-${d}d +%Y-%m-%d); ls "$OV"/reflections/${date_str}-reflection*.md 2>/dev/null > /dev/null || echo "missing: $date_str"; done
```

Read the daily notes for any missing days (`$OV/daily-notes/<date>.md`) so context is loaded, then prompt the user with 3 light **week-level** questions (do not force per-day reconstruction):

1. **Support pulse (week)**: 这 7 天里, 有哪些有意义的互动 (1:1 / 家人 / 朋友 / 同事) 没记到 daily reflection 里? 谁? 什么类型 (E / I / Inf / A)? 有没有新连接?
2. **Dining (week)**: 这 7 天有去新餐厅 / 重访旧餐厅没记到 dining log 的吗? (餐厅 + **就餐日期 YYYY-MM-DD** + 评分 + **再去? Y/N/Maybe** + 健康 flag + 必点 + Credit used). Backfill spans multiple days, so the Date column must hold the actual visit date — not the session date — otherwise the date-keyed dining log and credit-cycle tracking break. 评分 + 再去 are mandatory per the `/hi` Dining Pulse rule; do not append a row without both.
3. **Signals**: 这 7 天有哪些值得标记的事 (wins / drains / health observations / 决策 / 突发) 没进入 reflection 流?

Captured items fold into `## Missed-Day Backfill` (Support pulse / Dining / Signals sub-bullets); significant drains or wins may also surface in `## Energy Map`. Dining items additionally append to the dining log per the `/hi` Dining Pulse rule.

### 3. Health Follow-Up Due

Cross-check health-related cadences against current date. Reminder-only — actual booking lives outside the reflection flow.

Default cadences (read `$OV/health/metrics.md` for last-drawn dates and `directions.md` #energy for declared but unstarted items):

| Category | Default cadence | Where specifics live (read at runtime) |
|---|---|---|
| Lipid panel | Quarterly if any marker out of range; yearly otherwise | `$OV/health/metrics.md` |
| Vitamin / mineral panel | 90 days post-supplement-start, then quarterly. Markers below reference range fast-track (next available draw, not deferred) | `$OV/health/metrics.md` |
| Body composition (DEXA / scale) | 6-12 months | `$OV/health/metrics.md` |
| Endocrine surveillance (thyroid, nodules, etc) | 6-12 months when any finding is flagged | `$OV/health/metrics.md` |
| Planned interventions in `profile/directions.md` #energy | Per-intervention cadence (read at runtime) | `profile/directions.md` #energy |
| Annual physical / PCP | Yearly | runtime decision |

Generic categories only — do not hardcode user-specific lab values, conditions, or thresholds in this command file. The orchestrator reads `$OV/health/metrics.md` (gitignored, lives only in the local symlinked vault) at runtime to compute actual due-dates and severity. This is critical for privacy: the command file is committed to the repo, but the user's medical specifics never are.

For each item:
- **Due within 4 weeks** → surface as **Next Week → Start** candidate ("约 [item] 复查")
- **Overdue (past default cadence)** → surface as **Continue → schedule the appointment**, with honest gap note ("lipid 复查 已经晚 X 天")
- **Nothing due** → write `(no follow-up due this week)` and move on

This section catches what daily reflection cannot: daily focus is per-day events, not multi-month medical cadences. Long-time-constant indicators get systematically stale unless surfaced here.

### 4. Energy Audit
Map the week's energy:
- **High-energy days:** What were you doing? What made them good?
- **Low-energy days:** What drained you? Was it avoidable?
- **Pattern:** Is there a day-of-week or activity pattern?

### 5. Win Recognition
Identify 3 wins from the week, however small:
- What went well? (cite specific daily notes)
- What did you complete or make progress on?
- What did you learn?

### 6. Honest Assessment
For each goal category (#capacity, #learning, #identity, #energy):
- Did you make progress this week? Evidence?
- Did you avoid something? Why?
- What surprised you?

### 7. Attention Audit
Where did your attention actually go vs. where you wanted it to go?
- Apply Pareto: What 20% of activities produced 80% of your week's value?
- What consumed time but produced little?

### 8. Next Week's Intention
Based on the review:
- **One thing to continue:** [What's working]
- **One thing to start:** [What's been neglected]
- **One thing to stop:** [What's draining without value]

## Output

**File:** `$OV/reflections/YYYY-MM-DD-weekly.md`

```markdown
# Weekly Review — YYYY-MM-DD (Week of MM/DD - MM/DD)

## Apple Health
- 睡眠: avg <X>h, 入睡 avg <HH:MM>
- 步数: avg <N>/day, 趋势 <up/flat/down>
- 锻炼: <X> min Exercise, <X> kcal Active
- 心血管: RHR <X> bpm, HRV <X> ms
- 备注: <one-line interpretation: e.g., "sleep 比上周早 30 min" / "RHR 升 5 bpm 提示 recovery 不足">
- 未提供: <fields user couldn't pull>

## Missed-Day Backfill
- Days without `/hi`: <list of YYYY-MM-DD>
- **Support pulse (week)**: <people / type / new connection / direction>
- **Dining (week)**: <restaurants / scores / 健康 flags / 必点>
- **Signals**: <wins / drains / health obs / decisions surfaced retroactively>
- (omit if user surfaced nothing)

## Health Follow-Up Due
- **Due ≤4 weeks**: <items + appointment names>
- **Overdue**: <items + 晚 X 天>
- **No action**: <items still in cadence>
- Status of `directions.md` #energy planned-but-unstarted (e.g., allergy shots): <not started / scheduled / launched>

## Energy Map
- High: [days + activities]
- Low: [days + activities]
- Pattern: [observation]

## Wins
1. [Win] — [[Source Note]]
2. [Win] — [[Source Note]]
3. [Win] — [[Source Note]]

## Goal Progress
### #capacity
- [status + evidence]
### #learning
- [status + evidence]
### #identity
- [status + evidence]
### #energy
- [status + evidence]

## Attention Audit
- Time well spent: [activities]
- Time wasted: [activities]
- Pareto insight: [the 20% that mattered]

## Next Week
- Continue: [what's working]
- Start: [what's been neglected]
- Stop: [what's draining]

## Notes Referenced
[List of all [[Note Title]] links]

## Session Meta
- User engagement: high / medium / low
- Surprise factor: yes / no
```

## Session Log

After writing the weekly review file, emit a session log:
1. `Bash: uv run scripts/session_log.py --type weekly --duration <minutes>`
2. `Edit` the created file to populate sections from session data (agents dispatched, searches, questions, frameworks, anomalies). The canonical fill-in guide lives in `protocols/session-log.md` § "Section Guidance". Leave empty sections with headers only. If the write fails, warn and continue.

## Wrap Up

The weekly review file at `$OV/reflections/YYYY-MM-DD-weekly.md` is the durable session output. Daily notes are user-authored only; nothing is written back to them. Tell the user the weekly review has been saved and where to find it.
