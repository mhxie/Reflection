# Perks & Trip Status

Read-only dashboard. Surfaces open decisions, upcoming deadlines, and data gaps from existing trackers in `<paths.finance>/` and `<paths.travel>/`. Use on revisit to avoid re-reading multiple files.

## Load

Discover and read markdown trackers under:
- `<paths.finance>/*.md`
- `<paths.travel>/*.md`
- `<paths.planning>/*.md` (if present)

Today: `date +%Y-%m-%d`. If a folder is empty, skip it.

## Output

Four sections, in this order. Omit any section with zero items.

**Urgent (< 14 days)**
- Any dated item within 14 days: renewal, expiration, conditional trigger resolution, booking deadline
- Each line: item + days-to-deadline + tracker recommendation if any

**This quarter**
- Period-bound credits unclaimed before quarter-end
- Yearly uses remaining with no allocation
- Skip monthly auto credits unless an anomaly is visible in logs

**Pending decisions**
For each open decision across trackers:
- Subject
- Recommendation from tracker (else `TBD`)
- One-line reason

**Data gaps**
Fields still marked `TBD` or `☐` that likely have a user-side answer.

## Close

End with one line: pick the highest-leverage urgent item as the next action, or invite the user to supply a data-gap answer.

## Rules

- Read-only. Do not write any file.
- Do not propose new plans or optimizations; use a separate command for that.
- Do not re-derive tracker logic; surface what is there.
- Keep output under ~150 lines. If a section exceeds 5 items, show top 3 and add a pointer.
- Match user's language convention per `CLAUDE.md`.
