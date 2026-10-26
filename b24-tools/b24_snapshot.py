#!/usr/bin/env python3
"""Слепок портала Битрикс24 по вебхуку. Только чтение: методы вне READ_ONLY не вызываются.

  python3 b24_snapshot.py --env-file <путь к .env с B24_WEBHOOK=...> [--out файл.json]
  python3 b24_snapshot.py --env-file <путь> --call imopenlines.config.get '{"CONFIG_ID": 1}'
  B24_WEBHOOK=... python3 b24_snapshot.py
  python3 b24_snapshot.py --selftest

--call — точечный запрос для деталей, которых нет в слепке; пропускает только методы чтения
(*.get, *.list, *.fields и список READ_ONLY).

В stdout — короткая сводка в markdown, полный слепок — в JSON. Персональных данных
(ФИО, телефоны, почта) слепок не собирает — только счётчики и структуру.
"""
import argparse
import http.client
import json
import os
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

READ_ONLY = frozenset({
    "scope", "profile", "user.get", "department.get", "crm.settings.mode.get",
    "crm.type.list", "crm.item.list", "crm.item.fields", "crm.category.list", "crm.status.list",
    "crm.lead.userfield.list", "crm.deal.userfield.list", "crm.contact.userfield.list",
    "crm.company.userfield.list", "bizproc.workflow.template.list", "bizproc.workflow.instances",
    "lists.get", "imopenlines.config.list.get", "tasks.task.list",
})
BLIND_SPOTS = [
    "роботы и триггеры CRM — публичный REST их не отдаёт (только внутренний API под сессией админа)",
    "обязательность полей по стадиям — REST видит только общий признак «обязательное»",
    "права доступа (роли CRM) — проверять в интерфейсе",
    "CRM-формы и виджеты — проверять в интерфейсе",
]
BASE_ENTITIES = [(1, "Лиды", "lead"), (2, "Сделки", "deal"), (3, "Контакты", "contact"), (4, "Компании", "company")]


class B24Error(Exception):
    pass


def is_read_only(method):
    return method in READ_ONLY or (method != "batch" and method.rsplit(".", 1)[-1].lower() in ("get", "list", "fields"))


class Portal:
    def __init__(self, hook, transport=None):
        self.hook = hook if hook.endswith("/") else hook + "/"
        url = urlparse(self.hook)
        self.host, self.path = url.hostname, url.path
        self.transport = transport or self._http
        self.conn = None
        self._last = 0.0

    def _http(self, method, params):
        # одно соединение на весь слепок: через прокси TLS-рукопожатие с порталом стоит 4–20 с
        time.sleep(max(0.0, 0.5 - (time.time() - self._last)))  # лимит Б24 — 2 запроса в секунду
        self._last = time.time()
        for attempt in range(2):
            if self.conn is None:
                self.conn = http.client.HTTPSConnection(self.host, timeout=90)
            try:
                self.conn.request("POST", self.path + method + ".json", json.dumps(params).encode(),
                                  {"Content-Type": "application/json"})
                resp = self.conn.getresponse()
                raw = resp.read()
            except (http.client.HTTPException, OSError) as e:
                self.conn.close()
                self.conn = None
                if attempt:
                    return {"error": "NETWORK", "error_description": str(e)}
                continue
            try:
                return json.loads(raw.decode(errors="replace"))
            except ValueError:
                return {"error": f"HTTP {resp.status}"}

    def call(self, method, params=None):
        if not is_read_only(method):
            raise B24Error(f"{method}: не метод чтения, вызов запрещён")
        for attempt in range(5):
            t0 = time.time()
            body = self.transport(method, params or {})
            if os.environ.get("B24_DEBUG"):
                print(f"{method} start={(params or {}).get('start', 0)} {time.time() - t0:.1f}s "
                      f"{body.get('error', '')}", file=sys.stderr, flush=True)
            if body.get("error") in ("QUERY_LIMIT_EXCEEDED", "NETWORK") and attempt < 4:
                time.sleep(2 ** attempt)
                continue
            if "error" in body:
                raise B24Error(f"{method}: {body.get('error')} {body.get('error_description', '')}".strip()[:300])
            return body
        raise B24Error(f"{method}: не ответил после повторов")

    def all(self, method, params=None, pick=lambda r: r):
        out, start = [], 0
        while True:
            body = self.call(method, {**(params or {}), "start": start})
            chunk = pick(body.get("result"))
            out += chunk if isinstance(chunk, list) else []
            if body.get("next") is None:
                return out
            start = body["next"]


