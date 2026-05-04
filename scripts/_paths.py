"""Path resolution helpers for atelier scripts. Stdlib-only.

Why this exists: every script that walks the vault used to hardcode
relative `Path("zk/...")` literals. When run with $OV unset (or from a
cwd without a `zk/` subdir), they either silently created stray
directories in the project root or returned empty results. Centralizing
$OV resolution here gives every script the same fail-loud behavior and
the same token-efficient output format.

Usage:
    from _paths import vault_root, fmt

    OV = vault_root()                # absolute Path; for filesystem operations
    WIKI_DIR = OV / "wiki"
    print(fmt(some_file))            # '$OV/wiki/Foo.md' (token-efficient output)
"""

from __future__ import annotations

import os
import sys
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
