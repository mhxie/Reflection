#!/usr/bin/env python3
"""
pricing.py: provider pricing catalog reader + cost calculator. Stdlib only.

Reads `scripts/pricing.toml` (offline reference catalog, co-located
with this script — NOT in `harness/` because it is not a runtime
contract; nothing on the dispatch path loads it) and the chat_completion.py
invocation log (`~/.cache/atelier/llm_calls/<YYYY-MM-DD>.jsonl`) to
emit pricing tables, blended-cost rankings, and retrospective cost
totals for actual API calls.

Subcommands:
    list                          Sorted table (cheapest blended first)
    blended <provider> <class>    Single value, $/1M blended
    cost <provider> <class>       Estimated $ for a given token count
        --input N --output N
    cost-from-log [--date YYYY-MM-DD] [--profile NAME]
                                  Retrospective cost from invocation log
                                  (sums per-call usage * pricing).

Pricing classes are exactly two: `flagship` (top reasoning) and
`standard` (everyday). Use a provider's `notes` field for ultra-cheap
or ultra-niche variants that don't merit their own row.

Blended cost formula: (3*input + 1*output) / 4. Assumes the 3:1
input:output token ratio typical of our agent workloads.

Exit codes:
    0  ok
    1  pricing.toml missing or malformed
    2  provider/class not found, invalid arguments
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

PRICING_TOML = Path(__file__).resolve().with_suffix(".toml")
DEFAULT_LOG_DIR = Path.home() / ".cache" / "atelier" / "llm_calls"


def _load() -> dict:
    if not PRICING_TOML.exists():
        sys.stderr.write(f"pricing: {PRICING_TOML} not found\n")
        sys.exit(1)
    with PRICING_TOML.open("rb") as f:
        return tomllib.load(f)


def _blended(entry: dict) -> float:
    """Blended USD per 1M tokens, 3:1 input:output ratio."""
    return (3.0 * entry["input"] + 1.0 * entry["output"]) / 4.0


def _entries(data: dict) -> list[tuple[str, str, dict]]:
    """Return [(provider, class, entry), ...] over both flagship + standard."""
    out: list[tuple[str, str, dict]] = []
    providers = data.get("providers", {}) or {}
    for pname, pdata in providers.items():
        if not isinstance(pdata, dict):
            continue
        for klass in ("flagship", "standard"):
            entry = pdata.get(klass)
            if isinstance(entry, dict) and entry.get("model"):
                out.append((pname, klass, entry))
    return out


def cmd_list(args: argparse.Namespace) -> int:
    data = _load()
    rows = [(p, k, e, _blended(e)) for p, k, e in _entries(data)]
    rows.sort(key=lambda r: r[3])
    width = max(len(f"{p}/{k}/{e['model']}") for p, k, e, _ in rows)
    print(f"{'Provider/Class/Model':<{width}}  {'Input':>7}  {'Output':>7}  {'Cache':>9}  {'Blended':>8}  Notes")
    print("-" * (width + 60))
    for p, k, e, b in rows:
        ident = f"{p}/{k}/{e['model']}"
        notes = e.get("notes", "") or ""
        if len(notes) > 60:
            notes = notes[:57] + "..."
        print(
            f"{ident:<{width}}  ${e['input']:>6.2f}  ${e['output']:>6.2f}  ${e['cache_hit']:>8.4f}  ${b:>7.3f}  {notes}"
        )
    return 0


def _resolve(data: dict, provider: str, klass: str) -> dict:
    p = (data.get("providers", {}) or {}).get(provider)
    if not p:
        sys.stderr.write(f"pricing: unknown provider '{provider}'\n")
        sys.exit(2)
    entry = p.get(klass)
    if not entry:
        sys.stderr.write(f"pricing: provider '{provider}' has no '{klass}' class\n")
        sys.exit(2)
    return entry


def cmd_blended(args: argparse.Namespace) -> int:
    data = _load()
    entry = _resolve(data, args.provider, args.klass)
    print(f"{_blended(entry):.4f}")
    return 0


def cmd_cost(args: argparse.Namespace) -> int:
    data = _load()
    entry = _resolve(data, args.provider, args.klass)
    cost = (args.input * entry["input"] + args.output * entry["output"]) / 1_000_000
    cached_cost = (args.input * entry["cache_hit"] + args.output * entry["output"]) / 1_000_000
    print(f"{cost:.6f}  (cache-hit: {cached_cost:.6f})")
    return 0


def _model_to_pricing(data: dict) -> dict[str, dict]:
    """Index all model ids -> pricing entries for fast lookup from the log."""
    out: dict[str, dict] = {}
    for _p, _k, entry in _entries(data):
        out[entry["model"]] = entry
    return out


def cmd_cost_from_log(args: argparse.Namespace) -> int:
    data = _load()
    model_map = _model_to_pricing(data)
    log_dir = Path(args.log_dir) if args.log_dir else DEFAULT_LOG_DIR
    if not log_dir.exists():
        sys.stderr.write(f"pricing: log dir {log_dir} does not exist\n")
        return 2

    if args.date:
        log_files = [log_dir / f"{args.date}.jsonl"]
    else:
        log_files = sorted(log_dir.glob("*.jsonl"))

    total = 0.0
    matched = 0
    skipped_unknown = 0
    # model -> [calls, input_tokens, output_tokens, cost]
    by_model: dict[str, list] = {}
    for path in log_files:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if args.profile and event.get("profile") != args.profile:
                continue
            usage = event.get("usage")
            model = event.get("model")
            if not usage or not model:
                continue
            entry = model_map.get(model)
            if not entry:
                skipped_unknown += 1
                continue
            inp = int(usage.get("prompt_tokens", 0) or 0)
            out = int(usage.get("completion_tokens", 0) or 0)
            # Account for cache-hit tokens at the discounted rate when present.
            cache_hit = int(
                (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
                or usage.get("prompt_cache_hit_tokens", 0)
                or 0
            )
            cache_miss = max(inp - cache_hit, 0)
            cost = (
                cache_miss * entry["input"]
                + cache_hit * entry["cache_hit"]
                + out * entry["output"]
            ) / 1_000_000
            total += cost
            matched += 1
            row = by_model.setdefault(model, [0, 0, 0, 0.0])
            row[0] += 1
            row[1] += inp
            row[2] += out
            row[3] += cost

    width = max((len(m) for m in by_model), default=20)
    print(f"{'Model':<{width}}  {'Calls':>5}  {'Input':>10}  {'Output':>10}  {'Cost':>10}")
    print("-" * (width + 50))
    for model, (n, inp, out, cost) in sorted(by_model.items(), key=lambda x: -x[1][3]):
        print(f"{model:<{width}}  {n:>5d}  {inp:>10,}  {out:>10,}  ${cost:>9.4f}")
    print("-" * (width + 50))
    print(f"{'TOTAL':<{width}}  {matched:>5d}  {'':>10}  {'':>10}  ${total:>9.4f}")
    if skipped_unknown:
        sys.stderr.write(
            f"pricing: {skipped_unknown} log entries skipped (model not in pricing.toml)\n"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="scripts/pricing.py",
        description="Provider pricing reader + cost calculator (stdlib only).",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="Sorted table by blended cost")

    bp = sub.add_parser("blended", help="Blended USD/1M for a class")
    bp.add_argument("provider")
    bp.add_argument("klass", choices=["flagship", "standard"])

    cp = sub.add_parser("cost", help="Estimated cost for given token count")
    cp.add_argument("provider")
    cp.add_argument("klass", choices=["flagship", "standard"])
    cp.add_argument("--input", type=int, required=True, help="Input tokens.")
    cp.add_argument("--output", type=int, required=True, help="Output tokens.")

    lp = sub.add_parser("cost-from-log", help="Sum cost from invocation log")
    lp.add_argument("--date", default=None, help="Single YYYY-MM-DD log file.")
    lp.add_argument("--profile", default=None, help="Filter to one tier profile.")
    lp.add_argument("--log-dir", default=None, help="Override log directory.")

    args = ap.parse_args(argv)
    return {
        "list": cmd_list,
        "blended": cmd_blended,
        "cost": cmd_cost,
        "cost-from-log": cmd_cost_from_log,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
