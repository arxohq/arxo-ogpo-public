# Report: kz.corpus.vred_ts — content completeness and comparison with Catala (09.09.2026)

Source: Resolution of the Board of the National Bank of the Republic of
Kazakhstan No. 14 of 28.01.2016, "Rules for Determining the Amount of Damage
Caused to a Vehicle," pinned copy `sources/vred-ts/ru.txt` (sha256
`6840c4a9…07c0`, matches the `content_hash` of the publication
`VRED_TS_RU_TEXT`; 19 fragments, 13 clauses, three annexes, a title, and two
chapters; `check_source_pinning` — 0 violations).

## 1. What is implemented

The "source unit → requirement → implementation → scenarios → reference →
status" matrix is [`COVERAGE-MATRIX.md`](../../COVERAGE-MATRIX.md) (45 rows,
machine-checked by `tools/coverage_matrix.py --check`: quotes are substrings
of the pinned text, the names of 67 rules, 157 test titles, and 65 cases all
exist, and completeness holds in both directions). Summary by status:

| status | rows | what |
|---|---|---|
| executed by rules | 39 | cl. 2–4, 4-1, 6–11 (except cl. 7 part 4), annexes 1–3 down to sub-clauses and elements |
| case fact (delegation by the Rules) | 1 | annex 3 cl. 1 sub-cl. 2 — the "depreciation wear calculation" section (the Rules contain no formulas: cl. 2 specialized software, cl. 11 internet resource) |
| boundary with a cause | 3 | cl. 1 (subject matter), cl. 3 part 1 (inspection deadlines — cl. 3 art. 22 of the Law), cl. 5 (art. 29-1 of the Law) |
| description without a consequence | 2 | cl. 7 part 4 (photo materials as an additional source), headings |

Content gaps closed in this work (the green tests of 01.09 did not see
them): annex 2 down to sub-clauses (14) with the proviso "photo of the
odometer (if available)"; annex 3 down to elements (15) with "seal (if
available)"; the check for "a figure rounded to the tenge" with no mode
chosen (`round(amount, 0, "HALF_UP") == amount` — at an integer value the
mode does not matter, §50 is respected); the additional inspection of cl. 2
part 4 with three norms (own application, own report, adjustment); the
insurer's duty to submit a report (cl. 3 part 2, a window up to the part 6
limit; under simplified processing — no deadline); the condition on a part
under cl. 10 with two facts; the positions of cl. 2, 4-1, and the §124.2
maintenance duty covered by scenarios; the adjustment for hidden defects —
four scenarios (the rule previously had none).

External factual data is kept separate from the normative calculations: the
2026 calendar — a snapshot `corpus/clir/kz-official-2026.calendar.json` (Law
DSL — §85 pinned per DECISION-0175, Catala — a `Kalendar` structure supplied
as input); the term-computation policy §86 — supplied by the case (Civil Code
of the Republic of Kazakhstan art. 173, 176); the amount of wear and the
part's value net of wear — the result of an external tool (cl. 2 specialized
software, cl. 11 internet resource) supplied as case facts.

## 2. What confirms completeness

- **A full read-through** of the source against the model — the matrix above;
  every row quotes the source and names the rules, tests, and reference
  cases.
- **Positive and negative scenarios** for every condition and exception; for
  numeric and time boundaries — below, at, and above: 80 % (799,999 /
  800,000 / 800,001 at 1,000,000), 15,000 and 20,000 km (±1), two appraisers
  (0/1/2/5), the report on the last day of the term and one day later, the
  inspection day at the limit and after it, calendar boundaries (shifted days
  8–9 March, Nauryz 21–25 March, 7–11 May, 25–26 October, 1 January, end of
  coverage 31 December, outside coverage 2027-01-05 and 2025-12-31).
