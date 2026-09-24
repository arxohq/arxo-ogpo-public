#!/usr/bin/env python3
"""Исторические редакции Правил «бонус-малус» (постановление НБ РК № 140).

Образец — `corpus/laws/kz/ministries/so-rules/tools/build_order_states.py`.

Вход — состояния документа портала «Әділет», полученные его API 19.09.2026
(`GET /api/documents/<uuid>`, перечень — `…/versions`) и закреплённые байт в
байт: `sources/bonus-malus/api/V1600013928_<revision_date>_<uuid>.json`.
Действующая редакция (постановление АРРФР от 23.12.2025 № 82) закреплена
отдельно — `adilet-api.json`/`ru.txt` и генератор `lawgen pinning`; здесь
только ПРЕДШЕСТВУЮЩИЕ ей редакции:

  * № 102 от 23.11.2022 — Правила из пяти пунктов и приложение из
    ПЯТНАДЦАТИ строк (самый низкий класс — М, классов М1 и М2 нет);
    портал хранит два состояния (2022-11-22 и 2024-12-26) с байт в байт
    одинаковым текстом Правил — второе несёт лишь примечание о будущей
    редакции, и `--check` эту одинаковость сверяет;
  * № 87 от 27.12.2024 — Правила из пятнадцати пунктов и приложение из
    семнадцати строк, совпадающее с действующим.

Выход:
  * `sources/bonus-malus/v<начало>.txt` — извлечение текста всего документа
    тем же `extract_source_text.py --adilet-document-body`, что и `ru.txt`;
  * блок между маркерами в `sources.law`: редакция, публикация, фрагменты
    §194 пунктов Правил (`<PREFIX>_POINT_N`, локатор `article/N`) и
    приложения-таблицы (`<PREFIX>_ANNEX_TABLE`, локатор `annex/table`);
  * `sources/bonus-malus/states.json` — учёт: окна, число пунктов и строк.

  build_rules_states.py          — переписать всё перечисленное
  build_rules_states.py --check  — молча, кодом выхода

ОКНА — ПО СОСТОЯНИЯМ ПОРТАЛА, и это названная граница. Портал датирует
состояние днём изменяющего акта (`revision_date`, хранится как 18:00Z
предыдущего дня); день ввода в действие каждой редакции («по истечении десяти
календарных дней…», «по истечении трёх месяцев после дня первого официального
опубликования») ни текст, ни реквизиты ответа не называют. Окно редакции
№ 102 начато днём принятия (23.11.2022) и закрыто днём состояния № 87
(08.04.2025); окно № 87 закрыто днём принятия № 82 (23.12.2025). Между
23.12.2025 и 12.09.2026 — днём, с которого действующая редакция заведомо
действует, — пакет НЕ отвечает: подлинный день ввода № 82 не установлен
(DECISION-0333). Даты экспериментов статьи лежат вдали от границ.

ЕДИНИЦА ДЕЛЕНИЯ — ПУНКТ ПРАВИЛ. Резчик пунктов здесь свой, и он сверяется с
`lawgen`: на действующем `ru.txt` он обязан воспроизвести тексты фрагментов
`BM_POINT_1..16` из `sources.law` дословно (`--check` и запись это проверяют).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
ROOT = PKG.parents[4]
SOURCES = PKG / "sources" / "bonus-malus"
TARGET = PKG / "sources.law"
EXTRACTOR = ROOT / "corpus" / "tools" / "lib" / "extract_source_text.py"
BEGIN = "// BEGIN GENERATED BONUS MALUS STATES"
END = "// END GENERATED BONUS MALUS STATES"
RETRIEVED_AT = "2026-09-19T00:00:00Z"

#: Редакции, которые ведёт генератор: начало окна → состояние портала, конец
#: окна, символ редакции, префикс фрагментов, ожидаемые пункты и строки.
STATES = [
    {"start": "2022-11-23", "end": "2025-04-08", "revision": "2022-11-22",
     "symbol": "BONUS_MALUS_RU_2022", "prefix": "BM2022", "points": 5, "rows": 15,
     "act": "постановления Правления Агентства РК по регулированию и развитию финансового рынка от 23.11.2022 № 102",
     "same_body": "2024-12-26"},
    {"start": "2025-04-08", "end": "2025-12-23", "revision": "2025-04-07",
     "symbol": "BONUS_MALUS_RU_2025", "prefix": "BM2025", "points": 15, "rows": 17,
     "act": "постановления Правления Агентства РК по регулированию и развитию финансового рынка от 27.12.2024 № 87",
     "same_body": None},
]

sys.path.insert(0, str(ROOT / "corpus" / "tools" / "lib"))
import adilet_api  # noqa: E402

TITLE = re.compile(r"(?m)^Правила расчета (?:и применения коэффициента|класса) по системе")
BARE_ANNEX = re.compile(r"(?m)^Приложение\s*$")
POINT = re.compile(r"(?m)^(\d+)\. ")


def state_file(revision: str) -> Path:
    hits = sorted((SOURCES / "api").glob(f"V1600013928_{revision}_*.json"))
    if len(hits) != 1:
        raise SystemExit(f"build_rules_states: состояние {revision}: файлов {len(hits)}, нужен один")
    return hits[0]


def extract(api_path: Path) -> str:
    body = adilet_api.body_of(api_path.read_bytes())
    scratch = api_path.with_suffix(".body.tmp")
    out = api_path.with_suffix(".txt.tmp")
    scratch.write_bytes(body)
    try:
        result = subprocess.run([sys.executable, str(EXTRACTOR), "--adilet-document-body",
                                 str(scratch), str(out)], capture_output=True, text=True)
        if result.returncode != 0:
            raise SystemExit(f"extract_source_text: {result.stderr.strip()}")
        return out.read_text(encoding="utf-8")
    finally:
        scratch.unlink(missing_ok=True)
        out.unlink(missing_ok=True)


def rules_span(text: str) -> tuple[int, int, int]:
    """(начало Правил, начало приложения к Правилам, начало приложения к постановлению)."""
    titles = [m.start() for m in TITLE.finditer(text)]
    if not titles:
        raise SystemExit("build_rules_states: заголовок Правил не найден")
    start = titles[-1]
    bare = [m.start() for m in BARE_ANNEX.finditer(text) if m.start() > start]
    # Заголовок приложения к Правилам портал верстает по-разному: «Приложение»
    # отдельной строкой и «к Правилам расчета…» ниже (состояния 2022 и 2025)
    # либо «Приложение к Правилам» одной строкой (действующая редакция).
    heads = [b for b in bare if text[b:].split("\n", 2)[1].startswith("к Правилам")]
    heads += [m.start() for m in re.finditer(r"(?m)^Приложение к Правилам", text) if m.start() > start]
    if not heads:
        raise SystemExit("build_rules_states: приложение к Правилам не найдено")
    annex = min(heads)
    after = [b for b in bare if b > annex]
    if not after:
        raise SystemExit("build_rules_states: правая граница приложения не найдена")
    return start, annex, after[0]


def points_of(text: str, start: int, annex: int) -> list[tuple[str, str]]:
    body = text[start:annex]
    heads = list(POINT.finditer(body))
    out = []
    for i, m in enumerate(heads):
        stop = heads[i + 1].start() if i + 1 < len(heads) else len(body)
        out.append((m.group(1), body[m.start():stop].rstrip("\n")))
    return out


def annex_rows(annex_text: str) -> int:
    return sum(1 for line in annex_text.splitlines() if re.fullmatch(r"Класс [0-9М1-3M]+", line.strip()))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def lawtext(text: str) -> str:
    return text.replace('"""', '\\"\\"\\"')


