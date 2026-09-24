#!/usr/bin/env python3
"""Восемь дел над Правилами определения размера вреда: девятнадцать вопросов,
основания в доказательстве с якорем на пункт, Rust/Python побайтно и replay.

Запуск из checkout, Python >= 3.12; --out сохраняет повторяемые расчёты.
Ожидания взяты из текста пунктов 9 и 10 Правил и сноски приложения 3, не из
ответов движка: 80 % — строгое «превышают»; молчание о передаче остатков не
есть её отрицание (§113); условие о детали — конъюнкция двух фактов.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
from types import SimpleNamespace

PACKAGE = Path(__file__).resolve().parent
# Оракул lawref есть только в checkout монорепозитория. В вынесенном каноне
# (packages/<канон>/examples/<подборка>) его нет: тогда проверяются ответы,
# основания и replay закреплённого law-cli, а сверка Rust/Python пропускается.
ROOT = next((parent for parent in PACKAGE.parents if (parent / "engines" / "lawref").is_dir()), None)
if ROOT is not None:
    sys.path.insert(0, str(ROOT / "engines" / "lawref"))
    from lawref.canon import canonical_bytes  # noqa: E402
    from lawref.cases import check_registration  # noqa: E402
    from lawref.evaluator import EvaluationRequest, evaluate  # noqa: E402
else:
    evaluate = None

    def canonical_bytes(document: dict) -> bytes:
        """Только сравнение ask/replay/сохранённого результата, не канон §208."""
        return json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()

    def check_registration(package: Path) -> list[SimpleNamespace]:
        manifest = tomllib.loads((package / "law.toml").read_text(encoding="utf-8"))
        return [SimpleNamespace(name=entry["name"]) for entry in manifest.get("cases", [])]

NS = "urn:kz:corpus:clir:vred-ts#"
PKG = "kz.corpus.vred_ts::"
VYPLATA = f"evaluate collect amount: Money where {PKG}strakhovaya_vyplata_pri_gibeli(r: raschet, amount: amount);"
STOIMOST = f"evaluate collect amount: Money where {PKG}stoimost_zamenyaemoy_detali(d: detal, amount: amount);"


def money(value: str) -> list[dict]:
    return [{"currency": "KZT", "kind": "value", "type": {"name": "urn:law:std#Money"}, "value": value}]


# (дело, вопрос) → ожидание: статус, значение либо truth, решающее правило (или None)
# и `absent` — правило, которое в этом деле применяться НЕ должно.
# Вопрос — имя файла в queries/ либо пара (queryId, строка evaluate §267.2).
EXPECTED: list[tuple[str, str | tuple[str, str], dict]] = [
    ("Gibel", "unichtozheno", {"truth": "TRUE_ONLY", "rule": "EkonomicheskayaNetselesoobraznost"}),
    ("Gibel", ("vyplata", VYPLATA), {"value": money("850000"), "rule": "VyplataZaMinusomGodnykhOstatkov"}),
    ("PeredachaOstatkov", "unichtozheno", {"truth": "TRUE_ONLY", "rule": "EkonomicheskayaNetselesoobraznost"}),
    ("PeredachaOstatkov", ("vyplata", VYPLATA), {"value": money("1000000"), "rule": "VyplataPriPeredacheOstatkov"}),
    ("Porog", "unichtozheno", {"truth": "NEITHER", "rule": None, "absent": "EkonomicheskayaNetselesoobraznost"}),
    ("Porog", "pochemu-ne-unichtozheno", {"truth": "NEITHER", "blockers": 2, "rule": None, "absent": "EkonomicheskayaNetselesoobraznost"}),
    ("Porog", ("vyplata", VYPLATA), {"value": [], "rule": None}),
    ("Molchanie", "unichtozheno", {"truth": "TRUE_ONLY", "rule": "UnichtozhenoPoTekhnicheskoyNevozmozhnosti"}),
    ("Molchanie", ("vyplata", VYPLATA), {"value": [], "rule": None, "absent": "VyplataZaMinusomGodnykhOstatkov"}),
    # E-0164: оба правила пункта 9 — блокеры; у «за минусом остатков» голова
    # вычисляемая, и блокер несёт headArguments (равенство суммы не проверено).
    ("Molchanie", "pochemu-ne-vyplata", {"truth": "NEITHER", "blockers": 2, "rule": None,
                                        "headArguments": "VyplataZaMinusomGodnykhOstatkov",
                                        "absent": "VyplataZaMinusomGodnykhOstatkov"}),
    # Молчание снято одним фактом — установленным отрицанием передачи остатков.
    ("MolchanieSnyato", "unichtozheno", {"truth": "TRUE_ONLY", "rule": "UnichtozhenoPoTekhnicheskoyNevozmozhnosti"}),
    ("MolchanieSnyato", ("vyplata", VYPLATA), {"value": money("850000"), "rule": "VyplataZaMinusomGodnykhOstatkov",
                                             "absent": "VyplataPriPeredacheOstatkov"}),
    ("DetalFizlitso", "detal-bez-iznosa", {"truth": "TRUE_ONLY", "rule": "NovayaDetalUFizicheskogoLitsa"}),
    ("DetalFizlitso", ("stoimost-detali", STOIMOST), {"value": money("200000"), "rule": "StoimostDetaliBezIznosa"}),
    ("DetalFizlitso", "positions", {"position": ("PeredatZamenyaemuyuDetal", "ACTIVE"), "rule": None}),
    ("DetalYurlitso", "detal-bez-iznosa", {"truth": "TRUE_ONLY", "rule": "NovayaDetalUYuridicheskogoLitsa", "absent": "NovayaDetalUFizicheskogoLitsa"}),
    ("DetalYurlitso", ("stoimost-detali", STOIMOST), {"value": money("200000"), "rule": "StoimostDetaliBezIznosa"}),
    ("DetalRemont", "detal-bez-iznosa", {"truth": "NEITHER", "rule": None, "absent": "NovayaDetalUFizicheskogoLitsa"}),
    # Блокеров два: оба правила пункта 10 (физическое и юридическое лицо) не сработали.
    ("DetalRemont", "pochemu-ne-bez-iznosa", {"truth": "NEITHER", "blockers": 2, "rule": None, "absent": "NovayaDetalUFizicheskogoLitsa"}),
    ("DetalRemont", ("stoimost-detali", STOIMOST), {"value": money("120000"), "rule": "StoimostDetaliSUchetomIznosa"}),
]


def run_json(command: list[str]) -> dict:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode:
        raise RuntimeError(f"{' '.join(command)}\n{completed.stderr}\n{completed.stdout}")
    return json.loads(completed.stdout)


def ask(law: str, case: str, query: str | tuple[str, str], saved: Path) -> dict:
    command = [law, "ask", str(PACKAGE), "--case", case, "--out", str(saved)]
    if isinstance(query, tuple):
        command += ["--query", query[1], "--query-id", query[0]]
    else:
        command += ["--query-json", str(PACKAGE / "queries" / f"{query}.json")]
    return run_json(command)


def check(law: str, output: Path) -> None:
    entries = check_registration(PACKAGE)
    if {entry.name for entry in entries} != {case for case, _, _ in EXPECTED}:
        raise RuntimeError("Состав зарегистрированных дел расходится с проверкой")
    if check_registration(PACKAGE.parents[1]):
        raise RuntimeError("Дела примера ошибочно отнесены к родительскому канону")
    for case, query, want in EXPECTED:
        qid = query[0] if isinstance(query, tuple) else query
        saved = output / case / qid
        result = ask(law, case, query, saved)
        answer, = result["results"]
        if answer["evaluationStatus"] != "COMPUTED":
            raise RuntimeError(f"{case}/{qid}: ожидался COMPUTED, получено {answer['evaluationStatus']}")
        if "truth" in want and answer.get("truthStatus") != want["truth"]:
            raise RuntimeError(f"{case}/{qid}: ожидалось {want['truth']}, получено {answer.get('truthStatus')}")
        if "value" in want and answer.get("value") != want["value"]:
            raise RuntimeError(f"{case}/{qid}: ожидалось {want['value']}, получено {answer.get('value')}")
        if "blockers" in want:
            blockers = answer["value"]["value"]["blockers"]
            if len(blockers) != want["blockers"] or any(b["trigger"] != "UNDETERMINED" for b in blockers):
                raise RuntimeError(f"{case}/{qid}: ожидалось {want['blockers']} блокеров UNDETERMINED, получено {blockers}")
            if "headArguments" in want:
                marked = next((b for b in blockers if b["rule"] == NS + want["headArguments"]), None)
                if not marked or [h["status"] for h in marked.get("headArguments", [])] != ["UNEVALUATED"]:
                    raise RuntimeError(f"{case}/{qid}: у блокера {want['headArguments']} нет пометки "
                                       f"headArguments UNEVALUATED (E-0164)")
        if "position" in want:
            norm, status = want["position"]
            if answer.get("normativeStatus") != status or NS + norm not in json.dumps(result):
                raise RuntimeError(f"{case}/{qid}: ожидалась позиция {norm} {status}, "
                                   f"получено {answer.get('normativeStatus')}")
        request = json.loads((saved / "request.json").read_bytes())
        applied = {node["id"].split(":apply:")[1].split(":")[0]
                   for node in result["proofGraph"]["nodes"] if ":apply:" in node["id"]}
        if want["rule"] is not None:
            if want["rule"] not in applied:
                raise RuntimeError(f"{case}/{qid}: правило {want['rule']} не применено; применены {sorted(applied)}")
            rule = next(node for node in request["ir"]["nodes"] if node["id"] == NS + want["rule"])
            nodes_by_id = {node["id"]: node for node in request["ir"]["nodes"]}
            if not rule.get("anchors") or not all(anchor in nodes_by_id for anchor in rule["anchors"]):
                raise RuntimeError(f"{case}/{qid}: у правила {want['rule']} нет якоря на пункт Правил")
        if want.get("absent") in applied:
            raise RuntimeError(f"{case}/{qid}: правило {want['absent']} не должно применяться; применены {sorted(applied)}")
        replay = run_json([law, "eval", str(saved)])
        expected_bytes = canonical_bytes(result)
        if evaluate is not None and canonical_bytes(evaluate(EvaluationRequest.from_dict(request))) != expected_bytes:
            raise RuntimeError(f"{case}/{qid}: Rust != Python")
        if canonical_bytes(replay) != expected_bytes:
            raise RuntimeError(f"{case}/{qid}: ask != replay")
        if canonical_bytes(json.loads((saved / "result.json").read_bytes())) != expected_bytes:
            raise RuntimeError(f"{case}/{qid}: stdout != сохранённый результат")
        compared = "Rust/Python и replay" if evaluate is not None else "replay (без lawref: Rust/Python не сверялся)"
        print(f"{case}/{qid}: {want.get('truth') or want.get('value') or want.get('position')}; "
              f"основание, {compared} — OK", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--law", default=str(ROOT / "law") if ROOT is not None else None,
                        required=ROOT is None, help="бинарь law/law-cli или launcher checkout")
    parser.add_argument("--out", type=Path, help="сохранить request/result/ask; по умолчанию временный каталог")
    args = parser.parse_args()
    try:
        if args.out:
            check(args.law, args.out.resolve())
        else:
            with tempfile.TemporaryDirectory(prefix="vred-ts-examples-") as temporary:
                check(args.law, Path(temporary))
    except (RuntimeError, ValueError, OSError, KeyError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("vred-ts examples: 8 дел, 19 вопросов — OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