- **Incomplete and contradictory inputs** (`tests/15-…`, `16-…`, `14-…`):
  silence ≠ negation (§113), a contradiction produces BOTH and suppresses the
  conclusion (§62, §66), a mismatched mileage unit — TYPE_ERROR (E-0068), no
  policy — MISSING_POLICY, no snapshot in the world — MISSING_INPUT (E-0105),
  outside coverage — CALENDAR_OUT_OF_RANGE, money with tiyn — exact
  arithmetic per §50.
- **Mutations** `tools/catala/mutants.py`: 20 targeted losses (the 80 %
  boundary, the 70 % threshold, deduction of salvage, established negation,
  the 15,000 and 20,000 km boundaries, warranty, repair, 5 → 6 working days,
  working → calendar days, the cl. 3-1 defeater, `>` → `>=` at the limit,
  a single appraiser, the annex 3 footnote, the rounding check, VIN, the
  application for an additional inspection, established absence of
  documents, photography, the seal) — **20/20 killed**, none rejected by the
  compiler.
- **Explanation of results**: the scenarios pin the applied rules
  (`applied`/`any_applied`) and the §175 statuses with issue codes.

## 3. Independent comparison with Catala

The model `vred_ts.catala_en` (Catala 1.2.0, installed via opam) is derived
from the text: six areas — total loss (cl. 9), part value (cl. 10 +
footnote), choice of appraisers (cl. 4-1), admissibility of the inspection
(cl. 7), deadlines (cl. 3, 3-1), the final amount (annex 3 cl. 2). The agreed
semantics of money, dates, missing data, and negations is in `README.md`. The
expectations for the 65 cases in `cases.json` were established manually from
the text and the calendar, with rationale; the same cases are generated into
`tests/parity/*.lawtest` (family `kz.corpus.vred_ts#catala-parity`) and run
under both Law DSL evaluators.

| loop | result |
|---|---|
| `compare.py --catala` | 65/65 Catala cases matched the references |
| profile `sh verify/ci/run_all.sh` | 157 `.lawtest` (including 65 parity) under both evaluators — PASS; `vred_ts` regression 33/33; 35 calculations byte-identical liblaw_ffi == lawref |
| `compare.py --property 120 --seed 1` | 240 random cases (seed 1 and seed 2, 120 each; total loss, part value, choice of appraisers, deadlines on the 2026 calendar): Python reference ↔ Catala 240/240, Python reference ↔ lawc 240/240 |
| `mutants.py` | 20/20 killed |

Discrepancies between the implementations on the 65 reference and the random
cases — **zero**. The only known semantic difference is built in on purpose
and pinned by the test `urn:query:vred-t15-j`: Catala rounds `money *
decimal` to the nearest hundredth, Law DSL computes exactly (§50), so the
comparison is limited to whole-tenge amounts (annex 3 cl. 2 requires the same
of the final amount).

Forms outside Catala's comparable computational model — deontic positions
(ten duties, one liberty, the §124.2 maintenance duty), the defeasible layer
with `unless`, established negations in the proof, the set of documents
under the annexes — are checked by the Law DSL loop (scenarios under both
evaluators, byte-level differential, mutations). The pilot does not claim to
cover everything Catala can do, or all of Law DSL.

## 4. Qualification of discrepancies

| № | observation | qualification | action |
|---|---|---|---|
| 1 | The test expected MISSING_INPUT with no `calendar` axis in the context, both implementations answered TRUE_ONLY | defect in the test reference: §89 — the sole snapshot node in the world is selected automatically | the test was moved to a world without the calendar package (`16-srok-bez-kalendarya.lawtest`) |
| 2 | The test expected RUNTIME_ERROR on CALENDAR_OUT_OF_RANGE (the E-0105 list), both implementations — MISSING_INPUT, byte-identical | a gap in the prose SPEC (the MISSING_INPUT list does not name CALENDAR_OUT_OF_RANGE; the implementations read it as "no snapshot submitted for the date") — **SPEC-1**, pending owner errata | the test pins the issue code and NEITHER, does not pin the status; the implementations were not adjusted to match |
| 3 | Contradictory facts about the transfer of salvage: two amounts were expected, zero was obtained | defect in the test reference: a bare body premise is read as `established` (§66); under BOTH the rule does not apply | the expectation was corrected per the prose |
| 4 | Catala: `money * 80%` rounds on an amount with tiyn, Law DSL does not | a difference in language semantics, not a defect | the comparison scope is whole-tenge amounts; Law DSL is pinned by t15-j |

