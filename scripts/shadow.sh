#!/usr/bin/env bash
# Fire a sampled, backgrounded shadow API call. Returns immediately.
#
# Usage:
#   echo "<prompt>" | scripts/shadow.sh <profile> [--max-tokens N]
#
# Reads the profile's shadow_api / shadow_api_base / shadow_api_env /
# shadow_api_extras / shadow_api_timeout from profile/models.toml (the
# gitignored bindings file) via chat_completion.py --shadow-of <profile>.
# Logs land in ~/.cache/atelier/llm_calls/<date>.jsonl with
# shadow_of=<profile> so the entry is separable from primary calls.
#
# Sampling: $ATELIER_SHADOW_RATE (integer percent, 0..100). Default 10.
#   100 = always fire. 10 = fire one in ten calls. 0 = disable.
#
# The shadow call is backgrounded (nohup + disown) so the orchestrator
# never blocks waiting for the secondary leg. Stdin is consumed by either
# the API call (if sampled) or /dev/null (if not), so the caller can pipe
# the prompt without worrying about either branch.
#
# Exit codes:
#   0  ok (sampled or skipped, both are normal)
#   2  bad usage (no profile name; chat_completion.py also returns 2 for
#      profile-not-found and missing api_env, but those errors land in the
#      backgrounded process and are visible only in the call log)

set -uo pipefail

PROFILE="${1:-}"
if [ -z "$PROFILE" ]; then
  echo "shadow.sh: profile name required (usage: echo '<prompt>' | shadow.sh <profile> [extra args])" >&2
  exit 2
fi
shift

RATE="${ATELIER_SHADOW_RATE:-10}"
# Validate integer percent in [0, 100]
case "$RATE" in
  ''|*[!0-9]*) echo "shadow.sh: ATELIER_SHADOW_RATE must be an integer 0..100 (got '$RATE')" >&2; exit 2 ;;
esac
if [ "$RATE" -lt 0 ] || [ "$RATE" -gt 100 ]; then
  echo "shadow.sh: ATELIER_SHADOW_RATE must be 0..100 (got $RATE)" >&2; exit 2
fi

# Sample. RANDOM gives 0..32767; modulo 100 is good enough for a 10%
# sampling decision (the tiny bias is irrelevant for this use case).
if [ "$RATE" -eq 0 ] || { [ "$RATE" -lt 100 ] && [ $((RANDOM % 100)) -ge "$RATE" ]; }; then
  cat > /dev/null  # drain stdin so caller's pipe doesn't error
  exit 0
fi

# Sampled: background the API call, return immediately.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
nohup python3 "$SCRIPT_DIR/chat_completion.py" \
  --profile "$PROFILE" --shadow-of "$PROFILE" --prompt - "$@" \
  > /dev/null 2>&1 &
disown
exit 0
