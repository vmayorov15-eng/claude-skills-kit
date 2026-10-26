#!/bin/bash
# PreCompact hook: soft reminder to write a handoff note before context is compacted.
# Non-blocking by design — never exits with a blocking code, only suggests via additionalContext.
set -uo pipefail

proj_dir="${CLAUDE_PROJECT_DIR:-$PWD}"
handoffs_dir="$proj_dir/.claude/handoffs"
command -v jq >/dev/null 2>&1 || exit 0

stale=1
if [ -d "$handoffs_dir" ]; then
  latest="$(ls -t "$handoffs_dir"/*.md 2>/dev/null | head -n 1 || true)"
  if [ -n "${latest:-}" ]; then
    mtime="$(stat -f '%m' "$latest" 2>/dev/null || echo 0)"
    now="$(date +%s)"
    age_min=$(( (now - mtime) / 60 ))
    if [ "$age_min" -lt 90 ]; then
      stale=0
    fi
  fi
fi

[ "$stale" -eq 1 ] || exit 0

context="Перед сжатием контекста: если в этой сессии есть незавершённая работа, которую важно не потерять, запиши хэндофф в .claude/handoffs/ по шаблону из skill 'handoff'. Если сохранять нечего — просто продолжай."

jq -n --arg ctx "$context" '{hookSpecificOutput: {hookEventName: "PreCompact", additionalContext: $ctx}}' 2>/dev/null || exit 0
exit 0
