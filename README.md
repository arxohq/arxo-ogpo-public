# arxo-ogpo-public

This repository is a published snapshot of the executable canon for compulsory
motor third-party-liability insurance in Kazakhstan. It contains source text
with provenance, models, pinned dependencies, and scenarios for the nine
packages recorded in `CANON-MANIFEST.json`.

## What you can ask

A package answers questions about a case. Its **question catalog** lists every
question the package supports:

- `packages/<package>/QUESTIONS.md` is the readable catalog, grouped by the
  article of the act;
- `packages/<package>/analysis/questions.json` holds the same catalog in
  machine-readable form (`id`, question, kind, typed parameters, query
  template, rules that can answer it, source articles, tests).

Every card is backed by at least one executed scenario, and the catalog also
lists what the package does *not* answer, with the reason. A card says that a
question is supported and tested. The answer for a particular case comes only
from an evaluation with its proof.

| Package | Catalog |
| --- | --- |
| `kz.corpus.ogpovts` — Law No. 446-II on compulsory OGPO insurance | [QUESTIONS.md](packages/kz.corpus.ogpovts/QUESTIONS.md) |
| `kz.corpus.vred_ts` — Rules for determining damage to a vehicle (National Bank Board resolution No. 14 of 28.01.2016) | [QUESTIONS.md](packages/kz.corpus.vred_ts/QUESTIONS.md) |
| `kz.corpus.bonus_malus` — Rules for the bonus-malus coefficient (National Bank Board resolution No. 140) | [QUESTIONS.md](packages/kz.corpus.bonus_malus/QUESTIONS.md) |
| `kz.corpus.budget_code` — Budget Code of the Republic of Kazakhstan (No. 171-VIII) | [QUESTIONS.md](packages/kz.corpus.budget_code/QUESTIONS.md) |

The remaining packages (`kz.corpus.budget`, `kz.corpus.popravochnye_koeffitsienty`,
`vocab.*`) supply values and vocabularies to the ones above; their scope is in
each `package-info.json` and README.

Question text, rule names and legal terms stay in Russian, the language of the
act.

## Asking a question

Questions are asked against a **case package**: a small package that imports
the canon, declares the facts of one or more cases, and pins every dependency
in `law.lock`. `packages/kz.corpus.vred_ts/examples/gibel-i-detali` is one;
its README describes each case.

The pinned evaluator is `law-cli` from `toolchain.lock.json`
(`x86_64-unknown-linux-musl`). Downloading it needs the GitHub CLI:

```sh
tools=$(mktemp -d)/law-tools
python3 tools/toolchain.py download --lock toolchain.lock.json --out "$tools"
```

Is the vehicle considered destroyed? (catalog card `unichtozheno`, `truth`):

```sh
"$tools/law-cli" ask packages/kz.corpus.vred_ts/examples/gibel-i-detali --case Gibel --query-json packages/kz.corpus.vred_ts/examples/gibel-i-detali/queries/unichtozheno.json
```

The answer is `TRUE_ONLY`: repair costs 90% of the market value, so the rule
`EkonomicheskayaNetselesoobraznost` applies.

What is the insurance payment? (card `vyplata-pri-gibeli`, `collect`):

```sh
"$tools/law-cli" ask packages/kz.corpus.vred_ts/examples/gibel-i-detali --case Gibel --query 'evaluate collect amount: Money where kz.corpus.vred_ts::strakhovaya_vyplata_pri_gibeli(r: raschet, amount: amount);' --query-id vyplata
```

The answer is 850,000 KZT: the market value less the salvage, rule
`VyplataZaMinusomGodnykhOstatkov`.

Why is no payment derived? (card `pochemu-ne-vyplata`, `why_not`):

```sh
"$tools/law-cli" ask packages/kz.corpus.vred_ts/examples/gibel-i-detali --case Molchanie --query-json packages/kz.corpus.vred_ts/examples/gibel-i-detali/queries/pochemu-ne-vyplata.json
```

The answer is `NEITHER` with the blocking premises. The vehicle is destroyed,
but the case says nothing about whether the salvage was transferred to the
insurer. Silence is not treated as a denial, so neither payment rule applies.

Each command prints an evaluation document as JSON: `results` holds the answer
(`truthStatus` or `value`), `proofGraph` shows the rules applied and the source
text they are anchored to, and `issues` lists any problems. Add `--out <dir>`
to save the request and result. The saved evaluation can be replayed with
`"$tools/law-cli" eval <dir>`.

To ask about your own case, add a `case` block under `cases/` of a case
package and register it under `[[cases]]` in that package's `law.toml`. The
query template for each question is on its catalog card.

Public CI runs all three commands above and checks their answers
(`tools/usage_examples.py`).

## Verifying a release

The manifest is the release inventory. Verify a release artifact or a Git
archive rather than a working checkout, because the verifier rejects `.git`:

```sh
snapshot=$(mktemp -d)
git archive --format=tar HEAD | tar -x -C "$snapshot"
python3 tools/canon_publication.py verify --artifact "$snapshot"
```

The public CI also downloads the SHA-256-pinned toolchain, builds every
declared package offline, runs its scenarios, replays saved evaluations, and
rebuilds the package release. The public release is a snapshot: changes are
developed and reviewed before a new immutable manifest is published.

## License

The model and scenarios are Apache-2.0. Pinned legal texts remain subject to
their publishers' terms; `NOTICE` identifies the source and reproduction terms
for each package. This repository is not an official publication of a state
authority.

The supported standalone check is the pinned package build above. Supplemental
research tools retained under package directories may require the original
development environment; they are not invoked by public CI. Internal change
dossiers and their package README summaries are excluded from this release.
