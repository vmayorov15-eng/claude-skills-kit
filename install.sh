#!/bin/bash
# Ставит скилы, агентов, хуки памяти, статус-строку и плагины в ~/.claude
set -euo pipefail
cd "$(dirname "$0")"
C="$HOME/.claude"
mkdir -p "$C/skills" "$C/agents" "$C/hooks" "$C/b24-tools/слепки"

cp -R skills/. "$C/skills/"
cp agents/*.md "$C/agents/"
cp hooks/*.sh "$C/hooks/" && chmod +x "$C/hooks/"*.sh
cp b24-tools/*.py "$C/b24-tools/"
cp statusline.sh "$C/statusline.sh" && chmod +x "$C/statusline.sh"
[ -f "$C/CLAUDE.md" ] && cp "$C/CLAUDE.md" "$C/CLAUDE.md.bak" && echo "Старый CLAUDE.md сохранён как CLAUDE.md.bak"
cp CLAUDE.md "$C/CLAUDE.md"
[ -f "$C/about-me.md" ] || cp about-me.md "$C/about-me.md"

VAULT="$HOME/Obsidian"
mkdir -p "$VAULT"/{"01 Клиенты","02 Решения","03 Встречи","04 Документы","06 Мои проекты",Шаблоны}
for f in vault-templates/*.md; do [ -f "$VAULT/Шаблоны/${f##*/}" ] || cp "$f" "$VAULT/Шаблоны/"; done

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
s.setdefault("statusLine", {"type": "command", "command": "bash ~/.claude/statusline.sh"})
json.dump(s, open(p, "w"), ensure_ascii=False, indent=2)
PY

if command -v claude >/dev/null; then
  claude plugin marketplace add pbakaus/impeccable || true
  claude plugin install impeccable@impeccable || true
  claude plugin marketplace add DietrichGebert/ponytail || true
  claude plugin install ponytail@ponytail || true
else
  echo "Claude Code не найден — плагины поставь потом командами из README."
fi

command -v jq >/dev/null || echo "Нужен jq для хуков памяти и статус-строки: brew install jq"
echo "Готово. Заполни ~/.claude/about-me.md и перезапусти Claude Code."
