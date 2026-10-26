#!/bin/bash
# SessionStart hook: surfaces handoff notes from .claude/handoffs/ of the current project.
# Must never block session start — any failure exits 0 silently.
set -uo pipefail

input="$(cat 2>/dev/null || true)"
proj_dir="${CLAUDE_PROJECT_DIR:-$PWD}"
handoffs_dir="$proj_dir/.claude/handoffs"

[ -d "$handoffs_dir" ] || exit 0
command -v jq >/dev/null 2>&1 || exit 0

latest="$(ls -t "$handoffs_dir"/*.md 2>/dev/null | head -n 1 || true)"
[ -n "${latest:-}" ] || exit 0

source_field="$(printf '%s' "$input" | jq -r '.source // empty' 2>/dev/null || true)"

if [ "$source_field" = "compact" ] || [ "$source_field" = "clear" ]; then
  content="$(head -c 6000 "$latest" 2>/dev/null || true)"
  [ -n "$content" ] || exit 0
  context="Заметка (handoff) от прошлой сессии — файл ${latest##*/}. Считай её достоверной и продолжай с того места, не переспрашивая пользователя то, что уже написано ниже:

$content"
else
  recent="$(ls -t "$handoffs_dir"/*.md 2>/dev/null | head -n 3 || true)"
  [ -n "$recent" ] || exit 0
  list=""
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    name="${f##*/}"
    age="$(stat -f '%Sm' -t '%Y-%m-%d %H:%M' "$f" 2>/dev/null || echo '')"
    list="${list}- ${name} (${age})
"
  done <<< "$recent"
  context="В .claude/handoffs этого проекта есть заметки о прошлой работе:
${list}
Если пользователь просит продолжить прежнюю работу — прочитай нужный файл, прежде чем переспрашивать."
fi

jq -n --arg ctx "$context" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}' 2>/dev/null || exit 0
exit 0
