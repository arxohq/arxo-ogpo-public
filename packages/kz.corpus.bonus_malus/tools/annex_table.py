#!/usr/bin/env python3
"""Приложение к Правилам «бонус-малус» — разбор закреплённых байтов.

ЗАЧЕМ. Модуль `01-prilozhenie-klassy.law` переписывает таблицу приложения
нормативными фактами: семнадцать коэффициентов и восемьдесят пять переходов.
Сто два числа, набранных глазами, — ровно тот случай, где опечатка
компилируется, проходит differential и живёт до первого дела. Поэтому таблица
читается ОТДЕЛЬНО и НЕЗАВИСИМО — прямо из закреплённой публикации §194, — и
`--check` сверяет с этим чтением то, что стоит в `.law`.

Сверка идёт не с моделью, а с ИСТОЧНИКОМ: разбор ниже не знает ни одного
имени из `.law` и не читает его правил, он лишь превращает строки байтов в
таблицу. Совпадение двух независимых чтений одной публикации и есть проверка.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]

#: Состояние приложения → закреплённые байты, модуль фактов, число строк,
#: суффикс имён фактов. Редакция 2022 (постановление № 102) — пятнадцать
#: строк без М1/М2 и свой модуль; редакция 2025 (№ 87) несёт ту же таблицу,
#: что действующая, и `--check --state 2025` сверяет её с действующей.
STATES = {
    "current": (PACKAGE / "sources" / "bonus-malus" / "ru.txt",
                PACKAGE / "01-prilozhenie-klassy.law", 17, ""),
    "2022": (PACKAGE / "sources" / "bonus-malus" / "v2022-11-23.txt",
             PACKAGE / "06-redaktsiya-2022.law", 15, "2022"),
    "2025": (PACKAGE / "sources" / "bonus-malus" / "v2025-04-08.txt",
             PACKAGE / "01-prilozhenie-klassy.law", 17, ""),
}
SOURCE, MODULE, ROWS, SUFFIX = STATES["current"]

#: Начало и конец приложения К ПРАВИЛАМ в байтах публикации. Правая граница —
#: строка «Приложение» отдельной строкой: с неё начинается приложение К
#: ПОСТАНОВЛЕНИЮ (перечень утративших силу актов).
ANNEX_HEAD = re.compile(r"(?m)^Приложение(?: к Правилам|\nк Правилам)")

#: Обозначение класса в источнике → имя члена перечисления `Klass`.
#: Кириллическая «М» и латинская «M» в клетках портала стоят вперемешку; обе
#: приводятся к одному члену, и это ЕДИНСТВЕННОЕ место, где небрежность
#: вёрстки разрешена — дальше живёт символ.
NAMES = {"М2": "KlassM2", "M2": "KlassM2", "М1": "KlassM1", "M1": "KlassM1",
         "М": "KlassM", "M": "KlassM"}
NAMES.update({str(n): f"Klass{n}" for n in range(0, 14)})


def annex_text() -> str:
    text = SOURCE.read_text(encoding="utf-8")
    start = ANNEX_HEAD.search(text).start()
    stop = re.search(r"(?m)^Приложение$", text[start + 1:])
    if stop is None:
        raise SystemExit("правая граница приложения к Правилам не найдена")
    return text[start:start + stop.start()]


def parse() -> tuple[dict[str, str], dict[tuple[str, int], str]]:
    """`{класс: коэффициент}` и `{(класс, число случаев): класс}`.

    Строка приложения набрана портала столбцом: «Класс N», размер
    коэффициента, затем пять клеток перехода — 0, 1, 2, 3, «4 и более»
    страховых случая.
    """
    lines = [line.strip() for line in annex_text().splitlines() if line.strip()]
    # Строкой таблицы считается «Класс <обозначение>» и ТОЛЬКО она: шапка
    # столбцов начинается теми же буквами («Класс при заключении договора…»),
    # и признак «начинается с „Класс “» взял бы её восемнадцатой строкой.
    rows = [i for i, line in enumerate(lines)
            if line.startswith("Класс ") and line.removeprefix("Класс ").strip() in NAMES]
    if len(rows) != ROWS:
        raise SystemExit(f"строк «Класс …» в приложении: {len(rows)}, ожидалось {ROWS}")
    coefficients: dict[str, str] = {}
    transitions: dict[tuple[str, int], str] = {}
    for i in rows:
        label = lines[i].removeprefix("Класс ").strip()
        if label not in NAMES:
            raise SystemExit(f"неизвестное обозначение класса: {label!r}")
        name = NAMES[label]
        cells = lines[i + 1:i + 7]
        if len(cells) != 6:
            raise SystemExit(f"строка {label!r} короче шести клеток: {cells!r}")
        if not re.fullmatch(r"\d,\d\d", cells[0]):
            raise SystemExit(f"вторая клетка строки {label!r} не коэффициент: {cells[0]!r}")
        coefficients[name] = cells[0].replace(",", ".")
        for claims, cell in enumerate(cells[1:]):
            if cell not in NAMES:
                raise SystemExit(f"клетка перехода {label!r}/{claims}: {cell!r}")
            transitions[(name, claims)] = NAMES[cell]
    return coefficients, transitions


def module_facts() -> tuple[dict[str, str], dict[tuple[str, int], str]]:
    """То же самое, прочитанное из `assert` модуля — вторая, зависимая сторона."""
    text = MODULE.read_text(encoding="utf-8")
    named = r'(?:"[^"]*": )?' if SUFFIX else ""
    coefficients = {m.group(1): m.group(2) for m in re.finditer(
        rf"assert {named}koeffitsient_klassa\((\w+), ([\d.]+)\);", text)}
    transitions = {(m.group(1), int(m.group(2))): m.group(3) for m in re.finditer(
        rf"assert {named}perekhod_klassa\((\w+), (\d+), (\w+)\);", text)}
    return coefficients, transitions


def emit() -> str:
    coefficients, transitions = parse()
    order = list(coefficients)
    # Факты исторической редакции несут явный id (§207): те же литералы стоят
    # под якорем действующей редакции, и без id их digest был бы неоднозначен.
    def named(kind: str, *parts: str) -> str:
        return f'assert "bm{SUFFIX}-{kind}-{"-".join(parts)}": ' if SUFFIX else "assert "
    out = []
    for name in order:
        out.append(f"    {named('koef', name)}koeffitsient_klassa({name}, {coefficients[name]});")
    out.append("")
    for index, name in enumerate(order, start=1):
        out.append(f"    {named('mesto', name)}poryadok_klassa({name}, {index});")
    out.append("")
    for name in order:
        row = " ".join(f"{named('perekhod', name, str(claims))}perekhod_klassa({name}, {claims}, "
                       f"{transitions[(name, claims)]});" for claims in range(5))
        out.append(f"    {row}")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="сверить факты модуля с независимым чтением источника")
    parser.add_argument("--emit", action="store_true",
                        help="напечатать тело блока фактов из источника")
    parser.add_argument("--state", choices=sorted(STATES), default="current",
                        help="состояние приложения: действующее, 2022 (№ 102) или 2025 (№ 87)")
    args = parser.parse_args()
    global SOURCE, MODULE, ROWS, SUFFIX
    SOURCE, MODULE, ROWS, SUFFIX = STATES[args.state]
    if args.state == "2025":
        # та же таблица, что действующая: сверяется с ней, модуля своего нет
        want = parse()
        SOURCE, MODULE, ROWS, SUFFIX = STATES["current"]
        if want != parse():
            print(" РАЗОШЛОСЬ  приложение редакции 2025 отличается от действующего", file=sys.stderr)
            return 1
        if "@source(BM2025_ANNEX_TABLE)" not in MODULE.read_text(encoding="utf-8"):
            print(" РАЗОШЛОСЬ  факты действующей таблицы не закреплены якорем BM2025_ANNEX_TABLE",
                  file=sys.stderr)
            return 1
        print("        ==  приложение редакции 2025 совпадает с действующим и закреплено якорем")
        return 0
    if args.emit:
        print(emit())
        return 0
    want_k, want_t = parse()
    got_k, got_t = module_facts()
    problems = []
    for name, value in want_k.items():
        if got_k.get(name) != value:
            problems.append(f"коэффициент {name}: в модуле {got_k.get(name)!r}, "
                            f"в источнике {value!r}")
    for extra in sorted(set(got_k) - set(want_k)):
        problems.append(f"коэффициент {extra}: в модуле есть, в источнике нет")
    for key, value in want_t.items():
        if got_t.get(key) != value:
            problems.append(f"переход {key[0]}/{key[1]}: в модуле "
                            f"{got_t.get(key)!r}, в источнике {value!r}")
    for extra in sorted(set(got_t) - set(want_t)):
        problems.append(f"переход {extra[0]}/{extra[1]}: в модуле есть, в источнике нет")
    if problems:
        for line in problems:
            print(f" РАЗОШЛОСЬ  {line}", file=sys.stderr)
        return 1
    print(f"        ==  приложение «бонус-малус»: {len(want_k)} коэффициентов, "
          f"{len(want_t)} переходов — совпало с закреплёнными байтами")
    return 0


if __name__ == "__main__":
    sys.exit(main())
