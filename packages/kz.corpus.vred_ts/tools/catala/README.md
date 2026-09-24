# Independent implementation of the computational part in Catala, and comparison

This directory holds a second, independent-of-Law-DSL implementation of the
COMPUTATIONAL part of the Rules for Determining the Amount of Damage to a
Vehicle (Resolution of the Board of the National Bank of the Republic of
Kazakhstan No. 14 of 28.01.2016) in Catala 1.2.0, together with tools for
comparing three implementations — Catala, `lawc` (Rust), and `lawref` (the
Python oracle) — on the same cases, with expectations established from the
source text.

| file | what it is |
|---|---|
| `vred_ts.catala_en` | Catala model: cl. 3, 3-1, 4-1, 7, 9, 10, annex 3 cl. 2, and the footnote. Derived from the text `../../sources/vred-ts/ru.txt`, not translated from `.law` |
| `cases.json` | 65 reference cases: inputs, expectations (established manually from the text and the 2026 calendar), rationale, reference to the clause |
| `compare.py` | runner: generates `tests/parity/*.lawtest` from `cases.json`, runs Catala, both Law DSL evaluators, and a property mode with random cases against the Python reference |
| `mutants.py` | 20 targeted mutations of the `.law` model (dropped threshold, dropped defeater, dropped condition, dropped sub-clause form): each must be caught by the scenarios |
| `REPORT.md` | report: what is implemented, what confirms completeness, actual results, boundaries, open questions |

## Reproduction

Installing Catala (one time; verified on macOS, opam 2.5.2):

```sh
brew install opam ninja
opam init -c 4.14.2 --bare -n && opam switch create catala 4.14.2
eval $(opam env --switch=catala --set-switch) && opam install catala.1.2.0
```

Running from the repository root (`clerk` is looked up in PATH and in `~/.opam/*/bin`):

```sh
python3 corpus/laws/kz/vred-ts/tools/catala/compare.py --check      # tests/parity is up to date relative to cases.json
python3 corpus/laws/kz/vred-ts/tools/catala/compare.py --catala     # Catala against the references: 65/65
sh verify/ci/run_all.sh                                             # lawc + lawref on the same cases (family kz.corpus.vred_ts#catala-parity) and the full package regression
python3 corpus/laws/kz/vred-ts/tools/catala/compare.py --engines    # the same family separately, in a private profile snapshot
python3 corpus/laws/kz/vred-ts/tools/catala/compare.py --property 120 --seed 1   # random cases: the Python reference vs Catala vs lawc
python3 corpus/laws/kz/vred-ts/tools/catala/mutants.py              # 20 mutations, all must be killed
python3 corpus/laws/kz/vred-ts/tools/coverage_matrix.py --check     # the source coverage matrix is machine-consistent
```

None of these tools modifies the shared CLIR, locks, or registries: snapshots
are private (`work_profile.py --build-only --output`), and the Catala build
directory is temporary (`CLERK_BUILD_DIR`).

## Agreed comparison semantics

- **No conclusion.** Catala: `optional` output, `Absent` (the key is absent
  from the JSON response). Law DSL: `truth_status == NEITHER`; for quantities,
  `collected_count(0)`. The expectation in `cases.json` is `null`.
- **Established negation.** Catala: `Present content false`; Law DSL:
  `FALSE_ONLY`. Occurs for two conclusions: choice of appraisers (cl. 4-1) and
  admissibility of the inspection (cl. 7).
- **No input data.** Catala: an optional input is omitted (`Absent`); Law
  DSL: the fact is not submitted. Negative facts (`assert not …`) —
  `Present content false` for the inputs `ostatki_peredany`,
  `dokumenty_o_dtp`, `opredelyaetsya_stoimost_remonta`, `otchet_predostavlen`.
  Boolean inputs without negative rules (`podlezhit_zamene`, the seven
  conditions of cl. 7) — `false` ⇔ the fact is not submitted.
- **Money.** Whole-tenge amounts (KZT). Catala stores money to the nearest
  hundredth and rounds the product to the cent; Law DSL stores `Money`
  exactly and does not round (§50). At whole-tenge amounts, `80 %` of a sum is
  exactly representable in both (multiples of 0.2 tenge). At amounts with
  tiyn, the implementations DIVERGE by construction: the test
  `urn:query:vred-t15-j` (market value 1,000,000.01 ₸, expenses 800,000.01 ₸)
  fixes the exact Law DSL semantics (800,000.008 < 800,000.01 → not
  advisable), whereas Catala would round the threshold to 800,000.01 and give
  no conclusion. The comparison is therefore limited to whole-tenge amounts —
  the same requirement annex 3 cl. 2 imposes on the report's final amount.
- **Dates and working days.** Calendar dates; working days follow the external
  data of the 2026 official calendar snapshot
  (`corpus/clir/kz-official-2026.calendar.json`): Saturday and Sunday are
  non-working, holidays and shifted days off follow the snapshot's list. A
  term of N working days expires on the N-th working day after the day of the
  event (Civil Code of the Republic of Kazakhstan art. 173, 176; in Law DSL —
  §86 policy `start_count next_day, include_end true, roll
  next_working_day`, supplied by the case). If the day of the event or the
  target day is outside the snapshot's coverage — no conclusion (Catala
  `Absent`; Law DSL `NEITHER` with code `CALENDAR_OUT_OF_RANGE`).
- **Rounding to the tenge (annex 3 cl. 2).** The Rules do not name a rounding
  mode and none is chosen; only the absence of a fractional part is checked
  (Catala `round of s = s`, Law DSL `round(amount, 0, "HALF_UP") == amount`
  — at an integer value the result does not depend on the mode).

## What the comparison does NOT cover, and how it is checked

Deontic positions (ten duties and one liberty, statuses
SATISFIED/ACTIVE/VIOLATED, the maintenance duty of §124.2), the defeasible
layer with `unless` defeaters, established negations in the proof,
`whyNot` explanations, the set of documents under annexes 1–3, and the
"calculation under the Rules" chain — are not computational forms, and there
is no comparable model for them in Catala. They are checked by the Law DSL
loop: hand-written scenarios `tests/*.lawtest` under both evaluators, the
`vred_ts` regression under byte-level differential, and the `mutants.py`
mutations. This pilot is not proof of coverage of everything Catala can do,
or of the whole Law DSL language: exactly six computational areas are
compared, the ones listed in `vred_ts.catala_en`.