def stages_entity_id(etid, cat_id):
    if etid == 1:
        return "STATUS"
    if etid == 2:
        return "DEAL_STAGE" if not cat_id else f"DEAL_STAGE_{cat_id}"
    return f"DYNAMIC_{etid}_STAGE_{cat_id}"


def snapshot(p):
    snap = {"дата": date.today().isoformat(), "недоступно": {}, "слепые_зоны": BLIND_SPOTS}

    def section(name, fn):
        try:
            snap[name] = fn()
        except B24Error as e:
            snap["недоступно"][name] = str(e)

    section("права_вебхука", lambda: p.call("scope")["result"])
    section("режим_crm", lambda: {1: "классический, с лидами", 2: "простой, без лидов"}.get(
        p.call("crm.settings.mode.get")["result"], "неизвестно"))

    ids = {"все": set(), "активные": set()}

    def users():
        rows = p.all("user.get", {"ADMIN_MODE": True})
        active = [u for u in rows if u.get("ACTIVE") in (True, "Y", "1", 1)]
        ids["все"] = {str(u["ID"]) for u in rows}
        ids["активные"] = {str(u["ID"]) for u in active}
        return {"всего": len(rows), "активных": len(active),
                "активных_ни_разу_не_входили": sum(1 for u in active if not u.get("LAST_LOGIN")),
                "по_типам": dict(Counter(u.get("USER_TYPE") or "employee" for u in rows))}
    section("пользователи", users)

    def departments():
        rows = p.all("department.get")
        heads = [(d, str(d["UF_HEAD"])) for d in rows if d.get("UF_HEAD")]
        return {"всего": len(rows),
                "без_руководителя": [f"{d['ID']} {d['NAME']}" for d in rows if not d.get("UF_HEAD")],
                "руководитель_неактивен": [f"{d['ID']} {d['NAME']}" for d, h in heads
                                           if h in ids["все"] and h not in ids["активные"]],
                "руководитель_удалён": [f"{d['ID']} {d['NAME']} (id {h})" for d, h in heads
                                        if ids["все"] and h not in ids["все"]]}
    section("отделы", departments)

    entities = [(etid, title, code, {}) for etid, title, code in BASE_ENTITIES]
    try:
        for t in p.all("crm.type.list", pick=lambda r: (r or {}).get("types", [])):
            entities.append((t["entityTypeId"], t["title"], None, t))
    except B24Error as e:
        snap["недоступно"]["смарт_процессы"] = str(e)

    crm = {}
    for etid, title, code, meta in entities:
        e = {"entityTypeId": etid}
        if meta:
            e["настройки"] = {k: meta.get(k) for k in ("isCategoriesEnabled", "isStagesEnabled",
                              "isAutomationEnabled", "isBizProcEnabled", "isClientEnabled")}
        try:
            e["записей"] = p.call("crm.item.list", {"entityTypeId": etid, "select": ["id"]}).get("total")
            fields = p.call("crm.item.fields", {"entityTypeId": etid})["result"]["fields"]
            e["поля"] = [{"код": f.get("upperName") or k, "название": f.get("title"), "тип": f.get("type"),
                          "обязательное": bool(f.get("isRequired")), "множественное": bool(f.get("isMultiple")),
                          "значений_в_списке": len(f.get("items") or [])} for k, f in fields.items()]
            e["полей_всего"] = len(fields)
            e["полей_своих"] = sum(1 for k in fields if k.lower().startswith("uf"))
            if code:
                labels = {u["FIELD_NAME"]: u.get("EDIT_FORM_LABEL") for u in
                          p.all(f"crm.{code}.userfield.list", {"filter": {"LANG": "ru"}})}
                for f in e["поля"]:
                    if isinstance(labels.get(f["код"]), str) and labels[f["код"]]:
                        f["название"] = labels[f["код"]]
            if etid in (1, 3, 4):
                cats = [{"id": 0, "name": "—"}]
            else:
                cats = p.all("crm.category.list", {"entityTypeId": etid},
                             pick=lambda r: (r or {}).get("categories", []))
            if etid != 3 and etid != 4:
                e["воронки"] = [{"id": c["id"], "название": c.get("name"),
                                 "стадии": [f"{s.get('NAME')} [{s.get('SEMANTICS') or 'P'}]" for s in
                                            p.all("crm.status.list", {"filter": {"ENTITY_ID": stages_entity_id(etid, c["id"])},
                                                  "order": {"SORT": "ASC"}})]}
                                for c in cats]
        except B24Error as err:
            e["ошибка"] = str(err)
        crm[title] = e
    snap["crm"] = crm
    section("источники", lambda: [s.get("NAME") for s in
            p.all("crm.status.list", {"filter": {"ENTITY_ID": "SOURCE"}})])

    def bizproc():
        rows = p.all("bizproc.workflow.template.list",
                     {"select": ["ID", "MODULE_ID", "DOCUMENT_TYPE", "NAME", "AUTO_EXECUTE", "MODIFIED"]})
        running = p.call("bizproc.workflow.instances", {"select": ["ID"]}).get("total")
        return {"шаблонов": len(rows), "запущено_экземпляров": running,
                "по_документам": dict(Counter("/".join(str(x) for x in (t.get("DOCUMENT_TYPE") or []) if x)
                                              for t in rows)),
                "шаблоны": [{"id": t["ID"], "название": t.get("NAME"), "документ": t.get("DOCUMENT_TYPE"),
                             "автозапуск": t.get("AUTO_EXECUTE"), "изменён": t.get("MODIFIED")} for t in rows]}
    section("бизнес_процессы", bizproc)
    section("списки", lambda: {kind: [f"{x['ID']} {x['NAME']}" for x in p.all("lists.get", {"IBLOCK_TYPE_ID": kind})]
                               for kind in ("lists", "bitrix_processes")})
    section("открытые_линии", lambda: [f"{x.get('LINE_NAME')} ({'вкл' if x.get('ACTIVE') == 'Y' else 'выкл'})"
                                       for x in p.call("imopenlines.config.list.get")["result"]])
    section("задачи_открытых", lambda: p.call("tasks.task.list", {"select": ["ID"],
                                                                  "filter": {"<REAL_STATUS": 5}}).get("total"))
    return snap


