#!/usr/bin/env bash
# Canonical external review for atelier system-evolution changes.
# Runs the external-reviewer role (codex CLI + a direct-api leg) on the
# uncommitted diff with pre-baked prompts. Bindings are resolved from
# `harness/models.toml` (committed schema) + `profile/models.toml`
# (gitignored bindings). The voices composition (which two model
# identities pair on this role) is read from `harness/agents.toml`
# at run time, so the script stays in sync if the voices is rebound.
# Zero lookup at the call site: the orchestrator just runs this script
# — no skill, no doc.
#
# Usage:
#   bash scripts/review.sh             # codex + direct-api in parallel
#   bash scripts/review.sh codex       # codex only
#   bash scripts/review.sh direct      # direct-api only
#   bash scripts/review.sh gemini      # legacy reviewer (kept for users
#                                      # with the gemini CLI; not part
#                                      # of the external-reviewer voices)
#
# Output: reports written to $OV/cache/review-<timestamp>-{codex,direct,gemini}.md
#         stderr/warnings land in   $OV/cache/review-<timestamp>-{codex,direct,gemini}.md.err
# Exit codes:
#   0   all good
#   1   at least one reviewer failed
#   2   bad usage / $OV unset
#   3   nothing to review
#   4   payload exceeds ATELIER_REVIEW_MAX_BYTES (likely accidental large untracked file)

set -uo pipefail

# Refuse to fall back to a relative 'zk/' path because that silently creates
# a stray directory wherever the script runs (mirrors the rule enforced for
# python scripts via scripts/_paths.vault_root()).
if [ -z "${OV:-}" ]; then
  echo "review.sh: \$OV not set. Set it to your vault root before running this script (e.g., 'export OV=\"\$HOME/zk\"')." >&2
  exit 2
fi

MODE="${1:-both}"
TS=$(date +%Y%m%d-%H%M%S)
OUT_DIR="${OV%/}/cache"

# Resolve external-reviewer's bound voices from harness/agents.toml. The
# `voices` field is a keyed inline table; we read each leg by name (direct,
# codex) so reordering or adding a future leg does not break the script.
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)
EXT_VOICES=$(python3 - "$REPO_ROOT/harness/agents.toml" <<'PY'
import sys, tomllib
data = tomllib.loads(open(sys.argv[1], "rb").read().decode("utf-8"))
voices = (data.get("agents", {}).get("external-reviewer", {}) or {}).get("voices") or {}
if not isinstance(voices, dict) or not voices:
    sys.stderr.write("review.sh: harness/agents.toml has no [agents.external-reviewer].voices table\n")
    sys.exit(2)
direct = voices.get("direct", "")
codex = voices.get("codex", "")
print(f"{direct}\t{codex}")
PY
) || exit $?
DIRECT_MODEL=$(printf '%s' "$EXT_VOICES" | cut -f1)
CODEX_MODEL=$(printf '%s' "$EXT_VOICES" | cut -f2)
if [ -z "${DIRECT_MODEL:-}" ] || [ -z "${CODEX_MODEL:-}" ]; then
  echo "review.sh: external-reviewer voices missing direct or codex leg (got direct='$DIRECT_MODEL', codex='$CODEX_MODEL')" >&2
  exit 2
fi

# For the codex leg we also need the codex-side model id and reasoning effort
# (e.g., openai/gpt-5.5, "high"), which live in profile/models.toml under
# [models.$CODEX_MODEL]. Schema declarations in harness/models.toml are
# identity-only; the bindings are gitignored, so resolve at run time.
CODEX_MODEL_INFO=$(python3 - "$REPO_ROOT" "$CODEX_MODEL" <<'PY'
import sys, tomllib
from pathlib import Path
root, name = Path(sys.argv[1]), sys.argv[2]
schema = tomllib.loads((root / "harness" / "models.toml").read_text("utf-8"))
if name not in (schema.get("models") or {}):
    sys.stderr.write(f"review.sh: model `{name}` missing from harness/models.toml\n")
    sys.exit(2)
bindings_path = root / "profile" / "models.toml"
bindings = {}
if bindings_path.exists():
    bindings = tomllib.loads(bindings_path.read_text("utf-8"))
entry = (bindings.get("models", {}) or {}).get(name) or {}
codex = entry.get("codex") or ""
effort = entry.get("codex_reasoning_effort") or ""
print(f"{codex}\t{effort}")
PY
) || exit $?
CODEX_API_MODEL=$(printf '%s' "$CODEX_MODEL_INFO" | cut -f1)
CODEX_REASONING=$(printf '%s' "$CODEX_MODEL_INFO" | cut -f2)

