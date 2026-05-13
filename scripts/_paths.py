"""Path resolution helpers for atelier scripts. Stdlib-only.

Why this exists: every script that walks the vault used to hardcode
relative `Path("zk/...")` literals. When run with $OV unset (or from a
cwd without a `zk/` subdir), they either silently created stray
directories in the project root or returned empty results. Centralizing
$OV resolution here gives every script the same fail-loud behavior and
the same token-efficient output format.

Registry layer: `harness/paths.toml` (canonical, committed) maps logical
tier names to physical segments under $OV. `harness/paths.local.toml`
(gitignored, per-user) layers extensions on top (localized wikis,
sandbox overrides). A tier rename happens in the canonical file, not
across N markdown files. Scripts that previously wrote `OV / "wip"`
should call `wip_dir()` etc. so the rename propagates automatically.

Usage:
    from _paths import vault_root, fmt, tier, wiki_dirs

    OV = vault_root()                # absolute Path; for filesystem operations
    WIP_DIR = tier("wip")            # registry-aware
    WIKI_DIRS = wiki_dirs()          # list[Path]: primary wiki + localized
    print(fmt(some_file))            # '$OV/wiki/Foo.md' (token-efficient output)
"""

from __future__ import annotations

import os
import sys
import tomllib
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def vault_root() -> Path:
    """Return $OV as an absolute Path. Exit with a clear error if unset.

    Refusing to fall back to a relative 'zk/' default because that silently
    creates stray directories wherever the script runs.
    """
    ov = os.environ.get("OV")
    if not ov:
        prog = Path(sys.argv[0]).name if sys.argv else "<script>"
        sys.exit(
            f"ERROR: $OV environment variable not set. "
            f"Set it to your vault root before running {prog} "
            f'(e.g., `export OV="$HOME/zk"`).'
        )
    return Path(ov).expanduser().resolve()


def _atelier_root() -> Path:
    """Repo root (one level above scripts/)."""
    return Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def _registry() -> dict:
    """Load harness/paths.toml, layer harness/paths.local.toml on top.

    Returns the merged `[paths]` table. Missing files are tolerated: an
    OSS user without a `paths.local.toml` just gets the canonical map.

    Layering semantics: scalar keys are overridden; the
    `wiki_localized` sub-table is unioned (per-user adds languages
    without losing canonical entries, which are empty by default).
    """
    canonical_path = _atelier_root() / "harness" / "paths.toml"
    if not canonical_path.is_file():
        sys.exit(
            f"ERROR: canonical path registry missing at {canonical_path}. "
            "The atelier repo is incomplete; restore harness/paths.toml."
        )
    with canonical_path.open("rb") as f:
        merged = tomllib.load(f).get("paths", {})
    # Ensure wiki_localized exists so callers can iterate without KeyError.
    merged.setdefault("wiki_localized", {})

    local_path = _atelier_root() / "harness" / "paths.local.toml"
    if local_path.is_file():
        with local_path.open("rb") as f:
            local = tomllib.load(f).get("paths", {})
        local_loc = local.pop("wiki_localized", None)
        merged.update(local)
        if local_loc:
            merged["wiki_localized"] = {
                **merged.get("wiki_localized", {}),
                **local_loc,
            }

    return merged


def _resolve_segment(segment: str) -> Path:
    """Resolve a registry segment to an absolute Path under $OV.

    Absolute segments (rare; used for sandbox overrides) pass through.
    """
    if segment.startswith("/"):
        return Path(segment).expanduser().resolve()
    return vault_root() / segment


def tier(name: str) -> Path:
    """Return the absolute Path for a registry tier name.

    Exits with a clear error if the tier is unknown so typos surface
    immediately rather than silently writing to the wrong location.
    """
    reg = _registry()
    if name not in reg:
        known = sorted(k for k in reg if k != "wiki_localized")
        sys.exit(
            f"ERROR: unknown tier '{name}' in path registry. "
            f"Known: {', '.join(known)}. "
            "Add it to harness/paths.toml (or paths.local.toml for "
            "per-user tiers)."
        )
    value = reg[name]
    if not isinstance(value, str):
        sys.exit(
            f"ERROR: tier '{name}' resolves to {type(value).__name__}, "
            "expected string. Check harness/paths.toml."
        )
    return _resolve_segment(value)


def tier_segments() -> dict[str, str]:
    """Return the merged {name: segment} mapping (no path resolution).

    Useful for lint checks that compare segments against directory names
    in committed markdown.
    """
    reg = _registry()
    return {k: v for k, v in reg.items() if isinstance(v, str)}


def wiki_dirs() -> list[Path]:
    """Return the list of wiki directories: primary + localized.

    Order: primary `wiki` first, then localized entries in dict order
    (Python 3.7+ preserves insertion order). Callers that just need the
    primary directory should call `tier("wiki")` instead.
    """
    reg = _registry()
    dirs = [_resolve_segment(reg["wiki"])]
    for segment in reg.get("wiki_localized", {}).values():
        if isinstance(segment, str):
            dirs.append(_resolve_segment(segment))
    return dirs


def fmt(p: Path) -> str:
    """Render under-vault paths as '$OV/<rel>' for token-efficient output.

    Use in stdout, JSON output, error messages: anywhere paths reach the
    orchestrator or user. Internal file operations should keep using the
    absolute Path object directly.

    Falls through to the absolute path string if `p` is not under the vault
    (so logs of out-of-vault paths still resolve unambiguously).
    """
    try:
        rel = p.resolve().relative_to(vault_root())
        return f"$OV/{rel.as_posix()}"
    except ValueError:
        return p.as_posix()
