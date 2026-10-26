# Набор Claude Code для аналитика Bitrix24

Скилы, агенты и система памяти, с которыми я каждый день работаю в Claude Code.

## Установка

Нужны Claude Code и `jq` (`brew install jq`). Дальше в терминале:

```bash
git clone <ссылка на этот репозиторий> ~/claude-kit && bash ~/claude-kit/install.sh
```

Потом заполни `~/.claude/about-me.md` (прайс, опыт, кейсы) и перезапусти Claude Code.
Если у тебя уже был свой `~/.claude/CLAUDE.md`, он сохранится рядом как `CLAUDE.md.bak`.

## Что внутри

**Bitrix24**
- `bitrix24-analyst` — бизнес- и системный анализ, ТЗ, AS-IS/TO-BE, BPMN
- `bitrix24-agent` — REST API, вебхуки, OAuth, лимиты, ошибки
- `b24-grabli` — грабли с реальных внедрений: что ломается молча в БП, смарт-процессах, списках, формах

**Документы клиенту:** `prd-generator`, `user-story-writer`, `stakeholder-updates`, `process-mapper`, `doc-synthesis`, `market-research`

**Тексты:** `stop-slop` (убирает ИИ-обороты), `copywriting`, `copy-editing`

**Сайты** (вызов `/site`): `frontend-design`, `design-taste-frontend`, `emil-design-eng`, `apple-design-skill`,
`web-design-guidelines`, `mobile-native`, `page-cro`, `seo-audit`, GSAP и three.js, анимации

**Резюме и карьера:** `cv-creator`, `career-biographer`, `job-application-optimizer`, `review-resume`

**Прочее:** `context-engineering`, `find-skills`, `market-dynamics`

**Агенты** (Claude сам зовёт по описанию, или попроси по имени)
- `tz-critic` — ищет дыры в ТЗ перед отправкой заказчику
- `portal-scout` — экспресс-аудит портала по вебхуку, отчёт в Obsidian
- `config-verifier` — сверяет настроенный портал с ТЗ перед сдачей
- `lead-estimator` — оценка заказа с Kwork/FL: часы, риски, цена, черновик отклика
- `text-critic` — вычищает ИИ-обороты из писем и откликов

Агенты по порталу ходят только через `~/.claude/b24-tools/b24_snapshot.py` и только на чтение.
Вебхук кладёшь в файл `.env` строкой `B24_WEBHOOK=https://...` и даёшь агенту путь к нему.

**Память**
- `handoff` + два хука: перед сжатием контекста Claude напоминает себе записать заметку в
  `<проект>/.claude/handoffs/`, а в новой сессии сам показывает последние заметки
- `CLAUDE.md` — правила работы со мной и с волтом Obsidian (`~/Obsidian`, папки создаются сами)
- auto-memory включена в Claude Code по умолчанию, отдельно ставить не надо

**Плагины:** `impeccable` (дизайн интерфейсов), `ponytail` (код без лишнего). Ставятся скриптом;
вручную:

```bash
claude plugin marketplace add pbakaus/impeccable && claude plugin install impeccable@impeccable
```

Word, Excel, PowerPoint и PDF уже встроены в Claude, их ставить не надо.
