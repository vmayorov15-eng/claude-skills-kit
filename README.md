# Скилы Claude Code: дизайн, тексты, память

Общий набор скилов для Claude Code и память между сессиями.

## Установка

Нужны Claude Code и `jq` (`brew install jq`). В терминале:

```bash
git clone https://github.com/vmayorov15-eng/claude-skills-kit ~/claude-kit && bash ~/claude-kit/install.sh
```

Или из архива: распаковать и запустить `bash <папка>/install.sh`. Потом перезапустить Claude Code.

## Что внутри

**Память между сессиями**
- auto-memory включается в настройках: Claude сам запоминает факты о тебе и твоих задачах
  и помнит их в следующих чатах
- в `~/.claude/CLAUDE.md` дописываются правила, когда и что запоминать (твой файл не стирается)
- скил `handoff` + два хука: перед сжатием контекста Claude записывает заметку о незавершённой
  работе в `<проект>/.claude/handoffs/`, а в новой сессии сам её показывает

**Дизайн сайтов и интерфейсов** (все разом — командой `/site`)
`frontend-design`, `design-taste-frontend`, `emil-design-eng`, `apple-design-skill`,
`web-design-guidelines`, `mobile-native`, плагин `impeccable`

**Анимация и 3D:** GSAP (`gsap-*`), three.js (`threejs-*`), `animation-performance`, `find-animation-opportunities`

**Тексты:** `stop-slop` (убирает ИИ-обороты), `copywriting`, `copy-editing`

**Сайт продаёт и находится:** `page-cro`, `seo-audit`

**Общее:** `doc-synthesis` (выжимки из документов), `market-research` (анализ рынка и конкурентов),
`context-engineering`, `find-skills` (поиск новых скилов)

Плагин вручную:

```bash
claude plugin marketplace add pbakaus/impeccable && claude plugin install impeccable@impeccable
```

Word, Excel, PowerPoint и PDF уже встроены в Claude, их ставить не надо.