def fragment(symbol: str, edition: str, kind: str, locator: str, text: str) -> str:
    return (f"fragment {symbol} in {edition} {{\n    kind {kind};\n    locator \"{locator}\";\n"
            f"    text ru-KZ official \"\"\"{lawtext(text)}\"\"\";\n"
            f"    content_hash \"sha256:{sha(text)}\";\n}}\n")


def check_splitter_against_lawgen(problems: list[str]) -> None:
    """Резчик обязан воспроизвести фрагменты действующей редакции дословно."""
    text = (SOURCES / "ru.txt").read_text(encoding="utf-8")
    start, annex, _ = rules_span(text)
    mine = dict(points_of(text, start, annex))
    src = TARGET.read_text(encoding="utf-8")
    for number, body in mine.items():
        m = re.search(rf'fragment BM_POINT_{number} in BONUS_MALUS_RU \{{.*?text ru-KZ official """(.*?)""";',
                      src, re.S)
        if m is None:
            problems.append(f"lawgen: нет фрагмента BM_POINT_{number}")
        elif m.group(1) != body:
            problems.append(f"lawgen: текст пункта {number} расходится с BM_POINT_{number}")
    if len(mine) != 16:
        problems.append(f"lawgen: пунктов действующей редакции {len(mine)}, ожидалось 16")