No defects were found in lawc, lawref, or the Catala model; the core was not changed.

## 4a. Performance (measured 09.09.2026, Apple Silicon, warm runs)

These numbers do not compare "languages in general": the three
implementations produce a different product for one call. Catala returns a
VALUE; Law DSL returns a canonical evaluation document (`manifest`,
`results`, `proofGraph`, `positions`, `conflicts`, `issues`, `resultHash`),
and it is exactly this document that is compared byte-for-byte between the
two engines.

| measurement | Catala 1.2.0 (interpreter) | lawc (Rust, gate profile) | lawref (Python oracle) |
|---|---|---|---|
| one in-process calculation | ~16 µs (10,000 calls of the `Gibel` scope in 0.16 s above baseline) | 0.4–0.5 ms per `evaluate` (before the 09.09.2026 runner fix, a case with an inline §86 policy cost 6.5 ms) | ~2.5 ms per `evaluate` |
| process start and model load | ~40 ms (`clerk run`, `_build` inside the project) | ~10 ms (a bound world of 274 nodes, 292 KB) | ~0.3 s (interpreter and `.lawtest` lowering) |
| the whole comparison set | 5.8 s in one process, `compare.py --catala` (including a one-time stdlib build) | 0.07 s (`parity`, 48 cases / 118 `evaluate`) and 0.67 s (`parity-sroki`, 17 cases / 101 `evaluate`) | 0.86 s for the whole family |

**Correction to the first edition of this section.** The earlier "3.4 ms with
a deadline" figure was measured incorrectly: the program was the bare
package CLIR, which has no `calendar_snapshot` node, all 17 cases failed with
code `MISSING_CALENDAR`, and what was measured was the cost of the failure.
On the bound world (package plus calendar), the same cases pass 17 of 17 and
cost 6.5 ms per call.

### Where the 6.5 ms comes from

Breakdown on synthetic sets of 500 `evaluate` calls in one test, the same
world throughout:

| variant | per call |
|---|---|
| a question with no deadline, no inline policy | 0.38 ms |
| the same question, but the case declares `deadline_policy` in the context | 6.4 ms |
| a question with a calendar-based deadline under the same policy | 6.4 ms |

The surcharge was tied neither to date arithmetic nor to reading the
snapshot: a question that did not ask about a deadline at all paid exactly as
much. The cause lay in the runner (`law-cli/src/lawtest.rs`):
`pin_deadline_policies` cloned the entire world document on EVERY step to
append the policy node, and `Program::evaluate`, on a pointer mismatch
(`!std::ptr::eq(request.ir, &self.document)`), bypassed the prepared cache
and rebuilt `prepare_program`, `World`, `ViewCache`, and the identity hashes
from scratch; alongside this, `calendar_resource` walked back up the
directories and re-checked the calendar dataset against `datasetHash` on
every step.

**Fixed on 09.09.2026.** The calendar resource and the world with pinned
policies are now computed once PER TEST (both are functions of the
"program and case" pair, and a test has one case), and the pinned world
lives in a separate `Program` with its own preparation cache, reused by
every test in the file that shares the same policy. Comparison of the
binaries before and after, by CPU time on a loaded machine:

