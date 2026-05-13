## Purpose

Three intents (auto-detected from args):
- **A. Restaurant Recommendation** (default): pick 3 restaurant candidates based on user-supplied context, historical preferences, and credit-burn opportunities. Read-only on catalog docs under this intent.
- **B. Workplace Catering Tracker**: parse a weekly catering PDF dropped into `$OV/<slug>/catering/`, choose health-aware picks for the user's attendance days, and surface a confirmed table for the user to record themselves (the system does not write to daily notes).
- **C. Meal Log Capture** (ad-hoc): log a meal the user just ate. Parses receipt images (HEIC/JPG/PNG/PDF) when provided, cross-references catalogs for missing slots, asks ONE compact question for what cannot be derived, shows a draft row + side-effect plan, and appends to the dining log on confirm. Co-equal capture path with `/hi` Dining Pulse.

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

Intent C examples (logging a meal you just ate):
- `/dine log 今天午饭吃的 Cuanyue Malatang 两人 $49.32` → free-text meal report
- `/dine 今天晚饭吃的是 /path/to/receipt.heic` → receipt image (HEIC auto-converted before Read)
- `/dine 昨天 X 餐厅 dinner $85` → dated free text (respects late-sleep rule)
- `/dine log /path/to/receipt.pdf` → receipt PDF outside any catering folder

If args present, parse them as initial filters; only ask for slots not derivable.

## Step 0: Intent detection

Parse args. Precedence: **B → C → A** (most specific match wins; ambiguous → ask user one line before routing).

Route to **Intent B** if any of:
- First arg matches an existing folder `$OV/<arg>/catering/` (workplace slug)
- Any arg is a `.pdf` path under a `$OV/*/catering/` folder
- Args contain the literal token `catering`

Else route to **Intent C** if any of:
- Leading subcommand `log` (e.g., `/dine log <freetext>`)
- Args contain past-tense / reporting markers: `记录` / `log` / `吃了` / `吃的` / `刚吃完` / "今天X吃的" / "昨天Y" / "just had"
- An image path (`.heic` / `.jpg` / `.jpeg` / `.png`) is provided
- A `.pdf` path is provided **outside** any `$OV/*/catering/` folder
- Free text mentions a specific restaurant + amount/party (e.g., `<name> 两人 $49.32`) without a forward-looking verb

Do NOT route to C if the message is forward-looking: contains `推荐` / `去哪吃` / `想吃` / `what should I eat` / `where to eat` / `今晚吃什么` → fall through to A.

Otherwise route to **Intent A** (continue to Step 1 below).

For Intent B, jump to the "Intent B: Workplace Catering Tracker" section near the bottom and skip Steps 1-5.
For Intent C, jump to the "Intent C: Meal Log Capture" section near the bottom and skip Steps 1-5.

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

The user's vault holds these catalogs under `<paths.travel>/` and `<paths.finance>/`. Discover the actual filenames via `Grep` on those directories at runtime; do not hardcode private filenames here.

- Regional dining catalog (rotation + Michelin wishlist + 场景索引), under `<paths.travel>/`
- Dining log (history with 评分 + 再去 + recency), under `<paths.travel>/`
- Credit-perks dining catalog (Cycle Tracking + city catalogs), under `<paths.travel>/`
- Perks ledger (current cycle credit status, for burn signal), under `<paths.finance>/`
- Restaurant gift cards (prepaid balances per restaurant, for soft "use it" signal), under `<paths.finance>/`
- For LA / NYC / other city: use the credit-perks catalog city section + the corresponding city Michelin guide under `<paths.archive>/practical/travel/`

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

## Intent C: Meal Log Capture

Append a row to the user's meal log file under `<paths.travel>/` (filename specified in `profile/diet.md` § Catalog files; gitignored config). Co-equal capture path with `/hi` Dining Pulse.

### C.1 Resolve source material

