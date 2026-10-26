#!/usr/bin/env python3
"""
Разбор выгрузки шаблона бизнес-процесса Bitrix24 (.bpt).

Файл .bpt — это zlib-сжатая PHP-сериализация. Тело схемы через REST не отдаётся,
поэтому экспорт из конструктора — единственный способ разобрать процесс машинно.

Использование:
    python bpt_parse.py файл.bpt              # дерево шагов и сводка дефектов
    python bpt_parse.py файл.bpt --json       # машинночитаемый вывод
    python bpt_parse.py папка/ --json         # разбор всех .bpt в папке

Зависимость: pip install phpserialize
"""

import sys, os, json, re, zlib
from collections import Counter

try:
    import phpserialize
except ImportError:
    sys.exit("Нужен phpserialize:  pip install phpserialize")

# Активити, на которых процесс ждёт человека
WAIT_TYPES = {
    'ApproveActivity', 'RequestInformationActivity',
    'RequestInformationOptionalActivity', 'ReviewActivity',
    'Task2Activity', 'TaskActivity',
}

HUMAN = {
    'ApproveActivity': 'согласование',
    'RequestInformationActivity': 'запрос данных',
    'RequestInformationOptionalActivity': 'запрос данных (необязательный)',
    'ReviewActivity': 'ознакомление',
    'Task2Activity': 'задача',
    'TaskActivity': 'задача',
    'IMNotifyActivity': 'уведомление',
    'MailActivity': 'письмо',
    'WhileActivity': 'ЦИКЛ',
    'ParallelActivity': 'ПАРАЛЛЕЛЬНО',
    'GetUserActivity': 'поиск руководителя',
    'IfElseActivity': 'условие',
    'IfElseBranchActivity': 'ветка',
    'SequenceActivity': 'блок',
    'SetVariableActivity': 'переменная',
    'SetFieldActivity': 'запись поля',
    'SetStateActivity': 'статус',
    'SetPermissionsActivity': 'права',
    'DelayActivity': 'пауза',
    'LogActivity': 'журнал',
    'RestActivity': 'вызов приложения',
    'HttpRequestActivity': 'вызов веб-сервиса',
}


def load(path):
    """Распаковать и десериализовать .bpt."""
    raw = open(path, 'rb').read()
    try:
        raw = zlib.decompress(raw)
    except zlib.error:
        pass  # некоторые выгрузки лежат без сжатия
    return phpserialize.loads(raw, decode_strings=True)


def children(node):
    ch = node.get('Children') or {}
    return list(ch.values()) if isinstance(ch, dict) else list(ch)


def walk(node, depth=0, acc=None):
    acc = acc if acc is not None else []
    acc.append((depth, node))
    for c in children(node):
        walk(c, depth + 1, acc)
    return acc


def flatten(v):
    """Все строковые значения из вложенной структуры свойств."""
    if isinstance(v, dict):
        return [x for s in v.values() for x in flatten(s)]
    if isinstance(v, list):
        return [x for s in v for x in flatten(s)]
    return [str(v)]


def has_deadline(props):
    """Проставлен ли реальный срок. Ноль и пустая строка означают его отсутствие."""
    fields = props.get('Fields') if isinstance(props.get('Fields'), dict) else {}
    for val in (props.get('OverdueDate'), props.get('TimeoutDuration'),
                fields.get('DEADLINE') if fields else None):
        s = str(val or '').strip()
        if s and s not in ('0', '0.0', 'null', 'None'):
            return True
    return False