| set | before | after | speedup |
|---|---|---|---|
| `parity` (48 cases, 118 `evaluate`, no policy) | 0.18 s | 0.17 s | 1.1× |
| `parity-sroki` (17 cases, 101 `evaluate`, policy) | 1.62 s | 0.17 s | 9.5× |
| synthetic: 500 `evaluate` with no policy | 0.59 s | 0.55 s | 1.1× |
| synthetic: 500 `evaluate` with a policy | 7.73 s | 0.56 s | 13.8× |
| synthetic: 500 `evaluate` with a deadline | 7.92 s | 0.58 s | 13.7× |

The fix is transport-only: the bytes of the evaluation documents do not move.
Confirmed by — 114 crate tests (including a new equivalence test, "prepared
pinned world vs. execution with no cache," on canonical bytes), 1200
conformance vectors, 656 byte-level checks of `lawc eval == golden == live
lawref`, and eight package sets whose reports from the old and new binary
matched byte-for-byte (124 scenarios, including every case with a policy).

### Profile of the baseline 0.38 ms

`sample` over 20,000 calls, shares of self time: string comparison
(`memcmp`) 23 %, `BTreeMap::get`/`insert` 11 %, the allocator
(`malloc`/`free`) 26 %, `memmove`/`memset` 5 %, system calls
`open`/`stat`/`read` 4.5 %, `sha2` 2 %, `law_canon` canonicalization 2 %. The
solver (`solve_rec`) — 0.8 %. Conclusion: the baseline cost of a call does
not go into legal inference but into working with `serde_json::Value` as the
execution model, i.e., into string-key lookups and allocation.

## 5. Boundaries and open questions

Boundaries 1–8 are in `STATUS.md`. Questions for the owner (a reading has
been adopted and pinned by tests; the point is not considered closed):

- **Q1.** Clause 3-1 speaks of the deadlines for "the insurer's carrying out
  of the inspection and drawing up of the inspection report, and determining
  the amount of damage, as referred to in clause 3." The victim's marking
  deadline (three working days) is not a deadline "of the insurer's
  carrying out." Adopted: under simplified processing, all three deadlines of
  cl. 3 are lifted (KZ-VRED-20, t11-d, S09). Alternative: lift only the
  insurer's deadlines (response and report) — in which case the victim would
  retain the three-day marking deadline even under simplified processing.
- **Q2.** Who chooses the payment alternative under cl. 9 part 2 (transfer of
  salvage ↔ deduction of the value of usable salvage)? Adopted: it is
  determined by the established fact of transfer or by its established
  negation; silence means the payment is undetermined.
- **Q3.** No lower bound is named for the payment "net of the value of
  usable salvage": when the salvage is worth more than the market value, the
  formula yields a negative amount (case G14: 100,000 − 150,000 = −50,000).
  Zero is not implied.
- **SPEC-1.** See qualification 2.

What was intentionally not done: the shared CLIR
`corpus/clir/kz-vred-ts.lawir.json`, the lock, and the registry ratchets were
not rebuilt (DECISION-0184: the profile builds private snapshots, the OGPO VTS
consumer is frozen); the `check_label_coverage` row holds the previous shared
CLIR numbers (dictionary 125/0, norms 66/0) pending an authorized rebuild.

## 6. Artifacts and reproduction

| artifact | path |
|---|---|
| coverage matrix | `corpus/laws/kz/vred-ts/COVERAGE-MATRIX.md`, `analysis/coverage-matrix.json`, `tools/coverage_matrix.py` |
| Catala model and instructions | `tools/catala/vred_ts.catala_en`, `tools/catala/README.md` |
| references and runner | `tools/catala/cases.json`, `tools/catala/compare.py`, generated `tests/parity/*.lawtest` |
| mutations | `tools/catala/mutants.py` |
| scenarios | `tests/01…17-*.lawtest`, `tests/vred-ts*.lawtest` (`law.toml`, three families) |
| this report | `tools/catala/REPORT.md` |

Commands are in `tools/catala/README.md`; the normal verification entry point
is `sh verify/ci/run_all.sh`.
