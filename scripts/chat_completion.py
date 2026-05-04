#!/usr/bin/env python3
"""
chat_completion.py: stdlib-only OpenAI-compatible chat completion invoker.

Provider-neutral by design. The committed `harness/models.toml` defines
tier semantics; the gitignored `profile/models.toml` supplies the actual
provider/model bindings. Swapping providers is a binding-file edit, not
a script change.

Two modes — pick by use case:

  STATELESS (default, no flag)
      One-shot call. No history. Use for mechanical lookups, single
      bulk transforms, classification, anything where the prompt
      is self-contained.

      scripts/chat_completion.py --profile cross_validation --prompt "..."

  STATEFUL (--session FILE)
      Multi-turn. The script loads prior messages from FILE, sends
      them along with the new prompt, then appends the new turn and
      response back to FILE. Use for conversations, iterative
      refinement, deliberation chains. The provider's API is itself
      stateless — we replay history each call. Token cost grows
      linearly with session length; start a new session when the
      thread is done.

      scripts/chat_completion.py --profile X --session /tmp/s.json --prompt "first"
      scripts/chat_completion.py --profile X --session /tmp/s.json --prompt "second"

Other invocation flavors:

  Stdin via '-':
      echo "Hello" | scripts/chat_completion.py --profile X --prompt -

  Direct flags (no profile — ad-hoc):
      scripts/chat_completion.py --endpoint https://api.example.com/v1/chat/completions \\
                                 --model some-model --api-key-env EXAMPLE_KEY \\
                                 --prompt "..."

Profile keys read from the merged config (any may be overridden by flags):
    direct_api          model identifier
    direct_api_base     full endpoint URL (host + path)
    api_env             env var holding the API key
    direct_api_extras   inline table merged into request body for
                        provider-specific extensions (e.g., a `thinking`
                        block for reasoning-control providers)

Session file format: JSON array of `{"role": ..., "content": ...}` messages.
Inspectable, hand-editable, gitignore-worthy.

Invocation log (default ON): every successful or failed call appends one
JSON line to `~/.cache/atelier/llm_calls/<YYYY-MM-DD>.jsonl`. The event
records timestamp, profile, model, endpoint, prompt, response content,
reasoning_content (when thinking is enabled), `usage` token counts,
finish_reason, latency, and error kind on failure. Used for after-the-fact
quality evaluation, latency drift tracking, and reasoning-mode auditing.
The log dir is machine-local (parallel to ~/.cache/atelier/lance/) so it
does not sync into a Drive-mounted vault. Pass --no-log to skip the log
for sensitive prompts; --log-dir overrides the default location.

Auth is `Authorization: Bearer $<api_env>`. Providers that use a different
header scheme need their own helper (or a future --auth-header flag).

Exit codes:
    0  ok
    1  API error (non-2xx, malformed JSON, missing fields)
    2  config error (env var missing, profile not found, profile incomplete,
       or session file invalid)
    3  timeout
    4  invalid arguments (empty prompt, conflicting flags)
    5  response truncated at max_tokens (finish_reason=length); partial
       content is written to stdout, but caller must re-run with a higher
       --max-tokens to get the full response
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import tomllib
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_TOML = REPO_ROOT / "harness" / "models.toml"
BINDINGS_TOML = REPO_ROOT / "profile" / "models.toml"
DEFAULT_LOG_DIR = Path.home() / ".cache" / "atelier" / "llm_calls"


def _load_profile(name: str) -> dict | None:
    """Merge committed profile schema with gitignored bindings, by name.

    Returns the per-profile dict (rationale, invocation, claude_code,
    direct_api, api_env, ...) with binding values overlaid on the
    schema. Returns None if the profile is not in the schema. If the
    bindings file is absent, returns the schema-only profile (which
    will fail downstream when a binding key is required — by design).
    """
    if not SCHEMA_TOML.exists():
        return None
    with SCHEMA_TOML.open("rb") as f:
        schema = tomllib.load(f)
    profile = dict(schema.get("profiles", {}).get(name) or {})
    if not profile:
        return None
    if BINDINGS_TOML.exists():
        with BINDINGS_TOML.open("rb") as f:
            bindings = tomllib.load(f)
        profile.update(bindings.get("profiles", {}).get(name) or {})
    return profile


def _read_prompt(args: argparse.Namespace) -> str:
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8")
    if args.prompt == "-":
        return sys.stdin.read()
    return args.prompt or ""


def _load_session(path: Path) -> list[dict]:
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("session file must be a JSON array of messages")
    for i, m in enumerate(data):
        if not isinstance(m, dict) or "role" not in m or "content" not in m:
            raise ValueError(f"session[{i}] missing role/content")
    return data


def _save_session(path: Path, messages: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _resolve_extras(
    profile: dict | None, override_json: str | None, extras_field: str = "direct_api_extras"
) -> dict:
    extras: dict = {}
    if profile:
        extras.update(profile.get(extras_field, {}) or {})
    if override_json:
        extras.update(json.loads(override_json))
    return extras


def _post(endpoint: str, body: dict, api_key: str, timeout: float) -> dict:
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# Retriable HTTP statuses: rate limit (429) and the transient 5xx family.
# 4xx other than 429 are client bugs (bad request, auth, not found) and
# should not be retried.
_RETRIABLE_HTTP = {429, 500, 502, 503, 504}


def _backoff_seconds(attempt: int) -> float:
    """Exponential backoff schedule: 1s, 4s, 16s, ... capped at 60s."""
    return min(60.0, 4.0 ** attempt)


def _retry_after_seconds(exc: urllib.error.HTTPError) -> float | None:
    """Read Retry-After header from a 429/503 response. Returns seconds or None.

    The header may be either a number-of-seconds or an HTTP-date. We honor
    the numeric form; the date form falls through to the default backoff.
    """
    headers = getattr(exc, "headers", None)
    if not headers:
        return None
    val = headers.get("Retry-After")
    if not val:
        return None
    try:
        return max(0.0, float(val))
    except (TypeError, ValueError):
        return None


def _post_with_retry(
    endpoint: str,
    body: dict,
    api_key: str,
    timeout: float,
    *,
    max_attempts: int,
) -> dict:
    """POST with exponential backoff on transient failures.

    Retries: HTTP 429 (honoring Retry-After), 5xx, TimeoutError, URLError
    (network-level). Does NOT retry: 4xx other than 429 (client bug),
    JSONDecodeError (bad response shape).

    Re-raises the last exception when attempts are exhausted, so the
    existing top-level handlers in main() still classify it correctly.
    """
    attempts = max(1, max_attempts)
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return _post(endpoint, body, api_key, timeout)
        except urllib.error.HTTPError as e:
            if e.code not in _RETRIABLE_HTTP or attempt == attempts - 1:
                raise
            wait = _retry_after_seconds(e) or _backoff_seconds(attempt)
            sys.stderr.write(
                f"chat_completion: HTTP {e.code} on attempt {attempt+1}/{attempts}; "
                f"retrying in {wait:.1f}s\n"
            )
            time.sleep(wait)
            last_exc = e
        except (TimeoutError, socket.timeout) as e:
            if attempt == attempts - 1:
                raise
            wait = _backoff_seconds(attempt)
            sys.stderr.write(
                f"chat_completion: timeout on attempt {attempt+1}/{attempts}; "
                f"retrying in {wait:.1f}s\n"
            )
            time.sleep(wait)
            last_exc = e
        except urllib.error.URLError as e:
            if attempt == attempts - 1:
                raise
            wait = _backoff_seconds(attempt)
            sys.stderr.write(
                f"chat_completion: network error on attempt {attempt+1}/{attempts}: {e}; "
                f"retrying in {wait:.1f}s\n"
            )
            time.sleep(wait)
            last_exc = e
    # Defensive: should be unreachable (the last attempt re-raises above).
    if last_exc:
        raise last_exc
    raise RuntimeError("chat_completion: retry loop exited without success or exception")


def _log_call(log_dir: Path, event: dict) -> None:
    """Append a one-line JSON event for this call.

    Best-effort: any IOError, JSON-encoding error, or filesystem hiccup is
    swallowed so logging never fails the API call. Logs land in date-bucketed
    JSONL files under `log_dir` (default `~/.cache/atelier/llm_calls/`); the
    location is machine-local, parallel to the lance index, so it does not
    sync into a Drive-mounted vault. The log is a private record of every
    direct-API call: prompt, response, reasoning content, usage tokens,
    latency, finish_reason. Used for after-the-fact evaluation of response
    quality, latency drift, and reasoning-mode behaviour.
    """
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except (OSError, ValueError, TypeError):
        pass


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="scripts/chat_completion.py",
        description="OpenAI-compatible chat completion invoker. Stdlib only.",
    )
    ap.add_argument(
        "--profile",
        help=(
            "Profile name. Reads `direct_api`, `direct_api_base`, `api_env`, "
            "`direct_api_extras` from the merged schema (harness/models.toml) "
            "+ bindings (profile/models.toml). Any can be overridden by the "
            "flags below."
        ),
    )
    ap.add_argument(
        "--shadow-of",
        default=None,
        metavar="PROFILE",
        help=(
            "Run the call against the profile's shadow_api binding instead "
            "of direct_api. Reads shadow_api / shadow_api_base / shadow_api_env "
            "/ shadow_api_extras / shadow_api_timeout. The invocation log "
            "records `shadow_of: <PROFILE>` so shadow calls are separable "
            "from primary calls. Used by scripts/shadow.sh for sampled "
            "logging-only quality comparison; rarely useful directly."
        ),
    )
    ap.add_argument("--endpoint", help="Override profile's direct_api_base.")
    ap.add_argument("--model", help="Override profile's direct_api.")
    ap.add_argument(
        "--api-key-env",
        help="Override profile's api_env (env var name, not the key itself).",
    )
    ap.add_argument(
        "--extras-json",
        help="JSON object merged into request body, last-wins over profile extras.",
    )

    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--prompt", help="User prompt text. Use '-' for stdin.")
    grp.add_argument("--prompt-file", help="Path to file containing prompt.")

    ap.add_argument("--system", default=None, help="Optional system prompt.")
    ap.add_argument(
        "--session",
        default=None,
        help=(
            "Path to a JSON session file. If it exists, prior messages are "
            "replayed before the new prompt; on success, the new turn is "
            "appended to the file. Atomic write."
        ),
    )
    ap.add_argument(
        "--max-tokens",
        type=int,
        default=8192,
        help=(
            "Output token cap. Defaults to 8192 (was 4096; raised because "
            "system-review responses regularly need 8K+). When the response "
            "hits the cap (finish_reason=length), the script writes the "
            "partial content to stdout but exits 5 so callers see the "
            "truncation. Pass a higher value (e.g., 16384) for review-grade "
            "calls; pass 0 to silently accept truncation."
        ),
    )
    ap.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help=(
            "Total attempts for transient errors (429 with Retry-After, 5xx, "
            "TimeoutError, network errors). Default 3. Set 1 to disable "
            "retries (useful for tests and one-shot scripts that prefer a "
            "fast fail)."
        ),
    )
    ap.add_argument(
        "--check-context",
        type=int,
        default=0,
        metavar="MAX_INPUT_TOKENS",
        help=(
            "Pre-flight: estimate token count of the request (chars/4) and "
            "exit 4 before any API call if it exceeds MAX_INPUT_TOKENS. "
            "Pass the model's context window minus your --max-tokens budget. "
            "Default 0 = disabled."
        ),
    )
    ap.add_argument(
        "--timeout",
        type=float,
        default=None,
        help=(
            "Per-call timeout in seconds. Defaults to the profile's "
            "`direct_api_timeout` if set, else 120s. Reasoning-heavy tiers "
            "should configure this in the profile."
        ),
    )
    ap.add_argument(
        "--json",
        dest="emit_json",
        action="store_true",
        help="Emit full response object as JSON. Default emits message.content.",
    )
    ap.add_argument(
        "--no-log",
        dest="log",
        action="store_false",
        default=True,
        help=(
            "Skip the invocation log. Use for sensitive prompts or test runs. "
            "Default: log every call to ~/.cache/atelier/llm_calls/<date>.jsonl."
        ),
    )
    ap.add_argument(
        "--log-dir",
        default=None,
        help="Override the invocation log directory.",
    )
    args = ap.parse_args(argv)

    profile = _load_profile(args.profile) if args.profile else None
    if args.profile and profile is None:
        sys.stderr.write(
            f"chat_completion: profile '{args.profile}' not found in harness/models.toml\n"
        )
        return 2

    # When --shadow-of is set, source bindings from the shadow_* keys instead
    # of the direct_api* keys. The active profile remains args.profile (so
    # logging records `profile=<args.profile>` plus `shadow_of=<args.shadow_of>`),
    # but the actual call goes to the shadow binding.
    if args.shadow_of:
        shadow_profile = _load_profile(args.shadow_of)
        if shadow_profile is None:
            sys.stderr.write(
                f"chat_completion: --shadow-of profile '{args.shadow_of}' not found\n"
            )
            return 2
        binding_src = shadow_profile
        api_key_field = "shadow_api"
        base_field = "shadow_api_base"
        env_field = "shadow_api_env"
        extras_field = "shadow_api_extras"
        timeout_field = "shadow_api_timeout"
    else:
        binding_src = profile or {}
        api_key_field = "direct_api"
        base_field = "direct_api_base"
        env_field = "api_env"
        extras_field = "direct_api_extras"
        timeout_field = "direct_api_timeout"

    endpoint = args.endpoint or binding_src.get(base_field)
    model = args.model or binding_src.get(api_key_field)
    api_env = args.api_key_env or binding_src.get(env_field)
    if args.timeout is not None:
        timeout = args.timeout
    elif binding_src.get(timeout_field):
        timeout = float(binding_src[timeout_field])
    else:
        timeout = 120.0

    if not endpoint or not model or not api_env:
        sys.stderr.write(
            "chat_completion: missing required config (need endpoint, model, and api-key-env "
            "via --profile or via --endpoint/--model/--api-key-env flags).\n"
        )
        return 2

    api_key = os.environ.get(api_env)
    # Optional canonical-env-var fallbacks. Each entry maps a local alias
    # (the profile's `api_env`) to the provider's canonical env var, so a
    # machine that only exports the canonical name still works without
    # editing the binding file. Add new entries as needed; keep this list
    # minimal — most providers should use a single env var.
    _CANONICAL_ENV_FALLBACKS: dict[str, str] = {
        # alias -> canonical
    }
    if not api_key:
        canonical = _CANONICAL_ENV_FALLBACKS.get(api_env)
        if canonical:
            api_key = os.environ.get(canonical)
    if not api_key:
        sys.stderr.write(f"chat_completion: env var ${api_env} not set; cannot call API.\n")
        return 2

    prompt = _read_prompt(args)
    if not prompt.strip():
        sys.stderr.write("chat_completion: empty prompt.\n")
        return 4

    session_path = Path(args.session) if args.session else None
    try:
        history = _load_session(session_path) if session_path else []
    except (json.JSONDecodeError, ValueError) as e:
        sys.stderr.write(f"chat_completion: session file invalid: {e}\n")
        return 2

    # If --system is given, it replaces any existing system message at index 0;
    # otherwise the existing one (if any) stays. Without either, no system msg.
    if args.system is not None:
        history = [m for m in history if m.get("role") != "system"]
        history.insert(0, {"role": "system", "content": args.system})

    user_msg = {"role": "user", "content": prompt}
    messages = history + [user_msg]

    try:
        extras = _resolve_extras(binding_src, args.extras_json, extras_field=extras_field)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"chat_completion: --extras-json is not valid JSON: {e}\n")
        return 4

    body: dict = {"model": model, "messages": messages, "max_tokens": args.max_tokens}
    body.update(extras)

    # Optional pre-flight: refuse to send if the request would clearly bust
    # the model's context window. Estimate is rough (chars/4); the real
    # token count is provider-dependent but this catches the obvious cases
    # (a 50MB log file accidentally included via stdin).
    if args.check_context > 0:
        total_chars = sum(len(m.get("content", "")) for m in messages)
        if args.system:
            total_chars += len(args.system)
        estimated_tokens = total_chars // 4
        if estimated_tokens > args.check_context:
            sys.stderr.write(
                f"chat_completion: estimated input ≈ {estimated_tokens} tokens "
                f"(chars/4) exceeds --check-context cap {args.check_context}; "
                f"aborting before API call. Reduce input or raise the cap.\n"
            )
            return 4

    log_dir = Path(args.log_dir) if args.log_dir else DEFAULT_LOG_DIR
    log_event: dict = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "profile": args.profile,
        "shadow_of": args.shadow_of,
        "model": model,
        "endpoint": endpoint,
        "session": session_path.as_posix() if session_path else None,
        "system": args.system,
        "user_prompt": prompt,
    }
    started_at = time.monotonic()

    def _maybe_log() -> None:
        if args.log:
            log_event["latency_s"] = round(time.monotonic() - started_at, 3)
            _log_call(log_dir, log_event)

    try:
        resp = _post_with_retry(
            endpoint, body, api_key, timeout, max_attempts=args.max_attempts
        )
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            err_body = {"raw": str(e)}
        sys.stderr.write(f"chat_completion: HTTP {e.code}: {json.dumps(err_body)}\n")
        log_event.update({"status": "error", "error_kind": f"http_{e.code}"})
        _maybe_log()
        return 1
    except (TimeoutError, socket.timeout):
        sys.stderr.write(f"chat_completion: request timed out after {timeout}s\n")
        log_event.update({"status": "error", "error_kind": "timeout"})
        _maybe_log()
        return 3
    except urllib.error.URLError as e:
        sys.stderr.write(f"chat_completion: network error: {e}\n")
        log_event.update({"status": "error", "error_kind": "network", "error_message": str(e)})
        _maybe_log()
        return 1
    except json.JSONDecodeError as e:
        sys.stderr.write(f"chat_completion: response not JSON: {e}\n")
        log_event.update({"status": "error", "error_kind": "decode"})
        _maybe_log()
        return 1

    if "error" in resp:
        sys.stderr.write(f"chat_completion: API error: {json.dumps(resp['error'])}\n")
        log_event.update({"status": "error", "error_kind": "api", "error_message": resp["error"]})
        _maybe_log()
        return 1

    # Successful response: capture for logging regardless of output mode.
    try:
        choice = resp["choices"][0]
        msg = choice["message"]
        content = msg.get("content", "")
        reasoning = msg.get("reasoning_content")
        finish = choice.get("finish_reason")
    except (KeyError, IndexError) as e:
        sys.stderr.write(
            f"chat_completion: malformed response (missing choices/message/content): {e}\n"
        )
        log_event.update({"status": "error", "error_kind": "malformed_response"})
        _maybe_log()
        return 1

    log_event.update({
        "status": "ok",
        "response_content": content,
        "reasoning_content": reasoning,
        "finish_reason": finish,
        "usage": resp.get("usage"),
    })
    _maybe_log()

    # Truncation = caller-visible failure (unless --max-tokens 0 opts out).
    # Partial content still written to stdout / session so the caller can
    # recover what arrived; exit code distinguishes truncation from other
    # success/failure modes.
    truncated = finish == "length" and args.max_tokens > 0
    if truncated:
        sys.stderr.write(
            f"chat_completion: response truncated at max_tokens={args.max_tokens} "
            f"(finish_reason=length). Partial content written to stdout. "
            f"Re-run with a higher --max-tokens to recover the full response.\n"
        )
        log_event["error_kind"] = "truncated_max_tokens"
    elif finish and finish not in ("stop", "length"):
        # "length" is handled above (or silently accepted when max_tokens=0).
        # Anything else (tool_calls, content_filter, function_call, ...) is
        # unusual enough to surface but not block.
        sys.stderr.write(f"chat_completion: finish_reason={finish} (non-stop)\n")

    if args.emit_json:
        sys.stdout.write(json.dumps(resp, ensure_ascii=False))
        return 5 if truncated else 0

    if session_path is not None:
        history.append(user_msg)
        history.append({"role": "assistant", "content": content})
        try:
            _save_session(session_path, history)
        except OSError as e:
            sys.stderr.write(f"chat_completion: failed to write session file: {e}\n")
            # Don't fail the command — response is in stdout, caller can recover

    sys.stdout.write(content)
    return 5 if truncated else 0


if __name__ == "__main__":
    sys.exit(main())
