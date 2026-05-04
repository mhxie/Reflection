#!/usr/bin/env python3
"""
health.py: Aggregate Apple Health daily snapshots from zk/health/daily/.

Inputs: zk/health/daily/YYYY-MM-DD-health.md files with YAML frontmatter (see
zk/health/daily/README.md for schema). The `-health` suffix avoids Obsidian
wikilink collision with zk/daily-notes/YYYY-MM-DD.md (so `[[YYYY-MM-DD]]`
unambiguously resolves to the journal entry, not the health snapshot).

Subcommands:
  summary [--days N]     Last N days summary (default 7).
  audit                  Flag anomalies (HRV drop, RHR spike, short sleep, late bedtime, low steps).
  list                   List all loaded daily files with dates.
  trend <metric>         Plain-text trend for one metric across all loaded days.

Stdlib-only. Schema parser is purpose-built for the daily file format; not a general YAML parser.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import date as Date, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import vault_root  # type: ignore[import-not-found]  # noqa: E402

DAILY_DIR = vault_root() / "health" / "daily"

NUMERIC_FIELDS = {"weight_kg", "sleep_min", "steps", "resting_hr", "hrv_ms", "mindfulness_min"}
STRING_FIELDS = {"bedtime", "wake", "note", "date"}


@dataclass
class DayRecord:
    date: Date
    weight_kg: float | None = None
    sleep_min: int | None = None
    bedtime: str | None = None
    wake: str | None = None
    core_min: int | None = None
    rem_min: int | None = None
    deep_min: int | None = None
    awake_min: int | None = None
    steps: int | None = None
    resting_hr: int | None = None
    hrv_ms: int | None = None
    active_kcal: int | None = None
    exercise_min: int | None = None
    vo2_max: float | None = None
    workouts: list[dict[str, Any]] = field(default_factory=list)
    mindfulness_min: int | None = None
    note: str = ""


def _parse_scalar(s: str) -> Any:
    s = s.strip()
    # strip inline comment
    if "#" in s:
        s = s.split("#", 1)[0].strip()
    if s == "" or s == "null":
        return None
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    if s == "[]":
        return []
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        return s


def parse_daily_file(path: Path) -> DayRecord | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    body = parts[1]

    fields_dict: dict[str, Any] = {}
    workouts: list[dict[str, Any]] = []
    in_workouts = False
    current_workout: dict[str, Any] | None = None

    for raw_line in body.splitlines():
        if not raw_line.strip():
            continue
        is_indented = raw_line[0].isspace()
        stripped = raw_line.strip()

        if not is_indented:
            if current_workout is not None:
                workouts.append(current_workout)
                current_workout = None
            in_workouts = False
            if ":" in stripped:
                key, _, val = stripped.partition(":")
                key = key.strip()
                val = val.strip()
                if key == "workouts":
                    in_workouts = True
                    if val == "[]":
                        workouts = []
                    continue
                fields_dict[key] = _parse_scalar(val)
        else:
            if not in_workouts:
                continue
            if stripped.startswith("- "):
                if current_workout is not None:
                    workouts.append(current_workout)
                current_workout = {}
                rest = stripped[2:]
                if ":" in rest:
                    k, _, v = rest.partition(":")
                    current_workout[k.strip()] = _parse_scalar(v)
            elif current_workout is not None and ":" in stripped:
                k, _, v = stripped.partition(":")
                current_workout[k.strip()] = _parse_scalar(v)

    if current_workout is not None:
        workouts.append(current_workout)

    try:
        d = Date.fromisoformat(str(fields_dict.get("date", "")))
    except (ValueError, TypeError):
        return None

    return DayRecord(
        date=d,
        weight_kg=fields_dict.get("weight_kg"),
        sleep_min=fields_dict.get("sleep_min"),
        bedtime=fields_dict.get("bedtime"),
        wake=fields_dict.get("wake"),
        core_min=fields_dict.get("core_min"),
        rem_min=fields_dict.get("rem_min"),
        deep_min=fields_dict.get("deep_min"),
        awake_min=fields_dict.get("awake_min"),
        steps=fields_dict.get("steps"),
        resting_hr=fields_dict.get("resting_hr"),
        hrv_ms=fields_dict.get("hrv_ms"),
        active_kcal=fields_dict.get("active_kcal"),
        exercise_min=fields_dict.get("exercise_min"),
        vo2_max=fields_dict.get("vo2_max"),
        workouts=workouts,
        mindfulness_min=fields_dict.get("mindfulness_min"),
        note=fields_dict.get("note") or "",
    )


def load_records(days: int | None = None) -> list[DayRecord]:
    if not DAILY_DIR.exists():
        return []
    records: list[DayRecord] = []
    for f in sorted(DAILY_DIR.glob("*.md")):
        if f.name == "README.md":
            continue
        rec = parse_daily_file(f)
        if rec is not None:
            records.append(rec)
    records.sort(key=lambda r: r.date)
    if days is not None and records:
        cutoff = records[-1].date - timedelta(days=days - 1)
        records = [r for r in records if r.date >= cutoff]
    return records


def _avg(vals: list[Any]) -> float | None:
    clean = [float(v) for v in vals if v is not None]
    return sum(clean) / len(clean) if clean else None


def _bedtime_to_min(t: str | None) -> int | None:
    if not t:
        return None
    try:
        h, m = map(int, t.split(":"))
        if h < 6:  # treat 00-05 as 24-29 for averaging across midnight
            h += 24
        return h * 60 + m
    except (ValueError, AttributeError):
        return None


def cmd_summary(args: argparse.Namespace) -> int:
    records = load_records(args.days)
    if not records:
        print("No daily records found.")
        return 0

    n = len(records)
    print(f"\nApple Health summary — {n} day(s) ({records[0].date} to {records[-1].date})")
    print("─" * 72)

    def fmt(v: Any, suffix: str = "", prec: int = 1) -> str:
        if v is None:
            return "—"
        if isinstance(v, float):
            return f"{v:.{prec}f}{suffix}"
        return f"{v}{suffix}"

    weights = [r.weight_kg for r in records]
    sleeps = [r.sleep_min for r in records]
    steps = [r.steps for r in records]
    rhr = [r.resting_hr for r in records]
    hrv = [r.hrv_ms for r in records]

    weight_measured = sum(1 for w in weights if w is not None)
    weight_first = next((w for w in weights if w is not None), None)
    weight_last = next((w for w in reversed(weights) if w is not None), None)
    weight_delta = (
        weight_last - weight_first
        if weight_first is not None and weight_last is not None and weight_first != weight_last
        else None
    )

    sleep_avg = _avg(sleeps)
    sleep_avg_h = sleep_avg / 60 if sleep_avg is not None else None

    print(f"  Weight (kg)       avg {fmt(_avg(weights))}  measured {weight_measured}/{n}"
          + (f"  Δ {weight_delta:+.1f}" if weight_delta is not None else ""))
    print(f"  Sleep             avg {fmt(sleep_avg)}min ({fmt(sleep_avg_h, 'h')})")
    deep = [r.deep_min for r in records]
    rem = [r.rem_min for r in records]
    core = [r.core_min for r in records]
    awake = [r.awake_min for r in records]
    if any(v is not None for v in deep + rem + core):
        print(f"    stages          deep {fmt(_avg(deep), prec=0)}m | REM {fmt(_avg(rem), prec=0)}m | core {fmt(_avg(core), prec=0)}m | awake {fmt(_avg(awake), prec=0)}m")
    print(f"  Steps             avg {fmt(_avg(steps), prec=0)}")
    print(f"  Resting HR        avg {fmt(_avg(rhr), prec=0)} bpm")
    print(f"  HRV               avg {fmt(_avg(hrv), prec=0)} ms")
    kcal = [r.active_kcal for r in records]
    ex = [r.exercise_min for r in records]
    ex_clean = [v for v in ex if v is not None]
    ex_hit_30 = sum(1 for v in ex_clean if v >= 30)
    print(f"  Active kcal       avg {fmt(_avg(kcal), prec=0)}")
    print(f"  Exercise min      avg {fmt(_avg(ex), prec=0)}  hit-30 ring {ex_hit_30}/{len(ex_clean)}")
    vo2_vals = [(r.date, r.vo2_max) for r in records if r.vo2_max is not None]
    if vo2_vals:
        last_date, last_vo2 = vo2_vals[-1]
        print(f"  VO2 max           latest {last_vo2} (measured {last_date})")

    bts = [_bedtime_to_min(r.bedtime) for r in records]
    bts_clean = [b for b in bts if b is not None]
    if bts_clean:
        avg_bt = sum(bts_clean) / len(bts_clean)
        ah = int(avg_bt // 60) % 24
        am = int(avg_bt % 60)
        past_3 = sum(1 for b in bts_clean if b >= 27 * 60)  # 03:00 = 27h in our wraparound
        before_mid = sum(1 for b in bts_clean if b < 24 * 60)
        print(f"  Bedtime           avg {ah:02d}:{am:02d}  past 03:00 {past_3}/{len(bts_clean)}  before 00:00 {before_mid}/{len(bts_clean)}")

    workout_count = sum(len(r.workouts) for r in records)
    workout_min_total = sum(int(w.get("min") or 0) for r in records for w in r.workouts)
    types: dict[str, int] = {}
    for r in records:
        for w in r.workouts:
            t = str(w.get("type") or "?")
            types[t] = types.get(t, 0) + 1
    types_str = ", ".join(f"{t}×{c}" for t, c in sorted(types.items(), key=lambda x: -x[1])) or "(none)"
    print(f"  Workouts          {workout_count} total, {workout_min_total} min   types: {types_str}")

    print()
    print(f"  {'Date':<12} {'Wt':<6} {'Sleep':<7} {'Bed':<7} {'Wake':<7} {'Steps':<7} {'RHR':<5} {'HRV':<5} Workouts")
    for r in records:
        wt = f"{r.weight_kg:.1f}" if r.weight_kg is not None else "—"
        sl = f"{r.sleep_min/60:.1f}h" if r.sleep_min is not None else "—"
        bt = r.bedtime or "—"
        wk = r.wake or "—"
        st = str(r.steps) if r.steps is not None else "—"
        rh = str(r.resting_hr) if r.resting_hr is not None else "—"
        hv = str(r.hrv_ms) if r.hrv_ms is not None else "—"
        ws = ", ".join(f"{w.get('type','?')} {w.get('min','?')}m" for w in r.workouts) or "—"
        print(f"  {str(r.date):<12} {wt:<6} {sl:<7} {bt:<7} {wk:<7} {st:<7} {rh:<5} {hv:<5} {ws}")
    print()
    return 0


def cmd_audit(_args: argparse.Namespace) -> int:
    records = load_records(None)
    if len(records) < 2:
        print("Need at least 2 daily records to audit.")
        return 0

    print("\nAnomaly audit (across all loaded records):")
    print("─" * 72)
    flagged = 0

    rhr_history: list[int] = []
    hrv_prev: int | None = None
    sleep_prev: tuple[str | None, str | None, int | None] | None = None

    for r in records:
        flags: list[str] = []

        if r.sleep_min is not None and r.sleep_min < 360:
            flags.append(f"short sleep {r.sleep_min/60:.1f}h")

        if r.deep_min is not None and r.deep_min < 30:
            flags.append(f"low deep sleep ({r.deep_min}m)")

        if r.exercise_min is not None and r.exercise_min < 10 and r.steps is not None and r.steps > 1000:
            flags.append(f"low exercise min ({r.exercise_min}m of 30 ring)")

        bm = _bedtime_to_min(r.bedtime)
        if bm is not None and bm >= 27 * 60:
            flags.append(f"bedtime past 03:00 ({r.bedtime})")

        if hrv_prev is not None and r.hrv_ms is not None:
            if r.hrv_ms < hrv_prev * 0.75:
                flags.append(f"HRV drop {hrv_prev}→{r.hrv_ms} ms ({(1 - r.hrv_ms/hrv_prev)*100:.0f}%)")

        if r.resting_hr is not None and rhr_history:
            base = sum(rhr_history) / len(rhr_history)
            if r.resting_hr > base * 1.10:
                flags.append(f"RHR spike {base:.0f}→{r.resting_hr}")

        if r.steps is not None and r.steps < 1000:
            flags.append(f"very low steps ({r.steps})")

        cur_sleep = (r.bedtime, r.wake, r.sleep_min)
        if sleep_prev is not None and cur_sleep == sleep_prev and any(x is not None for x in cur_sleep):
            flags.append("sleep fields duplicate previous day (data attribution issue)")

        if flags:
            flagged += 1
            print(f"  {r.date}: {'; '.join(flags)}")

        if r.resting_hr is not None:
            rhr_history.append(r.resting_hr)
            if len(rhr_history) > 7:
                rhr_history.pop(0)
        if r.hrv_ms is not None:
            hrv_prev = r.hrv_ms
        sleep_prev = cur_sleep

    if not flagged:
        print("  No anomalies detected.")
    else:
        print(f"\n  {flagged} day(s) flagged.")
    print()
    return 0


def cmd_list(_args: argparse.Namespace) -> int:
    records = load_records(None)
    if not records:
        print("No daily records.")
        return 0
    print(f"\n{len(records)} daily record(s):")
    for r in records:
        print(f"  {r.date}")
    print()
    return 0


def cmd_trend(args: argparse.Namespace) -> int:
    metric = args.metric
    valid = {"weight_kg", "sleep_min", "steps", "resting_hr", "hrv_ms", "bedtime"}
    if metric not in valid:
        print(f"Unknown metric: {metric}. Valid: {sorted(valid)}")
        return 2
    records = load_records(None)
    if not records:
        print("No records.")
        return 0
    print(f"\n{metric}:")
    for r in records:
        v = getattr(r, metric)
        print(f"  {r.date}  {v if v is not None else '—'}")
    print()
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="scripts/health.py", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("summary", help="Summarize last N days.")
    s.add_argument("--days", type=int, default=7)
    s.set_defaults(func=cmd_summary)

    sub.add_parser("audit", help="Flag anomalies.").set_defaults(func=cmd_audit)
    sub.add_parser("list", help="List all loaded daily files.").set_defaults(func=cmd_list)

    t = sub.add_parser("trend", help="Trend for a single metric.")
    t.add_argument("metric")
    t.set_defaults(func=cmd_trend)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
