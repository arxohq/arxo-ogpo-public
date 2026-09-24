#!/usr/bin/env python3
"""Пять дел о сроке страховой выплаты ОГПО ВТС и неустойке статьи 353 ГК:
шестнадцать вопросов и один отказ, основания в доказательстве, Rust/Python
побайтно и replay.

Запуск из checkout, Python >= 3.12; --out сохраняет повторяемые расчёты.
Ожидания посчитаны по тексту статей 25, 26 Закона № 446-II и статьи 353 ГК,
снимку официального календаря 2026 года и закреплённым решениям
Национального Банка о базовой ставке — не по ответам движка: пятнадцать
рабочих дней от 22 июля истекают 12 августа, от 19 октября (через День
Республики и перенесённый выходной) — 10 ноября; двенадцать дней просрочки по
16,75 % годовых при делителе 365 дают 730 000 × 12 × 67/146000 = 4 020 ₸.
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

OGPO = "urn:kz:corpus:clir:ogpo-vts#"
MOST = "urn:kz:corpus:clir:strakhovaya-neustoyka#"
PKG = "kz.corpus.ogpovts::"
D = 'entity_ref("urn:example:ogpo:trebovanie")'
SROK = f"evaluate collect day: Date where {PKG}payment_due_day(demand: {D}, day: day);"
NEUSTOYKA = f"evaluate collect amount: Money where {PKG}late_payment_penalty_amount(demand: {D}, amount: amount);"


def money(value: str) -> list[dict]:
    return [{"currency": "KZT", "kind": "value", "type": {"name": "urn:law:std#Money"}, "value": value}]


def date(value: str) -> list[dict]:
    return [{"kind": "value", "type": {"name": "urn:law:std#Date"}, "value": value}]


def srok_truth(day: str) -> str:
    return f"evaluate truth({PKG}payment_due_day({D}, @{day}));"


# (дело, вопрос) → ожидание: статус исполнения (по умолчанию COMPUTED), truth
# либо value, решающее правило (полный URN или None) и `absent` — правило,
# которое в этом деле применяться НЕ должно. Вопрос — имя файла в queries/
# либо пара (queryId, строка evaluate §267.2).
EXPECTED: list[tuple[str, str | tuple[str, str], dict]] = [
    # Выплата в день истечения срока: срок выведен из дня получения документов
    # и календаря, просрочки нет, неустойка не выводится вовсе.
    ("VDenSroka", ("srok-12-avgusta", srok_truth("2026-08-12")), {"truth": "TRUE_ONLY", "rule": OGPO + "GeneralPaymentDueDay"}),
    ("VDenSroka", "prosrochka", {"truth": "NEITHER", "rule": None, "absent": OGPO + "PaymentMadeLate"}),
    ("VDenSroka", ("neustoyka", NEUSTOYKA), {"value": [], "rule": None, "absent": MOST + "RazmerNeustoyki"}),
    # Выплата после срока: просрочка выведена сравнением двух дней, неустойка
    # посчитана мостом по ставке на день исполнения, обязанность уплатить её ACTIVE.
    ("Prosrochka", ("srok", SROK), {"value": date("2026-08-12"), "rule": OGPO + "GeneralPaymentDueDay"}),
    ("Prosrochka", "prosrochka", {"truth": "TRUE_ONLY", "rule": OGPO + "PaymentMadeLate"}),
    ("Prosrochka", ("neustoyka", NEUSTOYKA), {"value": money("4020"), "rule": MOST + "RazmerNeustoyki"}),
    ("Prosrochka", "neustoyka-4020", {"truth": "TRUE_ONLY", "rule": MOST + "DnevnayaStavka"}),
    ("Prosrochka", "positions", {"position": (OGPO + "InsurerMustPayPenaltyForLatePayment", "ACTIVE"), "rule": None}),
    # Срок через праздник и перенесённый день отдыха: 10 ноября, а не 9-е.
    ("CherezPrazdnik", ("srok-10-noyabrya", srok_truth("2026-11-10")), {"truth": "TRUE_ONLY", "rule": OGPO + "GeneralPaymentDueDay"}),
    ("CherezPrazdnik", ("srok-9-noyabrya", srok_truth("2026-11-09")), {"truth": "NEITHER", "rule": None}),
    ("CherezPrazdnik", "prosrochka", {"truth": "NEITHER", "rule": None, "absent": OGPO + "PaymentMadeLate"}),
    # Без делителя года: просрочка есть, размер не выводится, why_not называет
    # правило размера как неустановленное, а не подставляет число.
    ("BezDelitelya", "prosrochka", {"truth": "TRUE_ONLY", "rule": OGPO + "PaymentMadeLate"}),
    ("BezDelitelya", ("neustoyka", NEUSTOYKA), {"value": [], "rule": None, "absent": MOST + "DnevnayaStavka"}),
    ("BezDelitelya", "pochemu-net-neustoyki", {"truth": "NEITHER", "blocker": MOST + "RazmerNeustoyki", "rule": None}),
    # Два дня выплаты по одному требованию: конфликт ключа §45.1/§196 делает
    # документ NON_EXECUTABLE — статус, а не «более правдоподобная» дата.
    ("Protivorechie", "prosrochka", {"status": "NON_EXECUTABLE", "issue": "KEY_CONFLICT", "rule": None}),
    ("Protivorechie", ("neustoyka", NEUSTOYKA), {"status": "NON_EXECUTABLE", "issue": "KEY_CONFLICT", "rule": None}),
]

# Вопрос вне покрытия: уменьшение неустойки судом (статья 297 ГК) в мире дела
# не формализовано — предиката нет, и вопрос отвергается статически, а не
# отвечается молчанием.
REFUSED: tuple[str, str, str, str] = (
    "Prosrochka", "vne-pokrytiya",
    f"evaluate truth({PKG}neustoyka_umenshena_sudom({D}));",
    "LDC-E1105",
)


def run(command: list[str]) -> tuple[int, str, str]:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return completed.returncode, completed.stdout, completed.stderr


def run_json(command: list[str]) -> dict:
    code, out, err = run(command)
    if code:
        raise RuntimeError(f"{' '.join(command)}\n{err}\n{out}")
    return json.loads(out)


def ask_command(law: str, case: str, query: str | tuple[str, str], saved: Path | None) -> list[str]:
    command = [law, "ask", str(PACKAGE), "--case", case]
    if saved is not None:
        command += ["--out", str(saved)]
    if isinstance(query, tuple):
        command += ["--query", query[1], "--query-id", query[0]]
    else:
        command += ["--query-json", str(PACKAGE / "queries" / f"{query}.json")]
    return command


def applied_rules(result: dict) -> set[str]:
    """Короткие имена применённых правил: узел применения назван
    `…:apply:<Имя правила>:<хэш подстановки>`, без пространства имён."""
    return {node["id"].split(":apply:")[1].split(":")[0]
            for node in result["proofGraph"]["nodes"] if ":apply:" in node["id"]}


def short(rule: str) -> str:
    return rule.split("#", 1)[1]


def check(law: str, output: Path) -> None:
    entries = check_registration(PACKAGE)
    if {entry.name for entry in entries} != {case for case, _, _ in EXPECTED}:
        raise RuntimeError("Состав зарегистрированных дел расходится с проверкой")
    if check_registration(PACKAGE.parents[1]):
        raise RuntimeError("Дела примера ошибочно отнесены к родительскому канону")
    for case, query, want in EXPECTED:
        qid = query[0] if isinstance(query, tuple) else query
        saved = output / case / qid
        result = run_json(ask_command(law, case, query, saved))
        # Рядом с ответом на вопрос документ несёт результаты ограничений
        # `calc.accruals` (BaseIsNotNegative, SingleEndPerAccrual, …): ответ — тот,
        # чей id назван делом и вопросом.
        answer = next(r for r in result["results"] if f"#case/{case}/query/{qid}" in r["id"])
        status = want.get("status", "COMPUTED")
        if answer["evaluationStatus"] != status:
            raise RuntimeError(f"{case}/{qid}: ожидался {status}, получено {answer['evaluationStatus']}")
        if "issue" in want and want["issue"] not in {issue.get("code") for issue in result.get("issues", [])}:
            raise RuntimeError(f"{case}/{qid}: нет issue {want['issue']}; есть {result.get('issues')}")
        if "truth" in want and answer.get("truthStatus") != want["truth"]:
            raise RuntimeError(f"{case}/{qid}: ожидалось {want['truth']}, получено {answer.get('truthStatus')}")
        if "value" in want and answer.get("value") != want["value"]:
            raise RuntimeError(f"{case}/{qid}: ожидалось {want['value']}, получено {answer.get('value')}")
        if "blocker" in want:
            blockers = answer["value"]["value"]["blockers"]
            hit = [b for b in blockers if b["rule"] == want["blocker"] and b["trigger"] == "UNDETERMINED"]
            if not hit:
                raise RuntimeError(f"{case}/{qid}: нет блокера {want['blocker']} UNDETERMINED; получено {blockers}")
        if "position" in want:
            norm, norm_status = want["position"]
            supports = answer.get("normativeStatusSupports", [])
            if not any(s.get("status") == norm_status and any(norm in p for p in s.get("proof", [])) for s in supports):
                raise RuntimeError(f"{case}/{qid}: нет позиции {norm} {norm_status}; получено {supports}")
        request = json.loads((saved / "request.json").read_bytes())
        applied = applied_rules(result)
        if want["rule"] is not None:
            if short(want["rule"]) not in applied:
                raise RuntimeError(f"{case}/{qid}: правило {want['rule']} не применено; применены {sorted(applied)}")
            nodes_by_id = {node["id"]: node for node in request["ir"]["nodes"]}
            rule = nodes_by_id[want["rule"]]
            if not rule.get("anchors") or not all(anchor in nodes_by_id for anchor in rule["anchors"]):
                raise RuntimeError(f"{case}/{qid}: у правила {want['rule']} нет якоря на текст источника")
        if want.get("absent") and short(want["absent"]) in applied:
            raise RuntimeError(f"{case}/{qid}: правило {want['absent']} не должно применяться; применены {sorted(applied)}")
        replay = run_json([law, "eval", str(saved)])
        expected_bytes = canonical_bytes(result)
        if evaluate is not None and canonical_bytes(evaluate(EvaluationRequest.from_dict(request))) != expected_bytes:
            raise RuntimeError(f"{case}/{qid}: Rust != Python")
        if canonical_bytes(replay) != expected_bytes:
            raise RuntimeError(f"{case}/{qid}: ask != replay")
        if canonical_bytes(json.loads((saved / "result.json").read_bytes())) != expected_bytes:
            raise RuntimeError(f"{case}/{qid}: stdout != сохранённый результат")
        shown = want.get("truth") or want.get("status") or want.get("position") or want.get("value")
        compared = "Rust/Python и replay" if evaluate is not None else "replay (без lawref: Rust/Python не сверялся)"
        print(f"{case}/{qid}: {shown}; основание, {compared} — OK", flush=True)
    case, qid, query, code = REFUSED
    rc, out, err = run(ask_command(law, case, (qid, query), None))
    if rc == 0 or code not in (out + err):
        raise RuntimeError(f"{case}/{qid}: ожидался отказ {code}; rc={rc}\n{out}\n{err}")
    print(f"{case}/{qid}: отказ {code} — OK", flush=True)


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
            with tempfile.TemporaryDirectory(prefix="ogpo-vts-examples-") as temporary:
                check(args.law, Path(temporary))
    except (RuntimeError, ValueError, OSError, KeyError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"ogpo-vts examples: 5 дел, {len(EXPECTED)} вопросов и 1 отказ — OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
