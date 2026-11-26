# Source history and publication copies

The repository separates three kinds of evidence:

| Evidence | What it establishes |
|---|---|
| Recorded results in `results/` | What the original experiment records report, including failures and measured effort |
| Source in `snapshots/` | Implementations and agent tests exported from commits or frozen outputs |
| Dated runs in `validation/` | Fresh local checks of the retained code, not additional model experiments |

The [manifest](manifest.json) records all 31 snapshot lineages, source origins, and original/published hashes. Original prompts and structured measurements for 008–011 were unavailable. The recovered 011 acceptance suite supports fresh validation only.

## What changed for publication

Earlier publication work removed identifying hostnames, normalized machine paths, annotated agent claims, and omitted identified example tests without established distribution permission. Raw event logs, machine-specific setup records, and duplicate candidate archives are not included. [Release exclusions](RELEASE_EXCLUSIONS.json) and [derivative hashes](editorial-derivatives.json) retain those transformations. Source digests identify recorded bytes; they do not authenticate measurements or recover missing primary events.

The [technical corrections](AUDIT_CORRECTIONS.md) strengthen shared acceptance suites 011, 013, and 016 and protect the evaluator against altered inputs or test collections. Historical implementations, agent-written tests, and experimental measurements were not repaired in place. The original acceptance suites remain at publication commit `730653289bc64db44674f63c1bde9a6bcab31775`.

Final cleanup removes 31 empty snapshot READMEs and the 15-file duplicate repaired tree. The canonical repaired source is [snapshots/018/repaired-luna](../snapshots/018/repaired-luna/). Historical reports still name `results/018/phase23/repaired/`; resolve that prefix to the canonical directory. Those report strings and historical hash records are preserved. Snapshot `pyproject.toml` files still declare the omitted empty README: these directories are source evidence, not buildable package distributions.

The [transformation inventory](publication-transformations.json) records every removed previously published path, its digest, and any replacement. The manifest retains omitted empty-artifact origins and resolves duplicate artifacts to canonical bytes. The [166-file classification](technical-corrections-files.csv) distinguishes substantive changes from generated files in technical commit `7962df7b46711e54556ccd052192d1f6362d4a3a`.

## Which validation to read

| Retained run | Purpose |
|---|---|
| [Pre-exclusion](../validation/p1-2026-11-26/summary.md) | Preserves the larger repository test set before licensing exclusions |
| [Original release reproduction](../validation/editorial-2026-11-26/summary.md) | Preserves the release test set before acceptance corrections |
| [Baseline diagnostic](../validation/audit-baseline-check-2026-11-26/summary.md) | Retains the initial JUnit `classname` mismatch in compact report form |
| [Technical corrections](../validation/technical-closeout-2026-11-26/summary.md) | Full post-audit validation, regression evidence, and the relocated scaling measurement |
| [After cleanup](../validation/final-editorial-2026-11-26/summary.md) | Rechecks the final publication layout with unchanged evaluator expectations |

The redundant release generation and superseded intermediate correction run are removed. Their original bytes remain in the technical commit. The baseline diagnostic and final cleanup run retain JSON reports and summaries; duplicate JUnit output is omitted. Distinct test sets and original experimental results are retained.

The twelve diff captures under `results/012/`–`results/017/` omit a final newline. Their bytes are unchanged; they are not directly applicable with Git as stored.

## Check the publication

Before generating new local validation output:

```sh
uv run --locked python tools/check_publication.py
```

The checker validates local Markdown link targets, snapshot lineages, exclusions, historical artifact digests, and the [current file inventory](p1-publication-checksums.json). It also scans selected privacy patterns. The inventory excludes itself and the changing [check report](p1-publication-checks.json); added local output files count as inventory changes.

After reviewing intentional publication edits, maintainers can refresh and recheck:

```sh
uv run --locked python tools/check_publication.py --refresh-checksums
uv run --locked python tools/check_publication.py
```

Refreshing cannot bypass historical artifact mismatches. These checks do not establish complete privacy review, legal clearance, or correctness beyond the executed tests. See [authorship and third-party material](RIGHTS_REVIEW.md) and [license scope](../LICENSE_SCOPE.md) for reuse terms.
