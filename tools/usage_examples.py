#!/usr/bin/env python3
"""Run the README usage examples with the pinned evaluator and check their answers.

Every command below must appear verbatim in README.md, and each answer must
match the catalog card it demonstrates. Expectations are taken from the case
package's own checks, not from this script's output.

    python3 tools/usage_examples.py --law-cli "$tools/law-cli"
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
EXAMPLE = "packages/kz.corpus.vred_ts/examples/gibel-i-detali"
CATALOG = "packages/kz.corpus.vred_ts/analysis/questions.json"
PAYMENT = ("evaluate collect amount: Money where "
           "kz.corpus.vred_ts::strakhovaya_vyplata_pri_gibeli(r: raschet, amount: amount);")

# (catalog card id, case, query id, arguments after `ask`, expectation)
EXAMPLES = [
    ("unichtozheno", "Gibel", "unichtozheno",
     [EXAMPLE, "--case", "Gibel", "--query-json", f"{EXAMPLE}/queries/unichtozheno.json"],
     {"truth": "TRUE_ONLY", "rule": "EkonomicheskayaNetselesoobraznost"}),
    ("vyplata-pri-gibeli", "Gibel", "vyplata",
     [EXAMPLE, "--case", "Gibel", "--query", PAYMENT, "--query-id", "vyplata"],
     {"value": [{"currency": "KZT", "kind": "value", "type": {"name": "urn:law:std#Money"},
                 "value": "850000"}],
      "rule": "VyplataZaMinusomGodnykhOstatkov"}),
    ("pochemu-ne-vyplata", "Molchanie", "pochemu-ne-vyplata",
     [EXAMPLE, "--case", "Molchanie", "--query-json", f"{EXAMPLE}/queries/pochemu-ne-vyplata.json"],
     {"truth": "NEITHER", "blockers": True}),
]


def applied_rules(document: dict) -> set[str]:
    return {node["id"].split(":apply:")[1].split(":")[0]
            for node in document.get("proofGraph", {}).get("nodes", []) if ":apply:" in node["id"]}


def check(law_cli: str) -> list[str]:
    problems: list[str] = []
    readme = README.read_text(encoding="utf-8")
    cards = {card["id"] for card in json.loads((ROOT / CATALOG).read_text(encoding="utf-8"))["questions"]}
    for card, case, query_id, args, want in EXAMPLES:
        where = f"{case}/{query_id}"
        before = len(problems)
        shown = '"$tools/law-cli" ask ' + shlex.join(args)
        if shown not in readme:
            problems.append(f"{where}: README.md does not show the command {shown}")
        if card not in cards:
            problems.append(f"{where}: catalog card {card!r} is missing from {CATALOG}")
        completed = subprocess.run([law_cli, "ask", *args], cwd=ROOT, capture_output=True,
                                   text=True, check=False)
        if completed.returncode != 0:
            output = (completed.stderr.strip() or completed.stdout.strip())[:800]
            problems.append(f"{where}: law-cli exited {completed.returncode}: {output}")
            continue
        document = json.loads(completed.stdout)
        answers = [r for r in document.get("results", []) if f"#case/{case}/query/{query_id}" in r.get("id", "")]
        if len(answers) != 1:
            problems.append(f"{where}: expected one answer, found {len(answers)}")
            continue
        answer = answers[0]
        if answer.get("evaluationStatus") != "COMPUTED":
            problems.append(f"{where}: status {answer.get('evaluationStatus')}")
        if "truth" in want and answer.get("truthStatus") != want["truth"]:
            problems.append(f"{where}: truth {answer.get('truthStatus')}, expected {want['truth']}")
        if "value" in want and answer.get("value") != want["value"]:
            problems.append(f"{where}: value {answer.get('value')}, expected {want['value']}")
        if want.get("blockers") and not answer.get("value", {}).get("value", {}).get("blockers"):
            problems.append(f"{where}: why_not names no blocking premise")
        if want.get("rule") and want["rule"] not in applied_rules(document):
            problems.append(f"{where}: rule {want['rule']} is not in the proof graph")
        if len(problems) == before:
            print(f"{where}: OK ({want.get('truth') or want['rule']})")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--law-cli", required=True, help="pinned law-cli from toolchain.lock.json")
    args = parser.parse_args()
    problems = check(args.law_cli)
    for line in problems:
        print(f"usage-examples: {line}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
