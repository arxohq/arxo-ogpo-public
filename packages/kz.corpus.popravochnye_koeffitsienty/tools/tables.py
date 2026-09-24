#!/usr/bin/env python3
"""Размеры поправочных коэффициентов — независимое чтение закреплённых байтов.

ЗАЧЕМ. Модуль `02-razmery.law` переписывает две таблицы АРРФР нормативными
фактами: двадцать территорий на каждый из двух годов, сорок чисел. Набранные
глазами, они компилируются, проходят differential и живут до первого дела.
Поэтому таблицы читаются ОТДЕЛЬНО и НЕЗАВИСИМО — прямо из закреплённой
публикации §194, — и `--check` сверяет с этим чтением то, что стоит в `.law`.

Разбор ниже не читает ни одного правила и знает из модели ровно одно:
соответствие наименования территории из акта АРРФР члену перечисления
`RegistrationTerritory` закона. Само это соответствие — юридическое решение
(двадцать строк пункта 3 статьи 19 и двадцать строк таблицы АРРФР суть один
перечень территорий), и потому записано здесь явно, а не выведено похожестью
строк.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
SOURCES = PACKAGE / "sources" / "popravochnye-koeffitsienty"
MODULE = PACKAGE / "02-razmery.law"
YEARS = {"2025": 2025, "2026": 2026}

#: Наименование территории в акте АРРФР → член перечисления
#: `kz.corpus.ogpovts::RegistrationTerritory`. Двадцать строк, столько же,
#: сколько у таблицы пункта 3 статьи 19 закона.
#: Наименование территории в акте АРРФР → константа общего словаря регионов
#: `vocab.geo` (DECISION-0139). Через НЕЁ величина связывается с
#: перечислением `RegistrationTerritory` закона: `pub enum` членов не
#: экспортирует (§24), и назвать их из подзаконного пакета нельзя. Мост
#: «член перечисления ↔ регион словаря» объявлен у владельца перечисления —
#: `kz/ogpo-vts/package.law`, отношение `territoriya_registratsii_regiona`.
TERRITORIES = {
    "Алматинская область": "ALMATY",
    "Жетысуская область": "ZHETISU",
    "Туркестанская область": "TURKISTAN",
    "Восточно-Казахстанская область": "EAST_KAZAKHSTAN",
    "Абайская область": "ABAI",
    "Костанайская область": "KOSTANAY",
    "Карагандинская область": "KARAGANDA",
    "Улытауская область": "ULYTAU",
    "Северо-Казахстанская область": "NORTH_KAZAKHSTAN",
    "Акмолинская область": "AKMOLA",
    "Павлодарская область": "PAVLODAR",
    "Жамбылская область": "ZHAMBYL",
    "Актюбинская область": "AKTOBE",
    "Западно-Казахстанская область": "WEST_KAZAKHSTAN",
    "Кызылординская область": "KYZYLORDA",
    "Атырауская область": "ATYRAU",
    "Мангистауская область": "MANGYSTAU",
    "Алматы": "ALMATY_CITY",
    "Астана": "ASTANA",
    "Шымкент": "SHYMKENT",
}


def parse(key: str) -> dict[str, str]:
    """`{член перечисления: коэффициент}` из закреплённых байтов года."""
    lines = [line.strip() for line in
             (SOURCES / f"{key}.ru.txt").read_text(encoding="utf-8").splitlines()
             if line.strip()]
    out: dict[str, str] = {}
    for i, line in enumerate(lines):
        if not re.fullmatch(r"\d{1,2}\.", line):
            continue
        name, value = lines[i + 1], lines[i + 2]
        if name not in TERRITORIES:
            raise SystemExit(f"{key}: неизвестное наименование территории {name!r}")
        if not re.fullmatch(r"\d,\d\d", value):
            raise SystemExit(f"{key}: строка {name!r} не несёт коэффициента: {value!r}")
        member = TERRITORIES[name]
        if member in out:
            raise SystemExit(f"{key}: территория {name!r} встретилась дважды")
        out[member] = value.replace(",", ".")
    if len(out) != len(TERRITORIES):
        missing = sorted(set(TERRITORIES.values()) - set(out))
        raise SystemExit(f"{key}: прочитано {len(out)} территорий из "
                         f"{len(TERRITORIES)}; нет {missing}")
    return out


def module_facts() -> dict[tuple[str, int], str]:
    text = MODULE.read_text(encoding="utf-8")
    return {(m.group(1), int(m.group(2))): m.group(3) for m in re.finditer(
        r"assert \"razmer-\d{4}-\w+\": razmer_popravochnogo_koeffitsienta\("
        r"vocab\.geo::(\w+), (\d{4}), ([\d.]+)\);", text)}


def emit() -> str:
    out = []
    for key, year in YEARS.items():
        out.append(f"    // Размеры на {year} год.")
        for member, value in parse(key).items():
            out.append(f'    assert "razmer-{year}-{member}": '
                       f"razmer_popravochnogo_koeffitsienta("
                       f"vocab.geo::{member}, {year}, {value});")
        out.append("")
    return "\n".join(out).rstrip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--emit", action="store_true")
    args = parser.parse_args()
    if args.emit:
        print(emit())
        return 0
    want = {(member, year): value
            for key, year in YEARS.items()
            for member, value in parse(key).items()}
    got = module_facts()
    problems = [f"{m}/{y}: в модуле {got.get((m, y))!r}, в источнике {v!r}"
                for (m, y), v in want.items() if got.get((m, y)) != v]
    problems += [f"{m}/{y}: в модуле есть, в источнике нет"
                 for (m, y) in sorted(set(got) - set(want))]
    if problems:
        for line in problems:
            print(f" РАЗОШЛОСЬ  {line}", file=sys.stderr)
        return 1
    print(f"        ==  поправочные коэффициенты: {len(want)} величин "
          f"({len(YEARS)} года × {len(TERRITORIES)} территорий) — совпало "
          f"с закреплёнными байтами")
    return 0


if __name__ == "__main__":
    sys.exit(main())