def summary(host, snap):
    out = [f"# Слепок {host} — {snap['дата']}", ""]
    if "права_вебхука" in snap:
        out.append(f"Права вебхука: {', '.join(snap['права_вебхука'])}")
    if "режим_crm" in snap:
        out.append(f"Режим CRM: {snap['режим_crm']}")
    u = snap.get("пользователи")
    if u:
        out.append(f"Пользователи: {u['всего']} всего, {u['активных']} активных, "
                   f"{u['активных_ни_разу_не_входили']} активных ни разу не входили; типы {u['по_типам']}")
    d = snap.get("отделы")
    if d:
        out.append(f"Отделы: {d['всего']}; без руководителя {len(d['без_руководителя'])}; "
                   f"руководитель неактивен {len(d['руководитель_неактивен'])}; "
                   f"руководитель удалён {len(d['руководитель_удалён'])}")
        for name in (d["руководитель_удалён"] + d["руководитель_неактивен"] + d["без_руководителя"])[:15]:
            out.append(f"  - {name}")
    out += ["", "## CRM"]
    for title, e in snap.get("crm", {}).items():
        if "ошибка" in e:
            out.append(f"- {title}: ошибка — {e['ошибка']}")
            continue
        req = [f["название"] or f["код"] for f in e.get("поля", []) if f["обязательное"] and f["код"] != "OPENED"]
        out.append(f"- {title} (entityTypeId {e['entityTypeId']}): записей {e.get('записей')}, "
                   f"полей {e.get('полей_всего')} (своих {e.get('полей_своих')}), обязательных {len(req)}"
                   + (f": {', '.join(req[:12])}" if req else ""))
        for c in e.get("воронки", []):
            out.append(f"  - воронка {c['id']} «{c['название']}»: {' → '.join(c['стадии'])}")
    if snap.get("источники"):
        out.append(f"Источники: {', '.join(filter(None, snap['источники']))}")
    b = snap.get("бизнес_процессы")
    if b:
        out += ["", f"## Бизнес-процессы: {b['шаблонов']} шаблонов, запущено экземпляров {b['запущено_экземпляров']}"]
        out += [f"- {doc}: {n}" for doc, n in b["по_документам"].items()]
    for key, title in (("списки", "Списки"), ("открытые_линии", "Открытые линии")):
        if snap.get(key):
            out.append(f"{title}: {json.dumps(snap[key], ensure_ascii=False)}")
    if snap.get("задачи_открытых") is not None:
        out.append(f"Открытых задач: {snap['задачи_открытых']}")
    out += ["", "## Не видно через REST"] + [f"- {s}" for s in snap["слепые_зоны"]]
    out += [f"- {k}: {v}" for k, v in snap["недоступно"].items()]
    return "\n".join(out)