# Default payload cap: 400KB (~100K tokens at chars/4). Set to 0 to disable.
# Catches the obvious failure mode: a fresh log/dump file accidentally left
# untracked is included verbatim by build_diff and balloons the API request.
PAYLOAD_CAP="${ATELIER_REVIEW_MAX_BYTES:-409600}"
mkdir -p "$OUT_DIR"

# Abort if working tree is clean.
if git diff --quiet HEAD -- 2>/dev/null && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  echo "No uncommitted changes — nothing to review." >&2
  exit 3
fi

# Pre-flight: estimate payload bytes (prompt + diff + untracked content)
# and bail with diagnostic before launching anything expensive.
estimate_payload_bytes() {
  local total=0
  total=$(( total + ${#PROMPT} ))
  local diff_bytes
  diff_bytes=$(git diff HEAD | wc -c | tr -d ' ')
  total=$(( total + diff_bytes ))
  local f bytes
  while IFS= read -r f; do
    [ -z "$f" ] || [ ! -f "$f" ] && continue
    bytes=$(wc -c < "$f" | tr -d ' ')
    total=$(( total + bytes ))
  done < <(git ls-files --others --exclude-standard)
  echo "$total"
}

check_payload_size() {
  if [ "$PAYLOAD_CAP" -le 0 ]; then
    return 0
  fi
  local size
  size=$(estimate_payload_bytes)
  if [ "$size" -le "$PAYLOAD_CAP" ]; then
    return 0
  fi
  cat <<EOF >&2
[review] estimated payload size $size bytes exceeds cap $PAYLOAD_CAP bytes.
[review] (Set ATELIER_REVIEW_MAX_BYTES=0 to disable, or raise the cap if intentional.)
[review] Largest untracked files (drop or .gitignore them if accidental):
EOF
  while IFS= read -r f; do
    [ -f "$f" ] && printf "  %10d bytes  %s\n" "$(wc -c < "$f" | tr -d ' ')" "$f"
  done < <(git ls-files --others --exclude-standard) | sort -rn | head -10 >&2
  return 4
}

PROMPT='Review this diff for atelier, a personal reflection system. The changes may be prose (protocols, agent definitions, slash commands, CLAUDE.md, handoff docs) or code (scripts, helpers). Apply the same rigor to both.

Check for:
1. Cross-file consistency — do all path references agree after renames?
2. Internal coherence — do new or modified protocols reinforce or contradict each other?
3. Overclaims — any load-bearing claim without supporting evidence in the repo?
4. Forward compatibility — does this block or enable the next phase?

Return issues grouped as BLOCKER / SHOULD-FIX / NICE-TO-HAVE with file:line pointers.
End with overall verdict: APPROVED / APPROVED_WITH_NOTES / NEEDS_REVISION / REJECTED.'

# Build a diff that includes untracked files (as synthetic new-file blocks)
# so newly added commands/scripts/protocols actually get reviewed.
build_diff() {
  git diff HEAD
  local f lines
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    lines=$(wc -l < "$f" | tr -d ' ')
    printf 'diff --git a/%s b/%s\nnew file mode 100644\n--- /dev/null\n+++ b/%s\n@@ -0,0 +1,%s @@\n' "$f" "$f" "$f" "$lines"
    awk '{print "+" $0}' "$f"
  done < <(git ls-files --others --exclude-standard)
}

# Exit-code sentinels: 0 = ok, 127 = missing CLI / config (soft-skip), other = real failure.

run_codex() {
  local out="$OUT_DIR/review-$TS-codex.md"
  local err="$out.err"
  if ! command -v codex >/dev/null 2>&1; then
    echo "[codex] MISSING — skipped" >&2
    return 127
  fi
  echo "[codex] running ($CODEX_MODEL → $CODEX_API_MODEL, reasoning=${CODEX_REASONING:-default}) → $out (errors → $err)" >&2
  # codex exec review --uncommitted picks up untracked files natively.
  # Model identity from external-reviewer voices in harness/agents.toml;
  # provider model id + reasoning effort from profile/models.toml.
  # The custom review prompt ($PROMPT) is piped on stdin via the `-` PROMPT
  # arg per `codex exec review --help`. (Earlier --full-auto flag was
  # invalid for the review subcommand; codex was running its built-in rubric
  # instead of ours, silently.)
  local codex_args=(exec review --uncommitted)
  [ -n "$CODEX_API_MODEL" ] && codex_args+=(-m "$CODEX_API_MODEL")
  [ -n "$CODEX_REASONING" ] && codex_args+=(-c "model_reasoning_effort=\"$CODEX_REASONING\"")
  codex_args+=(-)
  printf '%s' "$PROMPT" | codex "${codex_args[@]}" > "$out" 2> "$err"
  local rc=$?
  if [ $rc -eq 0 ]; then
    echo "[codex] done → $out"
    return 0
  fi
  echo "[codex] FAILED (exit $rc) → $out (stderr: $err)" >&2
  return $rc
}

run_gemini() {
  local out="$OUT_DIR/review-$TS-gemini.md"
  local err="$out.err"
  if ! command -v gemini >/dev/null 2>&1; then
    echo "[gemini] MISSING — skipped" >&2
    return 127
  fi
  echo "[gemini] running → $out (errors → $err)" >&2
  # Model choice for the Gemini CLI is read from $ATELIER_GEMINI_MODEL
  # (override) or falls back to the CLI's own default. Don't bake the model
  # version into the committed script.
  local gemini_model="${ATELIER_GEMINI_MODEL:-}"
  local gemini_args=()
  [ -n "$gemini_model" ] && gemini_args+=(-m "$gemini_model")
  build_diff | gemini "${gemini_args[@]}" -p "$PROMPT" -y > "$out" 2> "$err"
  local rc=$?
  if [ $rc -eq 0 ]; then
    echo "[gemini] done → $out"
    return 0
  fi
  echo "[gemini] FAILED (exit $rc) → $out (stderr: $err)" >&2
  return $rc
}

run_direct_api() {
  local out="$OUT_DIR/review-$TS-direct.md"
  local err="$out.err"
  echo "[direct-api] running ($DIRECT_MODEL) → $out (errors → $err)" >&2
  # Delegates to chat_completion.py with the external-reviewer's direct-api
  # leg ($DIRECT_MODEL, resolved from external-reviewer.voices in
  # harness/agents.toml). Provider bindings (model, endpoint, env var,
  # reasoning extras) live in the gitignored profile/models.toml.
  # chat_completion.py exits 2 when the api_env is unset — we treat that
  # as a soft-skip (127) here. System-review must NEVER be capped: pass
  # --max-tokens 0 to omit the cap from the request entirely (provider's
  # model maximum applies). Capping the safety net of the evolution loop
  # silently truncates real findings; that is the worst trade in this codebase.
  local body
  body="$PROMPT"$'\n\n'"$(build_diff)"
  printf '%s' "$body" | python3 scripts/chat_completion.py \
      --model "$DIRECT_MODEL" --max-tokens 0 --prompt - > "$out" 2> "$err"
  local rc=$?
  if [ $rc -eq 0 ]; then
    echo "[direct-api] done → $out"
    return 0
  fi
  if [ $rc -eq 2 ]; then
    echo "[direct-api] config missing (api_env unset) — skipped (stderr: $err)" >&2
    return 127
  fi
  if [ $rc -eq 5 ]; then
    echo "[direct-api] TRUNCATED at max_tokens — partial review in $out (stderr: $err; raise cap and re-run)" >&2
    return $rc
  fi
  echo "[direct-api] FAILED (exit $rc) → $out (stderr: $err)" >&2
  return $rc
}

check_payload_size || exit $?

case "$MODE" in
  codex)
    run_codex; rc=$?
    [ $rc -eq 127 ] && { echo "[review] codex missing — nothing ran" >&2; exit 1; }
    exit $rc
    ;;
  gemini)
    run_gemini; rc=$?
    [ $rc -eq 127 ] && { echo "[review] gemini missing — nothing ran" >&2; exit 1; }
    exit $rc
    ;;
  direct)
    run_direct_api; rc=$?
    [ $rc -eq 127 ] && { echo "[review] direct-api config missing — nothing ran" >&2; exit 1; }
    exit $rc
    ;;
  both)
    # external-reviewer role: codex CLI + direct-api leg, run in parallel.
    run_codex &
    CODEX_PID=$!
    run_direct_api &
    DIRECT_PID=$!
    wait $CODEX_PID; CODEX_RC=$?
    wait $DIRECT_PID; DIRECT_RC=$?
    # Missing CLI/config (127) is a soft-skip; real failures are hard.
    HARD_FAIL=0
    [ $CODEX_RC -ne 0 ]  && [ $CODEX_RC -ne 127 ]  && HARD_FAIL=1
    [ $DIRECT_RC -ne 0 ] && [ $DIRECT_RC -ne 127 ] && HARD_FAIL=1
    if [ $CODEX_RC -eq 127 ] && [ $DIRECT_RC -eq 127 ]; then
      echo "[review] both reviewers unavailable — install codex and/or configure direct-api binding" >&2
      exit 1
    fi
    if [ $HARD_FAIL -eq 1 ]; then
      echo "[review] at least one reviewer failed (codex=$CODEX_RC direct=$DIRECT_RC)" >&2
      exit 1
    fi
    echo "[review] done (codex=$CODEX_RC direct=$DIRECT_RC)" >&2
    exit 0
    ;;
  *)
    echo "usage: $0 [codex|direct|gemini|both]" >&2
    exit 2
    ;;
esac
