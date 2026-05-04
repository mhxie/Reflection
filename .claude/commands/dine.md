## Purpose

Two intents (auto-detected from args):
- **A. Restaurant Recommendation** (default): pick 3 restaurant candidates based on user-supplied context, historical preferences, and credit-burn opportunities. Read-only on catalog docs; new captures route through `/reflect` Dining Pulse.
- **B. Workplace Catering Tracker**: parse a weekly catering PDF dropped into `$OV/<slug>/catering/`, choose health-aware picks for the user's attendance days, and surface a confirmed table for the user to record themselves (the system does not write to daily notes).

## Quick start

Intent A examples:
- `/dine` → ask all context
- `/dine 工作日午餐` → use as scene hint, ask remaining
- `/dine 朋友 4 人 川菜 dinner` → use as filters, ask remaining
- `/dine SF burn credit` → location SF + flag credit-burn priority

Intent B examples (first arg = workplace slug; the folder `$OV/<slug>/catering/` must exist; personal policy lives in gitignored `profile/diet.md`):
- `/dine <slug>` → find latest PDF in `$OV/<slug>/catering/` covering this week, pick per `profile/diet.md` attendance pattern
- `/dine <slug> <pdf-path>` → explicit PDF
- `/dine <slug> all` → all 5 weekdays (override)
- `/dine <slug> M/T/Th` → custom attendance set (override; any day-code combination works)

If args present, parse them as initial filters; only ask for slots not derivable.

## Step 0: Intent detection

Parse args. Route to **Intent B** if any of:
- First arg matches an existing folder `$OV/<arg>/catering/` (workplace slug)
- Any arg is a `.pdf` path under a `$OV/*/catering/` folder
- Args contain the literal token `catering`

Otherwise route to **Intent A** (continue to Step 1 below).

For Intent B, jump to the "Intent B: Workplace Catering Tracker" section near the bottom and skip Steps 1-5.

## Step 1: Gather context

For missing slots, ask via `AskUserQuestion` or sequential 1-line prompts (whichever fits faster). Required slots first; optional slots only if useful.

| Slot | Options | Required |
|---|---|---|
| **Location** | Bay Area / SF / Peninsula / South Bay / East Bay / LA / NYC / Other | Y |
| **Party** | Solo / Partner / Family (N) / Friends (N) / Mixed work | Y |
| **Meal** | Lunch / Dinner / Brunch / Late night | Y |
| **Time budget** | Quick (<30min) / Standard (1-2h) / Leisurely (2h+) | Y |
| Mood / cuisine | Surprise / 中餐 / 不要中餐 / 重辣 / 清淡 / Comfort / 探索新 / Special occasion / 老人友好 | N (default any) |
| **Health filter** | options enumerated in `profile/diet.md` ("Health filter input options" section) plus `no preference` | N (default no preference) |
| Budget cap | $20 / $50 / $100 / $150+ / no cap | N |
| Avoid recent | Last 30 / 60 / 90 days | N (default 30) |

## Step 2: Load data (parallel)

The user's vault holds these catalogs under `$OV/travel/` and `$OV/finance/`. Discover the actual filenames via `Grep` on those directories at runtime; do not hardcode private filenames here.

- Regional dining catalog (rotation + Michelin wishlist + 场景索引), under `$OV/travel/`
- Dining log (history with 评分 + 再去 + recency), under `$OV/travel/`
- Credit-perks dining catalog (Cycle Tracking + city catalogs), under `$OV/travel/`
- Perks ledger (current cycle credit status, for burn signal), under `$OV/finance/`
- Restaurant gift cards (prepaid balances per restaurant, for soft "use it" signal), under `$OV/finance/`
- For LA / NYC / other city: use the credit-perks catalog city section + the corresponding city Michelin guide under `$OV/archive/practical/travel/`

**Missing-file fallback:** if any of these is absent, skip it silently and note the gap in the closing line ("scored without [missing source]"). The recommendation still produces; the user can decide whether to recreate the catalog.

## Step 3: Filter + score

**Hard filters** (eliminate non-matches):
- Location matches user's region
- Cuisine NOT in avoid list
- Estimated price ≤ budget cap (allow 20% margin)
- Drive time fits time budget (heuristic: 🚗 count × 15min one-way)
- For Quick lunch: ⌛ ≤ 1
- For "Special occasion": Michelin OR Exclusive Tables only
- Skip restaurants visited within `avoid recent` window (from the dining log)

**Soft scoring** (rank candidates):
| Factor | Score |
|---|---|
| Catalog 评 (legacy field) = 3 | +3 |
| Catalog 评 = 2 | +2 |
| Catalog 评 = 1 | +1 |
| Log 评分 avg (last 3 visits) ≥ 8 | +5 |
| Log avg 6-7 | +2 |
| Log avg ≤ 5 | -3 |
| 再去 = Y in last entry | +2 |
| 再去 = N in last entry | -5 (effectively eliminate unless strong override) |
| 场景索引 match (regional catalog) | +3 |
| Last visit 31-90d ago | 0 |
| Last visit > 90d (rusty miss) | +1 |
| Never visited + mood = "Surprise" or "探索" | +2 |
| **Credit-burn priority** (Exclusive Tables restaurant + relevant cycle has unused credit AND ≤ 60d to deadline) | **+5** |
| Michelin star match + mood = "Special occasion" | +4 |
| Old-favorite revisit (rotation 评 ≥ 2 + last visit > 60d) | +2 |
| **Health filter active** | apply scoring rules from `profile/diet.md` "Health-filter scoring rules" section (recent-visit penalties, clean-style bonuses, cumulative-load adjustments) |

