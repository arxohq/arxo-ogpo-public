# kz.corpus.vred_ts — amount of damage caused to a vehicle

Formalization of the Rules for Determining the Amount of Damage Caused to a
Vehicle (Resolution of the Board of the National Bank of the Republic of
Kazakhstan of 28 January 2016 No. 14). The package is a **sample of
subject-matter layout**: the norms are organized by the tasks the insurer
solves, not by file numbers (`docs/PACKAGE-LAYOUT.ru.md`, section "Subject-
matter layout of norms").

- package: `kz.corpus.vred_ts`, version `0.1.0`, `language "law.core" version "0.2"`;
- namespace: `urn:kz:corpus:clir:vred-ts`;
- dependency: `kz.corpus.clir.official_calendar` `0.1.0` — snapshot of the
  official calendar §85, input of the daily time limits in cl. 3;
- CLIR snapshot: `corpus/clir/kz-vred-ts.lawir.json`.

## What the package does and does not do

**Does.** Determines who conducts the assessment and on what basis; whether
the inspection report is complete and properly formalizes the inspection;
whether the inspection is admissible; whether the vehicle is deemed destroyed
and the amount of the payout in that case; whether a part is assessed without
depreciation and what value enters the calculation; the last days of the
three time limits in cl. 3 and the deontic positions of §§122—137 for all
duties of the report.

**Does not do — and this is a boundary of the Rules themselves, not a gap in
the model:**

| boundary | why |
|---|---|
| the amount of depreciation wear is not calculated | the Rules give no formula: cl. 2 refers to licensed software, cl. 11 to an internet resource, annex 3 calls the depreciation calculation a section of the report. Depreciation enters as a case fact (`stoimost_detali_s_uchetom_iznosa`) |
| the deadline for inspection and drawing up the report is not computed | part one of cl. 3 delegates it to cl. 3 of art. 22 of the Law; the Law's pinned bytes are not in the package |
| the amount of the payout when the report is not submitted is not computed | cl. 3-1 of art. 22 of the Law; only the RIGHT to such a payout is computed |
| rounding to tenge is not performed | annex 3 cl. 2 requires rounding but does not name the mode (§50); the module checks that the value is already rounded |
| the §86 policy for computing time limits is not declared as a norm | the Rules name the deadlines but do not establish a method of computation; the policy is a case input (Civil Code of the RK, art. 173, 176) |
| the IIN mask ("12 digits") and the VIN mask ("17 characters without I, O, Q") are not checked | these are not norms of Rules No. 14: the IIN mask is cl. 2 of the Rules for Forming the IIN (Order of the MIA No. 521, package `kz.corpus.iin`, fragment `IIN_RULES_P2_STRUCTURE`), the VIN mask is ISO 3779 / GOST 33990, neither of which is in the corpus (`us.cfr.vin` is a different jurisdiction). The language has been able to express masks since E-0166 (`text_matches`, `constraint` §93); wiring it in awaits a `pub fragment` from the neighboring package and re-pinning of the frozen packages (DECISION-0191 §2.9, DECISION-0189) |

## What questions the package answers

The catalog of provided-for queries and what each is verified by —
[QUESTIONS.md](QUESTIONS.md) (DECISION-0190): 41 cards across six tasks,
6 boundaries with a typed reason, 13 internal links; 43 derivable predicates
and 12 norms are closed in both directions. The authored input is
`analysis/questions.json`; the purpose and limitations verbatim —
`package-info.json`; `QUESTIONS.md` is generated and edited only by the
generator. A card is a parameterized request template §172, not an answer:
the answer is the evaluation document with proof; the reasons for a specific
case are issues and `why_not`. MCP lists the same cards:
`law_packages({"package": "kz-vred-ts", "catalog": "questions"})`; the
package detail names their count and this call.

## Tree of subject-matter modules

```
corpus/laws/kz/vred-ts/
├── package.law                 §22 header, §23 import, shared vocabulary
├── sources.law                 source, edition, publication, 19 fragments
├── modules/
│   ├── raschet/                assessment organization
│   │   ├── organizatsiya.law         insurer's basis for the assessment and its stages
│   │   ├── zayavlenie.law            application and annex 1
│   │   ├── otsenshchiki.law          engaged appraiser, choice from two
│   │   └── uchastie-poterpevshego.law duties of the injured party
│   ├── osmotr/                 inspection
│   │   ├── usloviya.law              conditions of possibility and admissibility
│   │   ├── provedenie.law            service station, additional inspection
│   │   └── akt.law                   inspection report, annex 2
│   ├── vyplata/                payout
│   │   ├── gibel-ts.law              destruction and amount of the payout
│   │   └── oplata-remonta.law        repair in lieu of a payout
│   ├── detali/
│   │   └── otsenka.law               assessment of the part to be replaced
│   ├── otchet/                 damage report
│   │   ├── sroki-i-vozrazheniya.law  time limits, marks, objections, replies
│   │   └── oformlenie.law            annex 3, final check
│   └── iznos/
│       └── dostupnost-rascheta.law   availability of the depreciation calculation
├── tests/                      §267 scenarios (see table below)
├── examples/gibel-i-detali/    teaching §168.4 cases (its own package)
├── sources/vred-ts/            pinned bytes of the publication
├── analysis/                   template findings, coverage matrix, question catalog
├── QUESTIONS.md                generated from analysis/questions.json (DECISION-0190)
├── package-info.json           purpose, limitations (verbatim at the catalog's boundaries), examples
└── tools/                      matrix generator, Catala comparison
```

`modules/` sets **organizational** boundaries. The compiler still sees a
SINGLE package namespace: the language introduces no internal `import`/
`export` or scopes (§22, §24); any declaration is visible to any module.
Checkable internal contracts are a possible next step, not a property of
this layout. The only real boundary inside the tree is `examples/`: it has
its own `law.toml`, and for the compiler it is a different package (T102).

## Task → file → inputs → results → scenarios

Inputs are case facts (`kind empirical`); results are derived facts
(`kind institutional`) and deontic norms. The full line-by-line reconciliation
with the source text — [COVERAGE-MATRIX.md](COVERAGE-MATRIX.md).

| task | file | source clauses | key inputs | results | scenarios |
|---|---|---|---|---|---|
| Who conducts the assessment and what its organization includes | `modules/raschet/organizatsiya.law` | cl. 2 (part 1), cl. 6 | `raschet_osushchestvlyaet_strakhovshchik`, `spo_primeneno`, `mesto_i_vremya_osmotra_soglasovany` | `raschet_vedetsya_po_pravilam`, `organizatsiya_rascheta_vypolnena` | `tests/regression/` |
| Application basis and its content | `modules/raschet/zayavlenie.law` | annex 1 | `zayavlenie_po_raschetu`, `zayavlenie_soderzhit_datu_i_vremya_postupleniya`, `zayavlenie_soderzhit_svedeniya_ob_imushchestve` | `zayavlenie_soderzhit_svedeniya_prilozheniya_1` | `tests/osmotr/10-dopolnitelnyy-osmotr.lawtest`, `tests/regression/` |
| Engaged appraiser and choice from at least two | `modules/raschet/otsenshchiki.law` | cl. 4, cl. 4-1, cl. 2 (second branch §206) | `otsenshchik_privlechen_po_dogovoru`, `predlozheno_otsenshchikov` | `raschet_osushchestvlyaet_otsenshchik`, `vybor_otsenshchikov_obespechen`, duty `PredlozhitDvukhOtsenshchikov` | `tests/raschet/07-dva-otsenshchika.lawtest`, `tests/raschet/08-odin-otsenshchik.lawtest`, `tests/integration/` (both files), `tests/regression/` |
| Duties of the injured party from the day of application | `modules/raschet/uchastie-poterpevshego.law` | cl. 2 (part 5) | `zayavlenie_predstavleno_v_den`, `imushchestvo_izmeneno_posle_proisshestviya`, `vozmozhnost_rascheta_predostavlena` | duties `SokhranitImushchestvo` (§124.2), `PredostavitVozmozhnostRascheta` | `tests/integration/17-pozitsii-otkrytykh-okon.lawtest` |
| When the inspection is possible and admissible | `modules/osmotr/usloviya.law` | cl. 7 | seven conditions of possibility, `opredelyaetsya_stoimost_vosstanovitelnogo_remonta`, `dokumenty_o_povrezhdeniyakh_v_dtp_predstavleny` | `osmotr_vozmozhen`, `osmotr_dopustim` | `tests/integration/15-nepolnye-i-protivorechivye-vkhody.lawtest`, `tests/regression/` |
| Where and how the inspection is conducted | `modules/osmotr/provedenie.law` | cl. 2 (parts 3, 4) | `trebovanie_ob_osmotre_na_sto`, `zayavlenie_o_dopolnitelnom_osmotre`, `skrytye_defekty_vyyavleny` | duty `OsmotrNaStantsii`, `dopolnitelnyy_osmotr_proveden_po_pravilam`, `korrektirovka_pri_skrytykh_defektakh_oformlyaetsya_dopolneniem` | `tests/osmotr/10-dopolnitelnyy-osmotr.lawtest`, `tests/integration/17-pozitsii-otkrytykh-okon.lawtest` |
| Content of the inspection report | `modules/osmotr/akt.law` | annex 2, cl. 2 (part 2) | 20 facts about the report's content (VIN, plate number, odometer photo, …) | `akt_soderzhit_svedeniya_prilozheniya_2`, `osmotr_oformlen` | `tests/osmotr/09-prilozhenie-2-podpunkty.lawtest`, `tests/regression/` |
| Destruction of the vehicle and the amount of the payout | `modules/vyplata/gibel-ts.law` | cl. 9 | `vosstanovlenie_tekhnicheski_nevozmozhno`, `ozhidaemye_raskhody_na_vosstanovlenie`, `rynochnaya_stoimost_na_datu_otcheta`, `ostatki_peredany_v_sobstvennost_strakhovshchika`, `stoimost_godnykh_k_realizatsii_ostatkov` | `ts_schitaetsya_unichtozhennym`, `strakhovaya_vyplata_pri_gibeli` | `tests/vyplata/` (three files), `tests/integration/15-…`, `tests/regression/` |
| Repair instead of a monetary payout | `modules/vyplata/oplata-remonta.law` | cl. 8 | `oplata_remonta_soglasovana` | power `OrganizovatOplatuRemonta` | `tests/regression/` |
| Assessment of the part to be replaced | `modules/detali/otsenka.law` | cl. 10, annex 3 (footnote) | `vladelets_fizicheskoe_litso` / `vladelets_yuridicheskoe_litso`, `srednegodovoy_probeg`, `detal_ranee_ne_povrezhdalas`, `rynochnaya_stoimost_novoy_detali`, `stoimost_detali_s_uchetom_iznosa` | `detal_otsenivaetsya_bez_iznosa`, `stoimost_zamenyaemoy_detali`, duty `PeredatZamenyaemuyuDetal` | `tests/detali/` (five files), `tests/integration/15-…`, `tests/regression/` |
| Time limits, marks, and objections around the report | `modules/otchet/sroki-i-vozrazheniya.law` | cl. 3, cl. 3-1 | `otchet_poluchen_poterpevshim`, `otmetka_nesoglasiya_poluchena_strakhovshchikom`, `osmotr_osushchestvlen_strakhovshchikom`, `uproshchennoe_oformlenie_proisshestviya` | three deadline boundaries, `otchet_ne_predostavlen_v_srok`, `pravo_na_vyplatu_po_punktu_3_1_stati_22_zakona`, four duties | `tests/otchet/11-…`, `tests/otchet/14-…`, `tests/otchet/16-…`, `tests/regression/vred-ts-w2.lawtest` |
| Formalization of the report | `modules/otchet/oformlenie.law` | annex 3, cl. 3 (part 5) | 29 facts about the report's content (title page, annexes, final value, approval, type) | `otchet_oformlen_po_prilozheniyu_3`, `otchet_sostavlen_po_pravilam` | `tests/otchet/13-prilozhenie-3-elementy.lawtest`, `tests/regression/` |
| Availability of the depreciation calculation | `modules/iznos/dostupnost-rascheta.law` | cl. 11 | `ombudsman_deystvuet`, `vozmozhnost_rascheta_iznosa_obespechena_*` | duties `ObespechitRaschetIznosaOmbudsmanom`, `ObespechitRaschetIznosaStrakhovshchikom` (open window) | `tests/regression/` |

The shared vocabulary `package.law` — five entities (`TransportnoeSredstvo`,
`Strakhovshchik`, `Poterpevshiy`, `RaschetVreda`, `Detal`) and five relations
(`raschet_po_ts`, `strakhovshchik_po_raschetu`, `poterpevshiy_po_raschetu`,
`detal_ts`, `spo_primeneno`): each is read by at least two modules.
Everything else is declared at its own task, including single-owner types —
`Zayavlenie`, `Otsenshchik`, `AktOsmotra`, `Otchet`, `StrakhovoyOmbudsman`.

## Scenarios

| directory | what is there | family |
|---|---|---|
| `tests/<area>/` | authored scenarios for one subject area; directories mirror `modules/` | `kz.corpus.vred_ts#authored` |
| `tests/integration/` | scenarios genuinely checking several areas at once (incomplete and contradictory inputs; deontic positions) | `kz.corpus.vred_ts#authored` |
| `tests/regression/` | the package's regression family — 33 scenarios in two parts | `vred_ts` (counted in regression) |
| `tests/parity/` | GENERATED comparison against the independent Catala model; edited only by `tools/catala/compare.py --emit` | `kz.corpus.vred_ts#catala-parity` |

Directories are created only where scenarios exist: `iznos/` has no authored
scenarios of its own, and no empty directory was created for the sake of
tree symmetry.

The split of the family's parts by world is preserved: the official
calendar snapshot §85 is supplied only to those scenarios that compute daily
time limits (`tests/otchet/11-…`, `tests/otchet/14-…`,
`tests/parity/parity-sroki.lawtest`, both parts of `tests/regression/`).
`tests/otchet/16-srok-bez-kalendarya.lawtest` checks the ABSENCE of the
calendar — it must not be added to that scenario's world.

## Checks

The active profile (DECISION-0184) is the single ordinary entry point:

```bash
sh verify/ci/run_all.sh
```

`--plan` prints the composition without compiling or executing; `--build-only
--output <directory>` saves a private CLIR snapshot without touching the
shared CLIR, locks, or registries. The full corpus (`--full`) is run only at
the owner's explicit request.

Package-specific checks:

```bash
python3 corpus/laws/kz/vred-ts/tools/coverage_matrix.py --check
python3 verify/ci/gates/coverage/check_package_questions.py --only corpus/laws/kz/vred-ts
python3 corpus/laws/kz/vred-ts/tools/catala/compare.py --check
python3 corpus/laws/kz/vred-ts/tools/catala/mutants.py
python3 .claude/skills/formalize-act/scripts/lint.py corpus/laws/kz/vred-ts/modules/osmotr/akt.law
```

## Teaching cases

[`examples/gibel-i-detali/`](examples/gibel-i-detali/README.md) — a nested
§168.4 case package with six cases and fifteen questions: destruction of the
vehicle, the 80% threshold, transfer of the remains, a part assessed without
depreciation, a silent case. It has its own `law.toml`, its own `law.lock`,
and an explicit import of the pinned canon; the canon does not know about
it. `tests/` checks the canon's expectations, `examples/` explains its
application and lets facts be varied — one does not replace the other.

## How to add

**A relation.** Declared in the module of the task that produces it, next to
the rules that read it. `kind empirical` is what a case brings; `kind
institutional` is what is derived. The `label ru official` mark is
mandatory. A relation moves to `package.law` only once it is read by at
least two modules, and at that point `package.law`'s header names exactly
who reads it.

**A rule.** Placed in the module of its own result and given an
`@source(...)` pointing to the fragment that produces it; a textual
disjunction ("либо", "или") is split into rules per §206, not written as
`or` in the body. A new rule must appear as a row in
[COVERAGE-MATRIX.md](COVERAGE-MATRIX.md) —
`analysis/coverage-matrix.json` + `tools/coverage_matrix.py`; completeness
there is bidirectional, and an unnamed rule fails the check.

**A scenario.** The file is placed in `tests/<area>/` of its own task (or in
`tests/integration/` if several areas are involved) and **must** be declared
as a `suites` entry in `law.toml` — an undeclared file is executed by
nothing, and the `check_lawtest_discovery` gate catches this. The §85
calendar is added to `world` only for the parts that compute daily time
limits. The test's title is also named in a row of the coverage matrix.

**A question.** A new derivable predicate or norm without a card fails
`check_package_questions.py`: add a card to `analysis/questions.json` (task,
question in Russian, form, parameters per the declaration, `evaluate …;`
template, test titles that execute exactly this query), or an `internal`
entry with a reason; a new boundary takes the `limitation` row verbatim from
`package-info.json`. Then `--only corpus/laws/kz/vred-ts --emit` regenerates
`QUESTIONS.md`.

**A module.** A new subject-matter directory `modules/<area>/` is created
without its own `law.toml`: the package remains one. The directory must be
named in `docs/PACKAGE-LAYOUT.ru.md` and in `lint.PACKAGE_SUBDIRS` if it is
a new KIND of package subdirectory (`modules/` itself is already named).
