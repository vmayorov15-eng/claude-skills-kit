---
name: handoff
description: Write or read a handoff note so work survives a context reset, /compact, or a new session. Use when the user says "передай контекст дальше", "запиши хэндофф", "заканчиваю на сегодня", when context is about to be compacted, or when picking up a project after a gap — read the latest handoff before asking the user to re-explain anything.
metadata:
  type: memory
---

# Handoff

A handoff is a markdown note that lets a **future session** (yours or another one) pick up
exactly where this one left off, without the user re-explaining anything. It lives in the
current project, not in global memory — it's about *this piece of work in progress*, not
about the user or the company.

Path: `.claude/handoffs/YYYY-MM-DD-короткая-тема.md` inside the project's working directory
(create the `handoffs` folder if it doesn't exist). One file per topic/session, don't append
to old ones — write a new dated file.

## When to write one

- User asks directly ("запиши хэндофф", "передай контекст", "на сегодня всё, сохрани").
- You notice the conversation is long and about to hit `/compact` or a context limit.
- Before ending a work session that isn't finished (a `SessionStart` hook may remind you if
  none exists — see below).

Don't write one for trivial or finished work — only when there's real state (decisions,
open questions, unfinished steps) that would otherwise be lost.

## Template

```markdown
# <тема одной строкой>

Дата: YYYY-MM-DD · Проект: <папка>

## Что нужно прочитать в первую очередь
<Как пользователь любит работать / что важно не забыть — 1-3 пункта>

## Цель
<Зачем это делается, в двух предложениях>

## Что уже сделано / в процессе
<Дословно, что менялось, что тестировали, что не доделано — не пересказ, а конкретика:
файлы, ссылки, цифры>

## Решения
- <решение> — источник: пользователь сказал / проверено на практике / предположение Claude
- ...

## Отклонённые варианты
- <вариант> — почему не подошёл

## Открытые вопросы
- <что нужно уточнить у пользователя или проверить>

## Ловушки
<Что выглядит нормально, но на самом деле не так — если есть>

## Следующий шаг
<Одно конкретное действие, с которого продолжать>
```

Every decision must say *how it's known* (user said it / verified / assumed) — that's what
makes the note trustworthy instead of a guess dressed up as fact.

## Reading one back

On session start (or when asked to continue prior work), check the project's
`.claude/handoffs/` for the most recent file. If it exists and this session started from a
`/compact` or `/clear`, treat it as ground truth and continue — don't re-ask the user
questions the handoff already answers. On a normal fresh start, just note it exists and offer
to continue from it if relevant.