## Step 4: Output

Top 3 candidates as a table:

```markdown
| # | 餐厅 | 类型 | $ | 距离·等待 | Why | Credit signal |
|---|---|---|---|---|---|---|
| 1 | <restaurant-A> | <cuisine> | <$range> | <distance·wait> | <reason from catalog/log: 评 N + scene fit + recency> | n/a |
| 2 | <restaurant-B> | <cuisine> ⭐ | <$range> | <distance·wait> | <reason: Michelin tier + last log rating + want-revisit>; **<credit-card> <perk-program> <half> deadline <MM/DD> ($<amount>)** | 🔥 burn |
| 3 | <restaurant-C> | <cuisine> ⭐ | <$range> | <distance·wait> | <reason: novelty + Michelin tier + perk-eligible>; <perk-program> 候选 | <credit-card> <half> ✓ available |
```

Brief reasoning paragraph (2-3 lines) below the table:
- Mention the top filter constraints applied
- Flag any credit-burn 紧迫性 in plain text
- If filter returned <3 candidates, note relaxation taken (e.g., "loosened distance to 🚗🚗")

## Step 5: Close

End with one line:
> "选哪个? (回 1/2/3) 我帮你 OpenTable / Resy 查时段, 或者 /dine + 新约束 重排"

Do NOT auto-book; just surface candidates.

## Intent B: Workplace Catering Tracker

### B.1 Resolve PDF

- If an arg is a `.pdf` path → use it directly.
- Else: list `"$OV"/<slug>/catering/*.pdf`, pick the one whose filename date range covers the current calendar week. Typical filename pattern: `<Workplace> Catering_<Mon> <DD>-<Mon> <DD>.pdf`. If multiple match (e.g., manual override), prefer the most recent `mtime`.
- Optional date arg `YYYY-MM-DD` shifts the target week (Mon of that week).
- 0 matches: report `本周菜单还没传到 $OV/<slug>/catering/` and exit cleanly.

### B.2 Parse menu

Read the PDF (`Read` tool). Extract per-day sections (Mon/Tue/Wed/Thu/Fri). Each day has a theme + items + dietary tags (`v` / `vg` / `mwgci`).

### B.3 Determine attendance days

Read attendance pattern from `profile/diet.md` (the section matching the resolved `<slug>`, key: `Attendance days`). Override via the second CLI arg:
- `all` → all 5 weekdays present in the PDF
- `M/T/Th`, `T/Th`, `W/F`, etc. → custom set (case-insensitive day codes; any combination)

If `profile/diet.md` is absent or has no entry for `<slug>` → ask the user once, do not assume a default. Map each chosen day code to an absolute date based on the resolved week.

### B.4 Pick per day (reuse Step 3 health-filter logic)

Read **dietary picking priorities** and **flag taxonomy** from `profile/diet.md` (the `<slug>` section). Apply the policy verbatim — do not bake personal preferences into this committed file.

Generic fallback when `profile/diet.md` is absent: choose ONE protein + 1-2 veg sides per day, no specific oil/protein bias, and ask the user to confirm the picks before presenting.

The skill itself enforces only the structural shape (one row per attendance day, columns: protein + veg + sauce-note + flag). The semantic content is policy from the private file.

### B.5 Preview

Show table (one row per attendance day; values fill from B.4):

```markdown
| Date | Day | Theme | Pick | Flag |
|---|---|---|---|---|
| YYYY-MM-DD | <day> | <menu theme> | <protein> + <veg sides> + <sauce/dressing note> | <flag from profile/diet.md taxonomy> |
```

Add a 1-2 line cross-day note if `profile/diet.md` defines cross-day rules (e.g., protein rotation, 油脂 balance). Otherwise omit.

### B.6 Present

Show the user the per-day picks as ready-to-paste lines so they can record them in their daily notes themselves. The system does not write to daily notes.

For each attendance day, output one line in the format:
`<Slug> <YYYY-MM-DD> — <Day> <theme> (<pick>, <flag>)` where `<Slug>` is the user-provided slug capitalized (first letter only).

### B.7 Report

```
/dine <slug> summary (<week-range>)
  picks:  N   (date list)
```

## Rules

Intent A:
- **Read-only on catalog docs**: do NOT modify the regional dining catalog or the credit-perks catalog from `/dine`
- **Reading from the dining log is fine**; new captures only via `/reflect` Dining Pulse or explicit user "记录今天 X"
- **0 candidates after hard filter**: relax most-restrictive constraint by 1 step, retry; surface 1-2 closest matches with flag "relaxed: <constraint>"
- **Always show credit-burn opportunity** if relevant (any perk-program H1/H2 cycle ≤ 60d deadline + unused, per the live perks ledger under `$OV/finance/`). Even if credit餐厅 doesn't match exact mood, surface as 4th line with format: `💡 Credit-burn alt: <restaurant> ($<amount> <half>, deadline <MM/DD>)`
- **Match user language**: Chinese-dominant if cuisine is Chinese; English if Western
- **Keep output under 30 lines** (table + 2-3 line reasoning + 1 close line)
- **No web search**: cuisine + restaurant data comes from local catalog files only

Intent B:
- **Read-only on the PDF**: never modify the catering PDF
- **Read-only on daily notes**: daily notes are user-authored; the system surfaces picks for the user to record themselves and never writes to `$OV/daily-notes/`
- **Does not touch the dining log**: workplace catering is excluded by design (low signal density per memory)
- **Per-day skip on parse failure**: if any one day's section fails to parse, skip that day with a logged warning; do not abort the whole batch
- **No web search**: menu data comes from the PDF only
