#!/usr/bin/env python3
"""PreToolUse-хук для portal-scout и config-verifier: к порталу — только через b24_snapshot.py.

Блокирует (exit 2) Bash-команды с сетевыми вызовами и чтением вебхука в обход скрипта.
Проверка: python3 guard_b24.py selftest
"""
import json
import re
import sys

SCRIPT = "python3 ~/.claude/b24-tools/b24_snapshot.py"
NETWORK = re.compile(r"curl|wget|urlopen|urllib|requests\.|http\.client|httpx|socket|/rest/", re.I)
SECRET = re.compile(r"\.env\b|B24_WEBHOOK")
CHAINING = re.compile(r"[;|&`]|\$\(")


def verdict(command):
    if NETWORK.search(command):
        return "к порталу — только через b24_snapshot.py (--call для точечных запросов чтения)"
    if SECRET.search(command) and (not command.startswith(SCRIPT) or CHAINING.search(command)):
        return "вебхук читает только b24_snapshot.py — передай ему --env-file, сам файл не открывай"
    return None


def selftest():
    assert verdict(f"{SCRIPT} --env-file /x/.env") is None
    assert verdict(f"{SCRIPT} --env-file /x/.env --call crm.item.list '{{}}'") is None
    assert verdict("python3 -c \"import json; print(1)\"") is None
    assert verdict("curl https://x.bitrix24.ru/rest/1/abc/crm.deal.update") is not None
    assert verdict("python3 -c 'import urllib.request'") is not None
    assert verdict("cat /x/.env") is not None
    assert verdict(f"{SCRIPT} --env-file /x/.env; cat /x/.env") is not None
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        selftest()
        sys.exit(0)
    tool_input = json.load(sys.stdin).get("tool_input") or {}
    path = tool_input.get("file_path", "")
    reason = verdict(tool_input.get("command", "")) or (
        "вебхук читает только b24_snapshot.py — сам .env не открывай" if SECRET.search(path) else None)
    if reason:
        print(f"Заблокировано: {reason}", file=sys.stderr)
        sys.exit(2)