Three input shapes:
- **Image receipt** (`.heic` / `.jpg` / `.jpeg` / `.png`): if HEIC or file size > 256KB, convert first via `sips -s format jpeg -Z 900 <src> --out /tmp/<basename>.jpg`, then `Read` the JPEG. `sips` is macOS-native; do not assume ImageMagick.
- **PDF receipt** (outside any `catering/` folder): `Read` directly.
- **Free text only**: parse the text for restaurant name, party size, total, and any other slots the user volunteered.

For images / PDFs, extract: restaurant name, items + spicy markers, subtotal / tax / tip / total, payment method (Apple Pay / Visa last-4 / gift card / cash), date + time, party size if shown.

### C.2 Cross-check catalogs (parallel reads)

Read `profile/diet.md` § Catalog files first to resolve the three filenames below; if `profile/diet.md` is missing or the section is empty, skip the catalog lookups and note that in the closing line.

- `Grep` the city catalog file under `<paths.travel>/` for the restaurant → derive `类型`, `City`, `⭐` if listed.
- `Grep` the dining log file under `<paths.travel>/` for the restaurant → first-time-or-not flag (used in 必点·备注 line if first time).
- `Grep` the gift-card catalog file under `<paths.finance>/` for the restaurant → if listed, expect a Credit slot of `Gift Card (no UR)` unless receipt says otherwise.
- If any catalog file is missing, skip silently and note in the closing line.

### C.3 Auto-derive what you can

| Slot | Derivation |
|---|---|
| **Date** | Default today; respect CLAUDE.md late-sleep rule (before 03:00 → previous calendar day). User free text override wins. |
| **City** | Catalog match → use; else infer from restaurant address on receipt; else ask. |
| **类型** | Catalog match → use; else infer from restaurant name (湘菜/川菜/etc.); else ask. |
| **⭐** | Catalog match only; else blank. |
| **Platform** | Receipt "Dine IN" → `W dine-in`; "Pickup/To-Go" → `W pickup`; OpenTable / Resy / DoorDash from booking source if visible; else ask. |
| **Credit** | Payment method → CSR (Visa) means `CSR #1 (+<UR estimate> @3x dining)` where UR estimate = round(subtotal × 3); Apple Pay → `Apple Pay (card 待 confirm)`; gift card → `Gift Card (no UR)`. |
| **健康 flags** | Heuristic from dish names. Cheatsheet: 粉蒸肉/红烧肉/扣肉/猪手 → `肥肉多`; 油炸/酥/脆皮 → `油炸`; 麻辣/水煮/干锅 → `重辣` / `油重`; 凉拌/清炒/白灼 → `清淡`; 全肉无蔬菜 → `蔬菜0` / `protein-heavy`; 1 蔬 + 2 肉 → `蔬菜少 (1/3)`; 米粉/麻辣烫 → `钠重`. Combine with `·`. Always show derivation to user in confirm prompt so they can correct. |

Required slots that cannot be derived: ask the user in **ONE compact prompt** (not a 6-question waterfall). Required = 评分 (1-10), 再去 (Y/N/Maybe), and any of {City / 类型 / Platform} that the auto-derive could not fill. Optional 1-line note at the end.

Example compact prompt:
> `City? · 评分 1-10? · 再去 Y/N/Maybe? · Platform (W dine-in / W pickup / OT / R / DD)? · 1 句备注?`

### C.4 Side-effect plan

Before writing, plan side effects. Each is opt-in via the confirm prompt (see C.5):

| Side effect | Trigger | Action |
|---|---|---|
| Meal log append | Always | Append row to the meal log file (under `<paths.travel>/`, filename per `profile/diet.md`); bump `Last updated:` to today. |
| Gift card update | Receipt shows gift-card balance line OR user volunteers balance | Update existing row in the gift-card catalog file (under `<paths.finance>/`, filename per `profile/diet.md`): Balance + Last updated + Source; or insert new row if first time. |
| Perks Ledger nudge | Credit slot maps to a tracked cycle credit (CSR dining 3x UR, OpenTable H1/H2, Resy quarterly, Sapphire Tables) | Suggest update; cite which row's `Cycle subtotal` would change by +$<amount>. Do NOT auto-write; surface as a one-liner for the user to apply manually. |
| Catalog promotion flag | 评分 ≥ 8 AND 再去 = Y AND restaurant not currently in the relevant city catalog file (per `profile/diet.md`) | One-line suggestion at the end: `→ 考虑 promote 到 <city catalog name> (评分 N + 再去 Y, 还没在 catalog)`. Do NOT write. |
| Daily note | (never) | Daily notes are user-authored. Do NOT auto-create even if today's note is missing. |