def render() -> tuple[dict[str, str], str, dict, list[str]]:
    problems: list[str] = []
    check_splitter_against_lawgen(problems)
    files: dict[str, str] = {}
    block: list[str] = []
    accounting: dict = {"retrieved_at": RETRIEVED_AT, "editions": []}
    for st in STATES:
        api_path = state_file(st["revision"])
        document = json.loads(api_path.read_text(encoding="utf-8"))["document"]
        text = extract(api_path)
        start, annex, right = rules_span(text)
        points = points_of(text, start, annex)
        annex_text = text[annex:right]
        rows = annex_rows(annex_text)
        if [n for n, _ in points] != [str(i) for i in range(1, st["points"] + 1)]:
            problems.append(f"{st['start']}: пункты {[n for n, _ in points]}, ожидалось 1..{st['points']}")
        if rows != st["rows"]:
            problems.append(f"{st['start']}: строк приложения {rows}, ожидалось {st['rows']}")
        if st["same_body"]:
            twin = extract(state_file(st["same_body"]))
            s2, a2, r2 = rules_span(twin)
            if twin[s2:r2] != text[start:right]:
                problems.append(f"{st['start']}: состояние {st['same_body']} несёт другой текст Правил")
        rel = f"sources/bonus-malus/v{st['start']}.txt"
        files[rel] = text
        sym, pre = st["symbol"], st["prefix"]
        block.append(
            f"// Редакция Правил в редакции {st['act']}: состояние портала «Әділет»\n"
            f"// с revision_date {st['revision']} (документ {document['id']}). Окно — по\n"
            f"// состояниям портала, см. заголовок генератора и DECISION-0333.\n"
            f"edition {sym} of BONUS_MALUS {{\n"
            f"    label ru-KZ official \"Правила в редакции {st['act']} (состояние портала с {st['start']})\";\n"
            f"    language ru-KZ;\n    officiality official;\n"
            f"    materialization_status PINNED_UNOFFICIAL_COPY;\n"
            f"    adopted @2016-05-30;\n    in_force [@{st['start']}, @{st['end']});\n}}\n\n"
            f"publication {sym}_TEXT of {sym} {{\n"
            f"    media_type \"text/plain; charset=utf-8\";\n"
            f"    uri \"https://adilet.zan.kz/api/documents/{document['id']}\";\n"
            f"    retrieved_at @{RETRIEVED_AT};\n"
            f"    content_hash \"sha256:{sha(text)}\";\n    local_path \"{rel}\";\n}}\n")
        for number, body in points:
            block.append(fragment(f"{pre}_POINT_{number}", sym, "paragraph", f"article/{number}", body))
        block.append(fragment(f"{pre}_ANNEX_TABLE", sym, "annex", "annex/table", annex_text))
        accounting["editions"].append({
            "edition": sym, "in_force": [st["start"], st["end"]], "portal_revision": st["revision"],
            "document": document["id"], "text": rel, "points": len(points), "annex_rows": rows,
            "same_rules_body_as_portal_revision": st["same_body"]})
    return files, "\n".join(block), accounting, problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files, block, accounting, problems = render()
    drift = len(problems)
    for line in problems:
        print(f"build_rules_states: {line}")
    for rel, body in files.items():
        target = PKG / rel
        if args.check:
            if not target.exists() or target.read_text(encoding="utf-8") != body:
                print(f"build_rules_states: {rel} расходится"); drift += 1
        else:
            target.write_text(body, encoding="utf-8")
    acc = SOURCES / "states.json"
    payload = json.dumps(accounting, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not acc.exists() or acc.read_text(encoding="utf-8") != payload:
            print("build_rules_states: states.json расходится"); drift += 1
    else:
        acc.write_text(payload, encoding="utf-8")
    generated = BEGIN + "\n" + block + END
    text = TARGET.read_text(encoding="utf-8")
    i, j = text.find(BEGIN), text.find(END)
    if i < 0 or j < 0:
        raise SystemExit(f"build_rules_states: в {TARGET.name} нет маркеров")
    if args.check:
        if text[i:j + len(END)] != generated:
            print("build_rules_states: блок в sources.law расходится"); drift += 1
        if not drift:
            print(f"build_rules_states: {len(files)} состояний, расхождений нет")
    else:
        TARGET.write_text(text[:i] + generated + text[j + len(END):], encoding="utf-8")
        print("состояния Правил № 140 записаны:", len(files))
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
