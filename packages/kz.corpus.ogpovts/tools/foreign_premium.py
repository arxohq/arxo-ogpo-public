#!/usr/bin/env python3
"""Чужие калькуляторы премии ОГПО ВТС против статьи 19 и её делегатов.

    python3 corpus/laws/kz/laws/ogpo-vts/tools/foreign_premium.py --snapshot  # их код → theirs в cases
    python3 corpus/laws/kz/laws/ogpo-vts/tools/foreign_premium.py --expect    # модель → ours в cases
    python3 corpus/laws/kz/laws/ogpo-vts/tools/foreign_premium.py --emit      # tests/ogpo-chuzhoy-*.lawtest
    python3 corpus/laws/kz/laws/ogpo-vts/tools/foreign_premium.py --check     # всё актуально
    python3 corpus/laws/kz/laws/ogpo-vts/tools/foreign_premium.py --report    # таблица для REPORT.md

Образец — `corpus/laws/kz/bridges/payroll/tools/compare.py`. Три стороны:

- ИХ ОТВЕТ снимается ПРОГОНОМ ИХ КОДА из закреплённых байтов
  (`tests/foreign/*/`), а не переписыванием чисел со страницы. calk.kz —
  модуль коэффициентов исполняется как есть, формула компонента React
  перенесена дословно (ниже цитата); calculators.kz — встроенный скрипт
  страницы исполняется целиком с подставным `document`.
- НАШ ОТВЕТ выводит независимая модель по закреплённым текстам: статья 19
  Закона № 446-II (`sources/ogpo-vts/ru.txt`), приложение и пункты 4, 9
  Правил № 140, размеры на 2026 год постановления АРРФР № 72. `--check`
  сверяет каждое число модели с закреплённым текстом.
- ФОРМАЛИЗАЦИЯ отвечает на порождённых `.lawtest` обоими оценщиками.

Ожидание сценария — число модели без округления: статья 19 округления не
называет. Их ответ округлён `Math.round`; сравнение идёт с нашим числом,
округлённым до тенге, и расхождение квалифицируется в REPORT.md поимённо, а не
подгоняется.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
ROOT = PACKAGE.parents[4]
CASES = HERE / "foreign-premium-cases.json"
TESTS = PACKAGE / "tests"
FOREIGN = TESTS / "foreign"
FAMILY = "kz.corpus.ogpovts#chuzhie-kalkulyatory"
PREFIX = "ogpo-chuzhoy-"

CALK_COEFFICIENTS = FOREIGN / "calk-kz" / "ogpoCoefficients-CWHGjXpF.js"
CALK_COMPONENT = FOREIGN / "calk-kz" / "InsuranceCalculator-DVKEHrs5.js"
CALCULATORS_PAGE = FOREIGN / "calculators-kz" / "insurance.html"

OGPO_TEXT = PACKAGE / "sources" / "ogpo-vts" / "ru.txt"
BM_SOURCES = ROOT / "corpus/laws/kz/regulators/bonus-malus/sources"
POPRAV_SOURCES = ROOT / "corpus/laws/kz/regulators/popravochnye-koeffitsienty/sources"

# ============================================================================
# Независимая модель: числа закреплённых текстов
# ============================================================================

#: МРП 2026 года — Закон о республиканском бюджете на 2026–2028 годы, ст. 8.
MRP_2026 = Fraction(4325)
#: Ст. 19 п. 2: базовая страховая премия — 1,9 МРП.
BASE_MRP = Fraction("1.9")
#: Ст. 19 п. 3: коэффициенты по территории регистрации.
TERRITORY = {
    "AlmatyOblast": "1.78", "TurkestanOblast": "1.01", "EastKazakhstanOblast": "1.96",
    "KostanayOblast": "1.95", "KaragandaOblast": "1.39", "NorthKazakhstanOblast": "1.33",
    "AkmolaOblast": "1.32", "PavlodarOblast": "1.63", "ZhambylOblast": "1.00",
    "AktobeOblast": "1.35", "WestKazakhstanOblast": "1.17", "KyzylordaOblast": "1.09",
    "AtyrauOblast": "2.69", "MangistauOblast": "1.15", "AbayOblast": "1.96",
    "UlytauOblast": "1.39", "ZhetisuOblast": "1.78", "Almaty": "2.96",
    "Astana": "2.2", "Shymkent": "1.01",
}
#: Постановление Правления АРРФР от 12.11.2025 № 72: поправочные на 2026 год.
ADJUSTMENT_2026 = {
    "AlmatyOblast": "1.44", "ZhetisuOblast": "1.20", "TurkestanOblast": "1.69",
    "EastKazakhstanOblast": "0.72", "AbayOblast": "0.80", "KostanayOblast": "1.11",
    "KaragandaOblast": "1.18", "UlytauOblast": "0.99", "NorthKazakhstanOblast": "0.67",
    "AkmolaOblast": "1.08", "PavlodarOblast": "0.82", "ZhambylOblast": "1.74",
    "AktobeOblast": "1.02", "WestKazakhstanOblast": "1.19", "KyzylordaOblast": "1.85",
    "AtyrauOblast": "0.48", "MangistauOblast": "0.79", "Almaty": "0.71",
    "Astana": "1.44", "Shymkent": "1.61",
}
#: Ст. 19 п. 4: иные города и населённые пункты области.
OTHER_SETTLEMENT = Fraction("0.8")
#: Ст. 19 п. 6: коэффициенты по типу транспортного средства.
VEHICLE = {
    "PassengerCar": "2,09", "BusUpToSixteenSeats": "3,26", "BusOverSixteenSeats": "3,45",
    "FreightVehicle": "3,98", "TrolleybusOrTram": "2,33", "MotorVehicle": "1,00",
    "Trailer": "1,00",
}
#: Ст. 19 п. 8: юридические лица.
LEGAL_ENTITY_DRIVER = Fraction("1.2")
#: Приложение к Правилам № 140: коэффициенты классов.
KLASS = {
    "KlassM2": "3.50", "KlassM1": "3.00", "KlassM": "2.45", "Klass0": "2.30",
    "Klass1": "1.55", "Klass2": "1.40", "Klass3": "1.00", "Klass4": "0.95",
    "Klass5": "0.90", "Klass6": "0.85", "Klass7": "0.80", "Klass8": "0.75",
    "Klass9": "0.70", "Klass10": "0.65", "Klass11": "0.60", "Klass12": "0.55",
    "Klass13": "0.50",
}
#: Правила № 140, пункт 4 (впервые) и пункт 9 (аренда, лизинг, автобусы, такси).
FIRST_CONTRACT_MULTIPLIER = Fraction("1.20")
TAXI_LEGAL_MULTIPLIER = Fraction("1.80")


def frac(text: str) -> Fraction:
    return Fraction(text.replace(",", "."))


def driver_coefficient(case: dict) -> Fraction | None:
    """Ст. 19 пп. 7–8. Стажа ровно двух лет пункт 7 не называет — None."""
    if case["insured"] == "LegalEntity":
        return LEGAL_ENTITY_DRIVER
    age, experience = case["age"], case["experience"]
    if experience == 2:
        return None
    young, novice = age < 25, experience < 2
    if young and novice:
        return Fraction("1.10")
    if young or novice:
        return Fraction("1.05")
    return Fraction("1.00")


def bonus_malus(case: dict) -> Fraction:
    bm = case["bonus_malus"]
    if bm["kind"] == "ordinary":
        return frac(KLASS[bm["klass"]])
    if bm["kind"] == "first":
        return frac(KLASS["Klass3"]) * FIRST_CONTRACT_MULTIPLIER
    if bm["kind"] == "taxi_legal":
        return frac(KLASS["Klass3"]) * TAXI_LEGAL_MULTIPLIER
    raise ValueError(bm)


def model(case: dict) -> Fraction | None:
    """Годовая премия ст. 19 п. 1. None — закон ответа не даёт."""
    if case["legal_year"] != 2026:
        return None
    driver = driver_coefficient(case)
    if driver is None:
        return None
    territory = frac(TERRITORY[case["territory"]]) * frac(ADJUSTMENT_2026[case["territory"]])
    if case["basis"] == "OtherSettlement":
        territory *= OTHER_SETTLEMENT
    operation = Fraction("1.00") if case["operation_term"] <= 7 else Fraction("1.10")
    return (MRP_2026 * BASE_MRP * territory * frac(VEHICLE[case["vehicle"]])
            * driver * operation * bonus_malus(case))


def decimal_text(value: Fraction) -> str:
    """Точная десятичная запись: множители конечные десятичные дроби."""
    d = Decimal(value.numerator) / Decimal(value.denominator)
    if Fraction(d) != value:
        raise ValueError(f"не конечная десятичная дробь: {value}")
    text = format(d, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def tenge(value: Fraction) -> int:
    d = Decimal(value.numerator) / Decimal(value.denominator)
    return int(d.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def check_model_numbers() -> list[str]:
    """Каждое число модели обязано стоять в закреплённом тексте."""
    problems = []
    text = OGPO_TEXT.read_text(encoding="utf-8")
    article = text[text.find("Статья 19."):text.find("Статья 20.")]
    for name, value in {**TERRITORY, **VEHICLE}.items():
        needle = value.replace(".", ",")
        if needle not in article:
            problems.append(f"ст. 19: {name} {needle} нет в тексте статьи")
    for needle in ("1,9 месячного", "0,8", "1,2."):
        if needle not in article:
            problems.append(f"ст. 19: «{needle}» нет в тексте статьи")
    for label, directory, numbers in (
            ("АРРФР № 72", POPRAV_SOURCES, ADJUSTMENT_2026.values()),
            ("Правила № 140", BM_SOURCES, KLASS.values())):
        corpus = "\n".join(p.read_text(encoding="utf-8", errors="replace")
                           for p in sorted(directory.rglob("*.txt")))
        for value in set(numbers):
            if value.replace(".", ",") not in corpus and value not in corpus:
                problems.append(f"{label}: {value} нет в закреплённых текстах")
    return problems


# ============================================================================
# Их код
# ============================================================================

#: Формула компонента `InsuranceCalculator` calk.kz, дословно из закреплённого
#: чанка (минифицированные имена сохранены в комментарии):
#:   p=K*V; S=L(r); I=!r.isCity&&j==="other"?Y:1; O=a.coefficient;
#:   b=max(1, fe(age,exp) по водителям); R=max(0,f-parseInt(u)); _=R>he?be:1;
#:   q=l.coefficient; ie=p*S*I*O*b*_*q; finalPremium=Math.round(ie)
#: где V=4325, f=2026, K=ge, L=o, Y=b, fe=c, he=d, be=e импорта модуля.
CALK_HARNESS = """
import {O as xe, o as L, a as pe, f as A, b as Y, c as fe, d as he, e as be, g as ge}
  from %(module)s;
