#!/bin/bash
# Ставит скилы, память между сессиями, статус-строку и плагин impeccable в ~/.claude
set -euo pipefail
cd "$(dirname "$0")"
C="$HOME/.claude"
mkdir -p "$C/skills" "$C/hooks"

cp -R skills/. "$C/skills/"
cp hooks/*.sh "$C/hooks/" && chmod +x "$C/hooks/"*.sh
cp statusline.sh "$C/statusline.sh" && chmod +x "$C/statusline.sh"
touch "$C/CLAUDE.md"
grep -q "# Память между сессиями" "$C/CLAUDE.md" || cat memory-rules.md >> "$C/CLAUDE.md"

python3 - "$C/settings.json" <<'PY'
import json, sys, os
p = sys.argv[1]
s = json.load(open(p)) if os.path.exists(p) else {}
hooks = s.setdefault("hooks", {})
def add(event, cmd):
    lst = hooks.setdefault(event, [])
    if not any(h.get("command") == cmd for g in lst for h in g.get("hooks", [])):
        lst.append({"hooks": [{"type": "command", "command": cmd}]})
add("SessionStart", "bash ~/.claude/hooks/surface-handoff.sh 2>/dev/null || true")
add("PreCompact", "bash ~/.claude/hooks/nudge-handoff.sh 2>/dev/null || true")
s["autoMemoryEnabled"] = True
s.setdefault("statusLine", {"type": "command", "command": "bash ~/.claude/statusline.sh"})
json.dump(s, open(p, "w"), ensure_ascii=False, indent=2)
PY

if command -v claude >/dev/null; then
  claude plugin marketplace add pbakaus/impeccable || true
  claude plugin install impeccable@impeccable || true
else
  echo "Claude Code не найден — плагин impeccable поставь потом командой из README."
fi

command -v jq >/dev/null || echo "Нужен jq для памяти и статус-строки: brew install jq"
echo "Готово. Перезапусти Claude Code."
