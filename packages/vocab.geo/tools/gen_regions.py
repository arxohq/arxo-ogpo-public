#!/usr/bin/env python3
"""Порождает `01-kz-regions.law` из `regions.json` (инвариант 2 CLAUDE.md).

Данные словаря живут одним файлом: код ISO 3166-2:KZ, подписи ru/kk/en и
опорная точка WGS84 на регион. Модуль `.law` — их проекция, руками он не
правится; ворота категории (`check_vocab.py`) зовут `--check`.

    python3 packs/vocab/geo/tools/gen_regions.py          # записать
    python3 packs/vocab/geo/tools/gen_regions.py --check  # сверить
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "regions.json"
OUT = PACKAGE / "01-kz-regions.law"
COORD = re.compile(r"^-?\d{1,3}\.\d{2}$")


def render() -> str:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    if data.get("schemaVersion") != "vocab.geo.regions/0.1":
        raise SystemExit("gen_regions: неизвестная схема regions.json")
    out = [
        "// ПОРОЖДЕНО tools/gen_regions.py из regions.json — руками не правится\n"
        "// (инвариант 2 CLAUDE.md). Коды — ISO 3166-2:KZ; опорные точки —\n"
        "// картографические (WGS84, градусы, lat/lon), не правовой факт.\n"
        "\n"
        'language "law.core" version "0.2";\n'
        'package vocab.geo version "0.1.0";\n'
        'namespace "urn:law:vocab:geo";\n'
    ]
    seen_codes: set[str] = set()
    regions = data["regions"]
    for region in regions:
        name, code = region["name"], region["code"]
        if not re.fullmatch(r"[A-Z][A-Z_]*", name) or code in seen_codes:
            raise SystemExit(f"gen_regions: недопустимое имя или повтор кода: {name} {code}")
        seen_codes.add(code)
        for key in ("lat", "lon"):
            if not COORD.match(region[key]):
                raise SystemExit(f"gen_regions: {name}: координата {key}={region[key]!r} не Decimal с двумя знаками")
        if not -90.0 <= float(region["lat"]) <= 90.0 or not -180.0 <= float(region["lon"]) <= 180.0:
            raise SystemExit(f"gen_regions: {name}: координата вне диапазона WGS84")
        slug = name.lower().replace("_", "-")
        out.append(
            f"\npub const {name}: Region = entity_ref(\"urn:law:vocab:geo:kz:region:{slug}\") {{\n"
            f'    label ru official "{region["ru"]}";\n'
            f'    label kk official "{region["kk"]}";\n'
            f'    label en official "{region["en"]}";\n'
            "};\n")
    out.append("\n// --- Атрибуты регионов: код и опорная точка ---------------------------------\n")
    for region in regions:
        out.append(f"\nassert region_code({region['name']}, \"{region['code']}\");\n"
                   f"assert region_anchor({region['name']}, {region['lat']}, {region['lon']});\n")
    return "".join(out)


def main(argv: list[str]) -> int:
    text = render()
    if "--check" in argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else None
        if current != text:
            print(f"gen_regions: {OUT.name} расходится с regions.json — перезапустите генератор",
                  file=sys.stderr)
            return 1
        print("gen_regions: выход совпадает")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"gen_regions: записан {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