const w = %(classes)s;
const out = [];
for (const c of %(cases)s) {
  const V = 4325, K = ge, f = 2026;
  const r = A(c.region), a = pe.find(m => m.id === c.vehicle), l = w.find(m => m.class === c.klass);
  if (!r || !a || !l) { out.push({error: "нет варианта ввода"}); continue; }
  const p = K * V, S = L(r), I = !r.isCity && c.settlement === "other" ? Y : 1, O = a.coefficient;
  let b = 1; c.drivers.forEach(([age, exp]) => { const D = fe(age, exp); if (D > b) b = D; });
  const re = parseInt(c.year) || f, R = Math.max(0, f - re), _ = R > he ? be : 1, q = l.coefficient;
  const ie = p * S * I * O * b * _ * q;
  out.push({premium: Math.round(ie), factors: {S, I, O, b, _, q}});
}
console.log(JSON.stringify(out));
"""

CALCULATORS_HARNESS = """
const script = %(script)s;
const out = [];
for (const c of %(cases)s) {
  const els = {};
  for (const [id, v] of Object.entries(c)) els[id] = {value: String(v), checked: v === true};
  for (const id of ["resInsuranceCost", "resBase", "resRegFactor"]) els[id] = {innerText: ""};
  const document = {getElementById: id => els[id], addEventListener: () => {}};
  (new Function("document", script + "\\ncalculateOGPO();"))(document);
  out.push({premium: Number(els.resInsuranceCost.innerText.replace(/[^0-9]/g, "")),
            shown: els.resInsuranceCost.innerText, region_factor: els.resRegFactor.innerText});
}
console.log(JSON.stringify(out));
"""


def calk_classes() -> list[dict]:
    chunk = CALK_COMPONENT.read_text(encoding="utf-8")
    return [{"class": m.group(1), "coefficient": float(m.group(2))}
            for m in re.finditer(r'\{class:"([^"]+)",coefficient:([0-9.]+)', chunk)]


def calculators_script() -> str:
    page = CALCULATORS_PAGE.read_text(encoding="utf-8")
    for m in re.finditer(r"<script(?![^>]*src)[^>]*>(.*?)</script>", page, re.S):
        if "REGION_DATA" in m.group(1):
            return m.group(1)
    raise SystemExit("calculators.kz: скрипт расчёта не найден в закреплённой странице")


def calculators_options() -> dict[str, set[str]]:
    page = CALCULATORS_PAGE.read_text(encoding="utf-8")
    return {m.group(1): set(re.findall(r'<option value="([^"]*)"', m.group(2)))
            for m in re.finditer(r'<select id="([^"]+)"[^>]*>(.*?)</select>', page, re.S)}


def node(source: str) -> list:
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(source)
    done = subprocess.run(["node", handle.name], capture_output=True, text=True, check=False)
    Path(handle.name).unlink()
    if done.returncode:
        raise SystemExit(f"node: {done.stderr}")
    return json.loads(done.stdout)


def theirs(cases: list[dict]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    calk = [c for c in cases if c.get("calk")]
    if calk:
        answers = node(CALK_HARNESS % {
            "module": json.dumps(CALK_COEFFICIENTS.as_uri()),
            "classes": json.dumps(calk_classes()),
            "cases": json.dumps([c["calk"] for c in calk], ensure_ascii=False)})
        for case, answer in zip(calk, answers):
            result.setdefault(case["id"], {})["calk"] = answer
    options = calculators_options()
    other = [c for c in cases if c.get("calculators")]
    for case in other:
        for field, value in case["calculators"].items():
            if field in options and str(value) not in options[field]:
                raise SystemExit(f"{case['id']}: у calculators.kz нет варианта {field}={value}")
    if other:
        answers = node(CALCULATORS_HARNESS % {
            "script": json.dumps(calculators_script()),
            "cases": json.dumps([c["calculators"] for c in other], ensure_ascii=False)})
        for case, answer in zip(other, answers):
            result.setdefault(case["id"], {})["calculators"] = answer
    return result


# ============================================================================
# Сценарии
# ============================================================================

HEADER = """language "law.core" version "0.1";
package kz.corpus.ogpovts version "0.1.0";
namespace "urn:kz:corpus:clir:ogpo-vts";

