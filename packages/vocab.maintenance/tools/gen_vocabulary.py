#!/usr/bin/env python3
"""Generate the maintenance vocabulary from its sole data file."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary.json"
OUT = ROOT / "package.law"


def render() -> str:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    if data.get("schemaVersion") != "vocab.maintenance/0.1":
        raise SystemExit("gen_vocabulary: unknown vocabulary schema")
    lines = [
        "// GENERATED from vocabulary.json; do not edit by hand.",
        'language "law.core" version "0.2";',
        'package vocab.maintenance version "0.1.0";',
        'namespace "urn:law:vocab:maintenance";',
        "",
    ]
    lines += [f'pub entity {name} {{ label ru official "{label}"; }}' for name, label in data["entities"]]
    lines += [""] + [f'pub enum {name} {{ label ru official "{name}"; {"; ".join(items)}; }}' for name, items in data["enums"]]
    lines += [""] + [f'pub relation {relation} kind empirical {{ label ru official "{relation.split("(", 1)[0]}"; }}' for relation in data["relations"]]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render()
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != expected:
            print("gen_vocabulary: package.law differs from vocabulary.json")
            return 1
        print("gen_vocabulary: OK")
        return 0
    OUT.write_text(expected, encoding="utf-8")
    print(f"gen_vocabulary: wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
