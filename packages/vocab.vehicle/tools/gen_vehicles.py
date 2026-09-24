#!/usr/bin/env python3
"""Порождает `01-kinds-and-categories.law` из `vehicles.json` (инвариант 2 CLAUDE.md).

Данные словаря живут одним файлом: категории с буквенным кодом и родительской
категорией, виды транспортных средств с категорией классификации, подписи
ru/kk/en. Модуль `.law` — их проекция, руками он не правится; ворота
категории (`check_vocab.py`) зовут `--check`.

    python3 packs/vocab/vehicle/tools/gen_vehicles.py          # записать
    python3 packs/vocab/vehicle/tools/gen_vehicles.py --check  # сверить
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "vehicles.json"
OUT = PACKAGE / "01-kinds-and-categories.law"
SERVICE_OUT = PACKAGE / "02-ownership-and-service.law"
NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
CODE = re.compile(r"^[A-Z][0-9]?$")


def _const(name: str, typ: str, genus: str, row: dict) -> str:
    slug = name.lower().replace("_", "-")
    return (
        f"\npub const {name}: {typ} = entity_ref(\"urn:law:vocab:vehicle:{genus}:{slug}\") {{\n"
        f'    label ru official "{row["ru"]}";\n'
        f'    label kk official "{row["kk"]}";\n'
        f'    label en official "{row["en"]}";\n'
        "};\n")


def render() -> str:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    if data.get("schemaVersion") != "vocab.vehicle.vehicles/0.1":
        raise SystemExit("gen_vehicles: неизвестная схема vehicles.json")
    out = [
        "// ПОРОЖДЕНО tools/gen_vehicles.py из vehicles.json — руками не правится\n"
        "// (инвариант 2 CLAUDE.md). Названия видов и категорий подтверждены\n"
        "// закреплёнными байтами корпуса (ст. 19 п. 6 Закона РК об ОГПО ВТС,\n"
        "// ПДД РК); коды нормализованы к латинице. Не правовой факт: нормы о\n"
        "// массе, местах, возрасте и коэффициентах остаются у предметных актов.\n"
        "\n"
        'language "law.core" version "0.2";\n'
        'package vocab.vehicle version "0.1.0";\n'
        'namespace "urn:law:vocab:vehicle";\n'
    ]
    categories = data["categories"]
    kinds = data["kinds"]
    names: set[str] = set()
    codes: set[str] = set()
    for cat in categories:
        name, code = cat["name"], cat["code"]
        if not NAME.match(name) or name in names:
            raise SystemExit(f"gen_vehicles: недопустимое имя или повтор: {name}")
        if not CODE.match(code) or code in codes:
            raise SystemExit(f"gen_vehicles: недопустимый код или повтор: {code}")
        names.add(name)
        codes.add(code)
    cat_names = {c["name"] for c in categories}
    for cat in categories:
        parent = cat["parent"]
        if parent is not None and (parent not in cat_names or parent == cat["name"]):
            raise SystemExit(f"gen_vehicles: {cat['name']}: родитель {parent!r} не категория")
    for kind in kinds:
        name = kind["name"]
        if not NAME.match(name) or name in names:
            raise SystemExit(f"gen_vehicles: недопустимое имя или повтор: {name}")
        names.add(name)
        if kind["category"] is not None and kind["category"] not in cat_names:
            raise SystemExit(f"gen_vehicles: {name}: категория {kind['category']!r} не объявлена")
    for row in categories + kinds:
        for key in ("ru", "kk", "en"):
            if not row.get(key) or '"' in row[key]:
                raise SystemExit(f"gen_vehicles: {row['name']}: подпись {key} пуста или содержит кавычку")

    out.append("\n// --- Категории транспортных средств -----------------------------------------\n")
    for cat in categories:
        out.append(_const(cat["name"], "Category", "category", cat))
    out.append("\n// --- Виды транспортных средств ----------------------------------------------\n")
    for kind in kinds:
        out.append(_const(kind["name"], "Kind", "kind", kind))
    out.append("\n// --- Атрибуты категорий: код и родительская категория -------------------------\n")
    for cat in categories:
        out.append(f"\nassert category_code({cat['name']}, \"{cat['code']}\");\n")
        if cat["parent"] is not None:
            out.append(f"assert category_parent({cat['name']}, {cat['parent']});\n")
    out.append("\n// --- Атрибуты видов: категория классификации (где источник её называет) -----\n")
    for kind in kinds:
        if kind["category"] is not None:
            out.append(f"\nassert kind_category({kind['name']}, {kind['category']});\n")
    return "".join(out)


def render_service() -> str:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    service = data.get("serviceVocabulary")
    if not isinstance(service, dict):
        raise SystemExit("gen_vehicles: serviceVocabulary is missing")
    lines = [
        "// GENERATED from vehicles.json; do not edit by hand.",
        'language "law.core" version "0.2";',
        'package vocab.vehicle version "0.1.0";',
        'namespace "urn:law:vocab:vehicle";',
        "",
    ]
    lines += [f'pub entity {name} {{ label ru official "{label}"; }}' for name, label in service["entities"]]
    lines += [""]
    lines += [f'pub enum {name} {{ label ru official "{name}"; {"; ".join(items)}; }}' for name, items in service["enums"]]
    lines += [""]
    for relation in service["relations"]:
        name = relation.split("(", 1)[0]
        lines.append(f'pub relation {relation} kind empirical {{ label ru official "{name}"; }}')
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    text = render()
    if "--check" in argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else None
        service_current = SERVICE_OUT.read_text(encoding="utf-8") if SERVICE_OUT.exists() else None
        if current != text or service_current != render_service():
            print(f"gen_vehicles: generated modules differ from vehicles.json — rerun generator",
                  file=sys.stderr)
            return 1
        print("gen_vehicles: выход совпадает")
        return 0
    OUT.write_text(text, encoding="utf-8")
    SERVICE_OUT.write_text(render_service(), encoding="utf-8")
    print(f"gen_vehicles: wrote {OUT.name} and {SERVICE_OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
