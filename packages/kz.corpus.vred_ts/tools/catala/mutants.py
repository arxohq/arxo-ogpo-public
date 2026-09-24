#!/usr/bin/env python3
"""Targeted mutations of the kz.corpus.vred_ts model: tests must catch them.

    python3 corpus/laws/kz/vred-ts/tools/catala/mutants.py [--only ID] [--keep]

Each mutation drops ONE material condition, exception, or boundary
(threshold, unit, the clause 3-1 defeater, a form's sub-item). The mutated
package is lowered by the compiler into a private snapshot and run through
`lawc test` against ALL of the package's declared suites (authored,
catala-parity, vred_ts). A mutation counts as killed if at least one
scenario fails. The shared CLIR, locks, and registries are left untouched;
the run uses only the Rust evaluator — byte equality with the oracle is the
profile's job, not this tool's.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parents[1]
ROOT = PACKAGE.parents[3]
sys.path[:0] = [str(ROOT / "corpus"), str(ROOT / "corpus/lib"), str(ROOT / "engines/lawref")]

#: Mutations are pinned to the subject module FILE `modules/<area>/…`. The
#: anchor is the exact source text, and its uniqueness is checked below: a
#: stale anchor fails the run instead of silently skipping the mutation.
#:
#: SIX ANCHORS WENT STALE BEFORE THIS PORT and are restored here (M01-M03,
#: M11, M14, M17): the 09.09.2026 migrations moved the package to named
#: arguments (`f(x: x)`), lifted the death threshold into a temporary `let`,
#: and gave the `unless` clauses names. The tool would have failed on the
#: very first mutant; each mutation's meaning is preserved, expectations
#: unchanged.
MUTANTS = [
    # id, file, what it was, what to replace it with, what is lost
    ("M01", "modules/vyplata/gibel-ts.law", "when costs > porog_gibeli;", "when costs >= porog_gibeli;",
     "cl. 9: \"exceed\" → \"not less than\" (boundary exactly 80%)"),
    ("M02", "modules/vyplata/gibel-ts.law", "let porog_gibeli: Money = market * 0.8;",
     "let porog_gibeli: Money = market * 0.7;", "cl. 9: threshold 80% → 70%"),
    ("M03", "modules/vyplata/gibel-ts.law", "let vyplata: Money = market - salvage;",
     "let vyplata: Money = market;", "cl. 9: payout without deducting salvage value"),
    ("M04", "modules/vyplata/gibel-ts.law", "        when not ostatki_peredany_v_sobstvennost_strakhovshchika(r);\n",
     "", "cl. 9: second alternative with no established negation of salvage transfer"),
    ("M05", "modules/detali/otsenka.law", "when distance <= 15000 km;", "when distance < 15000 km;",
     "cl. 10 sub-cl. 1: \"does not exceed\" → strictly less (boundary 15,000 km)"),
    ("M06", "modules/detali/otsenka.law", "when distance <= 20000 km;", "when distance < 20000 km;",
     "cl. 10 sub-cl. 2: boundary 20,000 km"),
    ("M07", "modules/detali/otsenka.law", "        when nakhoditsya_na_garantiynom_obsluzhivanii(v);\n", "",
     "cl. 10 sub-cl. 2: lost the warranty-service condition"),
    ("M08", "modules/detali/otsenka.law", "        when detal_ne_podvergalas_remontu(d);\n", "",
     "cl. 10: lost the \"was not repaired\" condition"),
    ("M09", "modules/otchet/sroki-i-vozrazheniya.law", "assert srok_predostavleniya_otcheta(5 business_day);",
     "assert srok_predostavleniya_otcheta(6 business_day);", "cl. 3: five business days → six"),
    ("M10", "modules/otchet/sroki-i-vozrazheniya.law", "assert srok_otmetki_poterpevshego(3 business_day);",
     "assert srok_otmetki_poterpevshego(3 calendar_day);", "cl. 3: business days → calendar days"),
    ("M11", "modules/otchet/sroki-i-vozrazheniya.law",
     "    unless UproshchennoeOformlenie when uproshchennoe_oformlenie_proisshestviya(r)\n"
     "        and srok_predostavleniya_otcheta(limit)\n"
     "        and osmotr_osushchestvlen_strakhovshchikom(r: r, day: day);\n",
     "", "cl. 3-1: lost the simplified-processing defeater for the report deadline"),
    ("M12", "modules/otchet/sroki-i-vozrazheniya.law", "        when got > due;\n", "        when got >= due;\n",
     "cl. 3: a report on the last day of the deadline counts as late"),
    ("M13", "modules/raschet/otsenshchiki.law", "        when n >= 2;\n", "        when n >= 1;\n",
     "cl. 4-1: one appraiser is enough"),
    ("M14", "modules/detali/otsenka.law",
     "    unless DetalBezIznosa when detal_otsenivaetsya_bez_iznosa(d)\n"
     "        and stoimost_detali_s_uchetom_iznosa(d: d, amount: amount);\n", "",
     "annex 3 footnote: depreciation also applies in the cl. 10 cases (two amounts)"),
    ("M15", "modules/otchet/oformlenie.law", '        when round(amount, 0, "HALF_UP") == amount;\n', "",
     "annex 3 cl. 2: lost the rounding-to-tenge check"),
    ("M16", "modules/osmotr/akt.law", "        when akt_vin(a: a, vin: _);\n", "",
     "annex 2 sub-cl. 4.1: a report without a VIN counts as complete"),
    ("M17", "modules/osmotr/provedenie.law", "        when zayavlenie_o_dopolnitelnom_osmotre(z: z, r: r);\n", "",
     "cl. 2 part 4: additional inspection without its own application"),
    ("M18", "modules/osmotr/usloviya.law", "        when not dokumenty_o_povrezhdeniyakh_v_dtp_predstavleny(r);\n", "",
     "cl. 7: inadmissibility without an established absence of documents"),
    ("M19", "modules/osmotr/usloviya.law", "        when fotosemka_povrezhdeniy_provodima(r);\n", "",
     "cl. 7: lost the photography condition"),
    ("M20", "modules/otchet/oformlenie.law", "        when pechat_otsutstvuet(o);\n", "        when otchet_podpis_utverzhdayushchego(o: o, fio: _);\n",
     "annex 3 cl. 1: certified by a single signature with no established absence of a seal"),
]


def suites_of_package() -> list[tuple[str, list[Path], list[str]]]:
    manifest = tomllib.loads((PACKAGE / "law.toml").read_text(encoding="utf-8"))
    out = []
    for section in manifest["tests"]:
        parts = section.get("part") or [section]
        for part in parts:
            out.append((section["family"], [PACKAGE / s for s in part["suites"]], part["world"]))
    return out


def run_lawc(listing: list[Path], world: list[str], lawcli: Path, tmp: Path, tag: str) -> tuple[int, list[str]]:
    from lawtests.run import world_json, context_json
    program = tmp / f"{tag}.world.json"
    program.write_text(world_json(tuple(world)), encoding="utf-8")
    files = tmp / f"{tag}.list.json"
    files.write_text(json.dumps([str(p) for p in listing]), encoding="utf-8")
    imports = tmp / f"{tag}.imports.json"
    imports.write_text(context_json(tuple(world)), encoding="utf-8")
    result = subprocess.run([str(lawcli), "test", str(files), "--lawtest-list", "--program", str(program),
                             "--imports", str(imports), "--json"], capture_output=True, text=True)
    try:
        report = json.loads(result.stdout)
    except ValueError:
        return 1, [f"lawc test produced no report: {(result.stdout + result.stderr)[-500:]}"]
    failed = [f"{Path(t['test']).name}/{t['title']}" for t in report["tests"] if not t["passed"]]
    return len(failed), failed


def worker(state: Path, tmp: Path) -> int:
    """Child process: all of the package's suites under one mutant's state."""
    target = Path(os.environ.get("CARGO_TARGET_DIR", ROOT / "engines/lawc/target")).resolve()
    failed_all: list[str] = []
    for n, (family, files, world) in enumerate(suites_of_package()):
        _count, failed = run_lawc(files, world, target / "gate/law-cli", tmp, f"suite{n}")
        failed_all += failed
    print(json.dumps(failed_all, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--keep", action="store_true", help="do not delete the temporary directory")
    parser.add_argument("--worker", nargs=2, metavar=("STATE", "TMP"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        return worker(Path(args.worker[0]), Path(args.worker[1]))
    import gen_kz_clir as generator
    target = Path(os.environ.get("CARGO_TARGET_DIR", ROOT / "engines/lawc/target")).resolve()
    lawcli = target / "gate/law-cli"
    if not lawcli.exists():
        raise SystemExit("no engines/lawc/target/gate/law-cli: run sh verify/ci/run_all.sh first")
    generator.LAWCLI = lawcli
    calendar_raw = (ROOT / "corpus/clir/kz-official-calendar-2026.lawir.json").read_bytes()
    context = generator.import_context(calendar_raw)
    selected = [m for m in MUTANTS if not args.only or m[0] in args.only]
    survivors, rejected = [], []
    workdir = Path(tempfile.mkdtemp(prefix="vred-ts-mutants-"))
    try:
        for mid, filename, old, new, what in selected:
            source = workdir / mid / "vred-ts"
            shutil.copytree(PACKAGE, source, ignore=shutil.ignore_patterns("tests", "catala", "__pycache__", "analysis"))
            path = source / filename
            text = path.read_text(encoding="utf-8")
            if text.count(old) != 1:
                raise SystemExit(f"{mid}: anchor occurs {text.count(old)} times in {filename}: {old[:60]!r}")
            path.write_text(text.replace(old, new), encoding="utf-8")
            lowered = subprocess.run([str(lawcli), "lower", str(source), "--imports", str(_write(workdir / mid / "imports.json", context))],
                                     capture_output=True)
            if lowered.returncode:
                rejected.append((mid, what, lowered.stderr.decode()[-300:]))
                print(f"REJECTED {mid} ({what}): the compiler rejected the mutant")
                continue
            clir = workdir / mid / "clir"
            clir.mkdir()
            (clir / "kz-vred-ts.lawir.json").write_bytes(lowered.stdout)
            for name in ("kz-official-calendar-2026.lawir.json", "kz-official-2026.calendar.json"):
                shutil.copyfile(ROOT / "corpus/clir" / name, clir / name)
            state = workdir / mid / "state.json"
            state.write_text(json.dumps({"format": "law.work-profile-run/1", "root": str(ROOT), "clir": str(clir),
                                         "test_roots": ["corpus/laws/kz/vred-ts"], "legacy_modules": [],
                                         "legacy_aliases": {}}), encoding="utf-8")
            # Suites run in a CHILD process: the CLIR index and profile state
            # are cached per-process, and clearing the caches between
            # mutants would be more fragile than a fresh process.
            child = subprocess.run([sys.executable, __file__, "--worker", str(state), str(workdir / mid)],
                                    capture_output=True, text=True,
                                    env=dict(os.environ, LAW_WORK_PROFILE_STATE=str(state), CARGO_TARGET_DIR=str(target)))
            try:
                killed_by = json.loads(child.stdout)
            except ValueError:
                raise SystemExit(f"{mid}: child run produced no report: {(child.stdout + child.stderr)[-800:]}")
            if killed_by:
                print(f"KILLED   {mid} ({what}): {len(killed_by)} failures, e.g. {killed_by[0]}")
            else:
                survivors.append((mid, what))
                print(f"SURVIVED {mid} ({what}): no scenario failed")
    finally:
        if args.keep:
            print(f"temporary directory: {workdir}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)
    print(f"mutants {len(selected)}: killed {len(selected) - len(survivors) - len(rejected)}, "
          f"survived {len(survivors)}, rejected by the compiler {len(rejected)}")
    return 1 if survivors else 0


def _write(path: Path, payload) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


if __name__ == "__main__":
    raise SystemExit(main())
