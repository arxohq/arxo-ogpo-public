# arxo-ogpo-public

This repository is a published snapshot of the executable canon for compulsory
motor third-party-liability insurance in Kazakhstan. It contains source text
with provenance, models, pinned dependencies, and scenarios for the nine
packages recorded in `CANON-MANIFEST.json`.

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

The model and scenarios are Apache-2.0. Pinned legal texts remain subject to
their publishers' terms; `NOTICE` identifies the source and reproduction terms
for each package. This repository is not an official publication of a state
authority.

The supported standalone check is the pinned package build above. Supplemental
research tools retained under package directories may require the original
development environment; they are not invoked by public CI. Internal change
dossiers and their package README summaries are excluded from this release.
