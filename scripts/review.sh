#!/usr/bin/env bash
# Canonical external review for reflectl system-evolution changes.
# Runs codex and/or gemini on the uncommitted diff with pre-baked prompts.
# Zero lookup: the orchestrator just runs this script — no skill, no doc.
#
# Usage:
#   bash scripts/review.sh            # both codex + gemini in parallel
#   bash scripts/review.sh codex      # codex only
#   bash scripts/review.sh gemini     # gemini only
#
# Output: reports written to zk/cache/review-<timestamp>-{codex,gemini}.md
# Exit codes: 0 all good, 1 at least one reviewer failed, 2 bad usage, 3 nothing to review.

set -uo pipefail

MODE="${1:-both}"
TS=$(date +%Y%m%d-%H%M%S)
OUT_DIR="zk/cache"
mkdir -p "$OUT_DIR"

# Abort if working tree is clean.
if git diff --quiet HEAD -- 2>/dev/null && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  echo "No uncommitted changes — nothing to review." >&2
  exit 3
fi

PROMPT='Review this diff for reflectl, a personal reflection system. The changes may be prose (protocols, agent definitions, slash commands, CLAUDE.md, handoff docs) or code (scripts, helpers). Apply the same rigor to both.

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

# Exit-code sentinels: 0 = ok, 127 = missing CLI (soft-skip), other = real failure.

run_codex() {
  local out="$OUT_DIR/review-$TS-codex.md"
  if ! command -v codex >/dev/null 2>&1; then
    echo "[codex] MISSING — skipped" >&2
    return 127
  fi
  echo "[codex] running → $out" >&2
  # codex exec review --uncommitted picks up untracked files natively.
  if codex exec review --uncommitted --full-auto > "$out" 2>&1; then
    echo "[codex] done → $out"
    return 0
  else
    local rc=$?
    echo "[codex] FAILED (exit $rc) → $out" >&2
    return $rc
  fi
}

run_gemini() {
  local out="$OUT_DIR/review-$TS-gemini.md"
  if ! command -v gemini >/dev/null 2>&1; then
    echo "[gemini] MISSING — skipped" >&2
    return 127
  fi
  echo "[gemini] running → $out" >&2
  if build_diff | gemini -m gemini-3.1-pro-preview -p "$PROMPT" -y > "$out" 2>&1; then
    echo "[gemini] done → $out"
    return 0
  else
    local rc=$?
    echo "[gemini] FAILED (exit $rc) → $out" >&2
    return $rc
  fi
}

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
  both)
    run_codex &
    CODEX_PID=$!
    run_gemini &
    GEMINI_PID=$!
    wait $CODEX_PID; CODEX_RC=$?
    wait $GEMINI_PID; GEMINI_RC=$?
    # Missing CLI (127) is a soft-skip; real failures are hard.
    HARD_FAIL=0
    RAN_ANY=0
    [ $CODEX_RC -ne 127 ]  && RAN_ANY=1
    [ $GEMINI_RC -ne 127 ] && RAN_ANY=1
    [ $CODEX_RC -ne 0 ]  && [ $CODEX_RC -ne 127 ]  && HARD_FAIL=1
    [ $GEMINI_RC -ne 0 ] && [ $GEMINI_RC -ne 127 ] && HARD_FAIL=1
    if [ $CODEX_RC -eq 127 ] && [ $GEMINI_RC -eq 127 ]; then
      echo "[review] both reviewers missing — install codex and/or gemini" >&2
      exit 1
    fi
    if [ $HARD_FAIL -eq 1 ]; then
      echo "[review] at least one present reviewer failed (codex=$CODEX_RC gemini=$GEMINI_RC)" >&2
      exit 1
    fi
    echo "[review] done (codex=$CODEX_RC gemini=$GEMINI_RC)" >&2
    exit 0
    ;;
  *)
    echo "usage: $0 [codex|gemini|both]" >&2
    exit 2
    ;;
esac
