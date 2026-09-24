#!/usr/bin/env python3
"""Source coverage matrix: clause → requirement → implementation → scenarios → reference → status.

    python3 corpus/laws/kz/vred-ts/tools/coverage_matrix.py          # check and rewrite COVERAGE-MATRIX.md
    python3 corpus/laws/kz/vred-ts/tools/coverage_matrix.py --check  # check only (for CI and review)

Machine check (analysis/coverage-matrix.json):
  1. `quote` of each row is an EXACT substring of the pinned text sources/vred-ts/ru.txt;
  2. every name in `rules` is declared in a .law file of the package (modules/** and root, excluding nested packages), and EVERY declared rule is named by at least one row;
  3. every name in `tests` is a test title in tests/**/*.lawtest, and EVERY title is named by at least one row;
  4. every `cases` entry is an id from tools/catala/cases.json, and every id is named by at least one row;
  5. status `executable` requires non-empty rules and tests; `fact` requires non-empty tests; `boundary`/`descriptive` requires a non-empty `reason`;
  6. open questions in `questions` reference Q-identifiers from the `open_questions` block.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
MATRIX = PACKAGE / "analysis" / "coverage-matrix.json"
OUT = PACKAGE / "COVERAGE-MATRIX.md"
STATUSES = {"executable": "executed by rules", "fact": "case fact (delegated by the Rules)",
            "boundary": "boundary with a reason", "descriptive": "description without a legal consequence"}


def own_laws() -> list[Path]:
    """`*.law` files of THIS package: recursive walk, nested packages excluded.

    The earlier form called `PACKAGE.glob("0*.law")` and relied on
    end-to-end file numbering: after the norms moved to
    `modules/<area>/` it would have found zero rules, while the
    matrix's two-way completeness check would have stayed green — an
    empty set of rules violates none of its assertions. The walk is
    the same one the compiler uses over the directory (§22,
    DECISION-0033): a subdirectory with its OWN `law.toml` is another
    package's boundary (`examples/…`), and its sources do not belong
    to the canon.
    """
    out: list[Path] = []
    for path in sorted(PACKAGE.rglob("*.law")):
        parent, nested = path.parent, False
        while parent != PACKAGE:
            if (parent / "law.toml").is_file():
                nested = True
                break
            parent = parent.parent
        if not nested:
            out.append(path)
    return out


def declared_rules() -> set[str]:
    names = set()
    for path in own_laws():
        names.update(re.findall(r"^\s*rule\s+([A-Za-z0-9_]+)", path.read_text(encoding="utf-8"), re.M))
    return names


def test_titles() -> set[str]:
    titles = set()
    for path in sorted(PACKAGE.glob("tests/**/*.lawtest")):
        titles.update(re.findall(r'^test\s+"([^"]+)"', path.read_text(encoding="utf-8"), re.M))
    return titles


def case_ids() -> set[str]:
    data = json.loads((PACKAGE / "tools/catala/cases.json").read_text(encoding="utf-8"))
    return {c["id"] for c in data["cases"]}


def expand(names: list[str], universe: set[str]) -> list[str]:
    """`prefix*` is expanded over the universe of names (parity-test titles, cases)."""
    out: list[str] = []
    for name in names:
        if name.endswith("*"):
            matches = sorted(n for n in universe if n.startswith(name[:-1]))
            if not matches:
                out.append(name)  # keep so the check fails
            out.extend(matches)
        else:
            out.append(name)
    return out


def check(matrix: dict) -> tuple[list[str], dict]:
    problems: list[str] = []
    source = (PACKAGE / "sources/vred-ts/ru.txt").read_text(encoding="utf-8")
    rules, titles, cases = declared_rules(), test_titles(), case_ids()
    used_rules, used_titles, used_cases = set(), set(), set()
    questions = {q["id"] for q in matrix.get("open_questions", [])}
    resolved = {}
    for row in matrix["rows"]:
        rid = row["id"]
        if row["quote"] not in source:
            problems.append(f"{rid}: quote is not a substring of the source: {row['quote'][:60]!r}")
        if row["status"] not in STATUSES:
            problems.append(f"{rid}: unknown status {row['status']}")
        r_tests = expand(row.get("tests", []), titles)
        r_cases = expand(row.get("cases", []), cases)
        for name in row.get("rules", []):
            if name not in rules:
                problems.append(f"{rid}: rule {name} is not declared")
            used_rules.add(name)
        for name in r_tests:
            if name not in titles:
                problems.append(f"{rid}: test {name} does not exist")
            used_titles.add(name)
        for name in r_cases:
            if name not in cases:
                problems.append(f"{rid}: case {name} is not in cases.json")
            used_cases.add(name)
            # A case's generated parity test carries a title derived from its id.
            used_titles.add(f"urn:query:vred-parity:{name}")
        for q in row.get("questions", []):
            if q not in questions:
                problems.append(f"{rid}: question {q} is not described in open_questions")
        if row["status"] == "executable" and (not row.get("rules") or not r_tests):
            problems.append(f"{rid}: status executable requires rules and tests")
        if row["status"] == "fact" and not r_tests:
            problems.append(f"{rid}: status fact requires tests")
        if row["status"] in ("boundary", "descriptive") and not row.get("reason"):
            problems.append(f"{rid}: status {row['status']} requires a reason")
        resolved[rid] = (r_tests, r_cases)
    for name in sorted(rules - used_rules):
        problems.append(f"rule {name} is not named by any row of the matrix")
    for name in sorted(titles - used_titles):
        problems.append(f"test {name} is not named by any row of the matrix")
    for name in sorted(cases - used_cases):
        problems.append(f"case {name} is not named by any row of the matrix")
    return problems, {"rules": len(rules), "tests": len(titles), "cases": len(cases), "resolved": resolved}


def render(matrix: dict, stats: dict) -> str:
    lines = ["# Source coverage matrix — kz.corpus.vred_ts", "",
             "Generated by `tools/coverage_matrix.py` from `analysis/coverage-matrix.json`; the check "
             "is machine-run (quotes are substrings of the pinned text, rule/test/case names must "
             "exist, completeness is two-way). Do not edit by hand.", "",
             f"Rules: {stats['rules']}; test titles: {stats['tests']}; comparison cases: {stats['cases']}.", "",
             "| No. | source unit | normative requirement | implementation | scenarios | Catala/Python reference | status |",
             "|---|---|---|---|---|---|---|"]
    for row in matrix["rows"]:
        tests, cases = stats["resolved"][row["id"]]
        rules = ", ".join(f"`{r}`" for r in row.get("rules", [])) or "—"
        facts = ", ".join(f"`{f}`" for f in row.get("facts", []))
        impl = rules + (f"; facts: {facts}" if facts else "")
        status = STATUSES[row["status"]]
        if row.get("reason"):
            status += f": {row['reason']}"
        if row.get("questions"):
            status += " (questions: " + ", ".join(row["questions"]) + ")"
        shown_tests = ", ".join(tests) if len(tests) <= 6 else f"{len(tests)} tests ({tests[0]} … {tests[-1]})"
        shown_cases = ", ".join(cases) if len(cases) <= 8 else f"{len(cases)} cases ({cases[0]} … {cases[-1]})"
        lines.append(f"| {row['id']} | {row['unit']} | {row['requirement']} | {impl} | {shown_tests or '—'} | {shown_cases or '—'} | {status} |")
    lines += ["", "## Open questions for the owner", ""]
    for q in matrix.get("open_questions", []):
        lines.append(f"- **{q['id']}.** {q['text']} Reading adopted pending a decision: {q['reading']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    problems, stats = check(matrix)
    for p in problems:
        print("FAIL " + p)
    text = render(matrix, stats)
    if args.check:
        if OUT.read_text(encoding="utf-8") != text:
            problems.append("COVERAGE-MATRIX.md is stale: regenerate it")
            print("FAIL COVERAGE-MATRIX.md is stale")
    else:
        OUT.write_text(text, encoding="utf-8")
    print(f"coverage-matrix: rows {len(matrix['rows'])}, rules {stats['rules']}, tests {stats['tests']}, cases {stats['cases']}, "
          f"issues {len(problems)}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