def load_hook(args):
    if args.env_file:
        for line in Path(args.env_file).expanduser().read_text().splitlines():
            if line.strip().startswith("B24_WEBHOOK="):
                return line.split("=", 1)[1].strip().strip('"')
        sys.exit(f"В {args.env_file} нет строки B24_WEBHOOK=")
    if os.environ.get("B24_WEBHOOK"):
        return os.environ["B24_WEBHOOK"]
    sys.exit("Нужен вебхук: --env-file путь/.env (строка B24_WEBHOOK=...) или переменная B24_WEBHOOK")


def selftest():
    pages = {0: {"result": [1, 2], "next": 2}, 2: {"result": [3]}}
    p = Portal("https://x.bitrix24.ru/rest/1/abc", transport=lambda m, prm: pages[prm["start"]])
    assert p.all("user.get") == [1, 2, 3], "пагинация"
    for method in ("crm.deal.update", "crm.item.add", "batch", "bizproc.workflow.start", "user.update"):
        try:
            p.call(method, {})
            raise AssertionError(f"{method}: запись должна быть запрещена")
        except B24Error:
            pass
    assert is_read_only("imopenlines.config.get") and is_read_only("crm.item.list")
    assert stages_entity_id(2, 0) == "DEAL_STAGE" and stages_entity_id(2, 4) == "DEAL_STAGE_4"
    assert stages_entity_id(1038, 7) == "DYNAMIC_1038_STAGE_7"
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--env-file")
    ap.add_argument("--out", help="куда положить полный JSON (по умолчанию рядом, в папку слепки/)")
    ap.add_argument("--call", nargs="+", metavar=("МЕТОД", "JSON"), help="один запрос чтения")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    hook = load_hook(args)
    if args.call:
        params = json.loads(args.call[1]) if len(args.call) > 1 else {}
        try:
            print(json.dumps(Portal(hook).call(args.call[0], params).get("result"), ensure_ascii=False, indent=1))
        except B24Error as e:
            sys.exit(str(e))
        return
    host = urlparse(hook).hostname or "portal"
    snap = snapshot(Portal(hook))
    out = Path(args.out) if args.out else Path(__file__).parent / "слепки" / f"{host}-{snap['дата']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snap, ensure_ascii=False, indent=1))
    print(summary(host, snap))
    print(f"\nПолный слепок: {out}")


if __name__ == "__main__":
    main()