### C.5 Confirm gate (non-negotiable)

Show the user in this exact shape:

```
Draft row (meal log):
| <Date> | <Restaurant> | <City> | <类型> | <⭐> | <评分> | <再去> | <健康> | <Platform> | <Credit> | <必点·备注> |

Side effects:
  1. Append row to meal log + bump Last updated
  2. <gift card update if any>
  3. <perks ledger nudge if any>
  4. <catalog promotion flag if any>

OK to apply 1-N? (yes / partial: "1,2" / no / edit: tell me what to change)
```

User says `yes` → apply all. Partial → apply only the listed numbers. `no` → do nothing. `edit` → patch and re-confirm. **Never silent-append.**

### C.6 Write

For the meal log: use `Edit` to insert the new row at the correct date position (the table is roughly chronological; insert before the next-newer-date row, or append at the end if today is the newest). Bump `Last updated:` line. For the gift-card catalog: same `Edit` pattern.

For Perks Ledger: do NOT write — surface the one-liner only.

### C.7 Report

One line:
> `Logged: <Restaurant> <Date> 评 <N>/10. <one optional flag, e.g., "Gift card balance now $X" or "→ promote candidate" or "Perks Ledger: CSR #1 dining +$Y to apply manually">.`

## Rules

Intent A:
- **Read-only on catalog docs (under Intent A)**: do NOT modify the regional dining catalog or the credit-perks catalog when handling a recommendation request. The dining log is also read-only under Intent A — appends route through Intent C (or `/hi` Dining Pulse).
- **0 candidates after hard filter**: relax most-restrictive constraint by 1 step, retry; surface 1-2 closest matches with flag "relaxed: <constraint>"
- **Always show credit-burn opportunity** if relevant (any perk-program H1/H2 cycle ≤ 60d deadline + unused, per the live perks ledger under `<paths.finance>/`). Even if credit餐厅 doesn't match exact mood, surface as 4th line with format: `💡 Credit-burn alt: <restaurant> ($<amount> <half>, deadline <MM/DD>)`
- **Match user language**: Chinese-dominant if cuisine is Chinese; English if Western
- **Keep output under 30 lines** (table + 2-3 line reasoning + 1 close line)
- **No web search**: cuisine + restaurant data comes from local catalog files only

Intent B:
- **Read-only on the PDF**: never modify the catering PDF
- **Read-only on daily notes**: daily notes are user-authored; the system surfaces picks for the user to record themselves and never writes to `<paths.daily_notes>/`
- **Does not touch the dining log**: workplace catering is excluded by design (low signal density per memory)
- **Per-day skip on parse failure**: if any one day's section fails to parse, skip that day with a logged warning; do not abort the whole batch
- **No web search**: menu data comes from the PDF only

Intent C:
- **Confirmation gate is non-negotiable**: never silent-append. Always show the draft row + side-effect plan and wait for user `yes` / partial / no / edit.
- **One compact prompt for missing slots**: do NOT waterfall 6 questions. Group required-and-underivable slots into a single line.
- **HEIC + large image handling**: if the input image is HEIC or > 256KB, convert via `sips -s format jpeg -Z 900 <src> --out /tmp/<basename>.jpg` first, then `Read` the JPEG. Do not assume ImageMagick.
- **Read-only on daily notes**: do NOT auto-create today's daily note even if it's missing. Daily notes are user-authored.
- **Read-only on Perks Ledger**: surface the cycle-credit nudge as a one-liner; never auto-write to the ledger.
- **Match user language**: Chinese-dominant for Chinese cuisine; English otherwise.
- **No web search**: restaurant data comes from local catalogs and the user-provided receipt only.
- **Tight output**: draft row + side-effect list + one-line confirm prompt. No preamble.