// ПОРОЖДЁН tools/foreign_premium.py --emit из tools/foreign-premium-cases.json —
// не править руками. Ожидание выведено НЕЗАВИСИМОЙ моделью инструмента по
// закреплённым текстам (ст. 19 Закона № 446-II, Правила № 140, постановление
// АРРФР № 72), а не снято с ответа движка; чужие ответы и их квалификация —
// tests/foreign/REPORT.md.
//
// Дело {case_id}: {rationale}
"""

BM = "kz.corpus.bonus_malus"


def facts(case: dict) -> list[str]:
    c = f'entity_ref("urn:kz:ogpo:contract:foreign-{case["id"]}")'
    d = f'entity_ref("urn:kz:bm:ogpo:foreign-{case["id"]}")'
    rows = [
        f"territory_basis({c}, {case['basis']})",
        f"registration_territory({c}, {case['territory']})",
        f"vehicle_type_of({c}, {case['vehicle']})",
        f"insured_kind_of({c}, {case['insured']})",
        f"vehicle_operation_term_years({c}, {case['operation_term']})",
        f'"urn:kz:corpus:clir:ogpo-vts:table:operation-term-coefficient/input"({case["operation_term"]})',
        f"raschet_bonus_malus_dogovora({c}, {d})",
    ]
    if case["insured"] == "NaturalPerson":
        rows += [
            f"insured_age_years({c}, {case['age']})",
            f"driving_experience_years({c}, {case['experience']})",
            f'"urn:kz:corpus:clir:ogpo-vts:table:age-experience-coefficient/input"({case["age"]}, {case["experience"]})',
        ]
    bm = case["bonus_malus"]
    if bm["kind"] == "ordinary":
        rows += [
            f"{BM}::osnovanie_iz_bazy_dannykh({d}, {BM}::OtsutstvieInformatsiiOSluchayakh)",
            f"{BM}::deystvuyushchiy_klass({d}, {BM}::{bm['klass']})",
            f"{BM}::dney_strakhovaniya_s_poslednego_izmeneniya({d}, 269)",
        ]
    elif bm["kind"] == "first":
        rows.append(f"{BM}::nepreryvnogo_strakhovaniya_270_dney_v_baze_net({d})")
    elif bm["kind"] == "taxi_legal":
        rows += [
            f"{BM}::strakhovatel_yurlitso_ip_ili_krestyanskoe_khozyaystvo({d})",
            f"{BM}::oked_arendy_lizinga_avtobusov_ili_taksi({d})",
            f"{BM}::dostup_k_svedeniyam_punkta_3({d})",
        ]
    return rows


def lawtest(case: dict) -> str | None:
    if case["legal_year"] != 2026:
        return None
    contract = f'entity_ref("urn:kz:ogpo:contract:foreign-{case["id"]}")'
    lines = [HEADER.format(case_id=case["id"], rationale=case["rationale"]),
             f'test "urn:query:ogpo-chuzhoy-{case["id"]}" {{', "    given {", "        context {",
             "            decision_time @2026-09-15T12:00:00+05:00;",
             "            knowledge_time @2026-09-15T12:00:00+05:00;",
             "            legal_time @2026-09-15;",
             '            timezone "Asia/Almaty";', "        }"]
    for i, row in enumerate(facts(case)):
        lines.append(f'        assert "f{i}": {row} {{ origin case_input; }}')
    lines.append("    }")
    ours = case.get("ours")
    if ours is None:
        # Граница закона: пункт 7 не называет стажа ровно двух лет.
        lines += [f"    evaluate truth(applicable_driver_coefficient({contract}, 1.00));",
                  "    expect result_kind == PROPOSITION;",
                  "    expect truth_status == NEITHER;",
                  "    expect evaluation_status == COMPUTED;"]
    else:
        lines += [f"    evaluate truth(annual_premium_calculated({contract}, {ours} KZT));",
                  "    expect result_kind == PROPOSITION;",
                  "    expect truth_status == TRUE_ONLY;",
                  "    expect evaluation_status == COMPUTED;"]
    lines.append("}")
    return "\n".join(lines) + "\n"


def test_path(case: dict) -> Path:
    return TESTS / f"{PREFIX}{case['id']}.lawtest"


# ============================================================================
# Отчёт
# ============================================================================

def verdict(ours: str | None, their: dict | None) -> str:
    if their is None:
        return "—"
    if "error" in their:
        return f"не вводится: {their['error']}"
    if ours is None:
        return f"{their['premium']:,} — ГРАНИЦА".replace(",", " ")
    mark = "✓" if tenge(Fraction(ours)) == their["premium"] else "**расходится**"
    return f"{their['premium']:,} {mark}".replace(",", " ")


def report(data: dict) -> str:
    rows = ["| дело | наш ответ (точно) | до тенге | calk.kz | calculators.kz |",
            "|---|---|---|---|---|"]
    for case in data["cases"]:
        ours = case.get("ours")
        snap = case.get("theirs", {})
        rows.append("| `{}` | {} | {} | {} | {} |".format(
            case["id"],
            ours if ours is not None else ("нет (граница)" if case["legal_year"] == 2026
                                           else "нет (год вне редакции)"),
            f"{tenge(Fraction(ours)):,}".replace(",", " ") if ours is not None else "—",
            verdict(ours, snap.get("calk")),
            verdict(ours, snap.get("calculators"))))
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    for flag in ("--snapshot", "--expect", "--emit", "--check", "--report"):
        mode.add_argument(flag, action="store_true")
    args = parser.parse_args()
    data = json.loads(CASES.read_text(encoding="utf-8"))
    cases = data["cases"]

    if args.snapshot or args.expect:
        if args.snapshot:
            snap = theirs(cases)
            for case in cases:
                case["theirs"] = snap.get(case["id"], {})
        if args.expect:
            for case in cases:
                value = model(case)
                case["ours"] = decimal_text(value) if value is not None else None
        CASES.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0

    if args.emit:
        suites = []
        for case in cases:
            text = lawtest(case)
            if text is not None:
                test_path(case).write_text(text, encoding="utf-8")
                suites.append(f"tests/{test_path(case).name}")
        print(json.dumps(suites, ensure_ascii=False))
        return 0

    if args.report:
        print(report(data))
        return 0

    problems = check_model_numbers()
    snap = theirs(cases)
    for case in cases:
        value = model(case)
        want = decimal_text(value) if value is not None else None
        if case.get("ours") != want:
            problems.append(f"{case['id']}: ours {case.get('ours')} ≠ модель {want}")
        if case.get("theirs", {}) != snap.get(case["id"], {}):
            problems.append(f"{case['id']}: снимок их ответа устарел")
        text = lawtest(case)
        path = test_path(case)
        if text is None:
            if path.exists():
                problems.append(f"{path.name}: сценарий у дела без ответа закона")
        elif not path.exists() or path.read_text(encoding="utf-8") != text:
            problems.append(f"{path.name}: не порождён или изменён руками")
    known = {test_path(c).name for c in cases}
    for path in TESTS.glob(f"{PREFIX}*.lawtest"):
        if path.name not in known:
            problems.append(f"{path.name}: сценарий без дела в cases")
    for line in problems:
        print(f"FAIL {line}")
    print("OK" if not problems else f"{len(problems)} проблем")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