def analyze(path):
    data = load(path)
    tpl = data.get('TEMPLATE')
    tpl = list(tpl.values())[0] if isinstance(tpl, dict) else tpl[0]
    nodes = walk(tpl)

    types = Counter(n.get('Type') for _, n in nodes)
    waits, no_deadline, loops, hardcoded = [], [], [], set()

    for depth, n in nodes:
        t, p = n.get('Type'), (n.get('Properties') or {})
        title = p.get('Title') or n.get('Name')

        if t in WAIT_TYPES:
            ok = has_deadline(p)
            waits.append({
                'тип': HUMAN.get(t, t), 'шаг': title,
                'код': n.get('Name'), 'глубина': depth, 'срок': ok,
            })
            if not ok:
                no_deadline.append(title)

        if t == 'WhileActivity':
            loops.append({'шаг': title, 'условие': str(p.get('fieldcondition') or p.get('Condition') or '')[:200]})

        for s in flatten(p):
            hardcoded.update(re.findall(r'user_(\d+)', s))

    return {
        'файл': os.path.basename(path),
        'всего_активити': len(nodes),
        'шагов_ожидания': len(waits),
        'без_срока': len(no_deadline),
        'параллельных_блоков': types.get('ParallelActivity', 0),
        'циклов': len(loops),
        'вшитых_ID': len(hardcoded),
        'состав': dict(types),
        'шаги': waits,
        'шаги_без_срока': no_deadline,
        'детали_циклов': loops,
        'переменные': list((data.get('VARIABLES') or {}).keys()),
        'константы': list((data.get('CONSTANTS') or {}).keys()),
        'параметры': list((data.get('PARAMETERS') or {}).keys()),
    }


def report(r):
    print('=' * 74)
    print(r['файл'])
    print(f"  активити: {r['всего_активити']} | шагов ожидания: {r['шагов_ожидания']} "
          f"| циклов: {r['циклов']} | параллельных блоков: {r['параллельных_блоков']}")

    flags = []
    if r['без_срока']:
        flags.append(f"БЕЗ СРОКА: {r['без_срока']} из {r['шагов_ожидания']}")
    if r['параллельных_блоков'] == 0 and r['шагов_ожидания'] > 2:
        flags.append("НЕТ ПАРАЛЛЕЛЬНЫХ СОГЛАСОВАНИЙ")
    if r['вшитых_ID']:
        flags.append(f"вшитых ID сотрудников: {r['вшитых_ID']}")
    if r['циклов']:
        flags.append(f"циклов без проверки ограничения: {r['циклов']}")
    for f in flags:
        print('  ! ' + f)

    print('\n  Шаги ожидания:')
    for w in r['шаги']:
        mark = '  ' if w['срок'] else '⚠ '
        print(f"    {mark}[{w['тип']}] {w['шаг']}"
              + ('' if w['срок'] else '   ← срок не задан'))

    if r['детали_циклов']:
        print('\n  Циклы (проверить ограничение числа кругов и выход по времени):')
        for l in r['детали_циклов']:
            print(f"    • {l['шаг']}")
            if l['условие']:
                print(f"      условие: {l['условие']}")

    if r['переменные']:
        print(f"\n  Переменные: {', '.join(r['переменные'])}")
    print()


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    target = sys.argv[1]
    as_json = '--json' in sys.argv

    paths = []
    if os.path.isdir(target):
        paths = [os.path.join(target, f) for f in sorted(os.listdir(target))
                 if not f.startswith('.')]
    else:
        paths = [target]

    results = []
    for p in paths:
        try:
            results.append(analyze(p))
        except Exception as e:
            print(f"Не удалось разобрать {os.path.basename(p)}: {e}", file=sys.stderr)

    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
        return

    for r in results:
        report(r)

    if len(results) > 1:
        print('=' * 74)
        print('СВОДКА ПО ВСЕМ СХЕМАМ')
        print(f"  активити: {sum(r['всего_активити'] for r in results)}")
        print(f"  шагов ожидания: {sum(r['шагов_ожидания'] for r in results)}, "
              f"из них без срока: {sum(r['без_срока'] for r in results)}")
        print(f"  параллельных блоков: {sum(r['параллельных_блоков'] for r in results)}")
        print(f"  циклов: {sum(r['циклов'] for r in results)}")
        print(f"  вшитых ID: {sum(r['вшитых_ID'] for r in results)}")
        print()


if __name__ == '__main__':
    main()
