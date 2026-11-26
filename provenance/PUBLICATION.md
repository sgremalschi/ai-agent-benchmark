# Source provenance and release transformations

This repository distinguishes three evidence classes:

| Evidence | Interpretation |
|---|---|
| Recorded results | Measurements captured during the original coding experiments |
| Reconstructed source | Code and tests exported from existing commits, without inferring missing runs |
| Fresh validation | Dated evaluation of retained implementations using the supplied tools |

The [manifest](manifest.json) records experiment identities, all 31 snapshot lineages, original commits or frozen-source origins, source hashes and release hashes. Experiments 008–011 lack original prompts and structured historical measurements. The 011 acceptance source was recovered separately; later validation does not establish its original outcome.

## Original evidence and derivatives

Implementations, fixtures and independent suites are unchanged by editorial cleanup. Original-source hashes describe the source evidence; release hashes describe the files here. Where copies were already sanitized before editorial cleanup, their intermediate hashes are retained. Edited historical records are explicitly marked with a source hash and description of the changes. Exact originals are retained separately.

Release transformations include omission of identified example tests without established distribution permission, removal of identifying JUnit hostnames, normalization of machine-specific references, and annotations separating agent claims from independent findings. Original test counts still describe the original test sets. The [exclusion and transformation ledger](RELEASE_EXCLUSIONS.json) records test omissions and earlier sanitization; the [editorial derivative inventory](editorial-derivatives.json) identifies edited evidence.

The twelve diff captures under `results/012/`–`results/017/` omit a final newline. They retain their original bytes and are not directly applicable with Git as stored. Structural validation supplies a terminal newline to parser input in memory only; it does not modify the files or establish applicability to every release snapshot.

Raw logs, duplicate candidate archives, machine-specific launch/setup records and incidental development records are not included. Their omission does not remove scientific findings: known failures, cross-candidate test results, model/settings identities, measured effort and methodological limitations remain in the public records and [methodology](../METHODOLOGY.md).

## Validation

The [pre-exclusion validation](../validation/p1-2026-11-26/summary.md), [release validation](../validation/release-2026-11-26/summary.md) and [current reproduction](../validation/editorial-2026-11-26/summary.md) identify their dates and test sets. The latter two use the same candidate code and tests. These are local reproductions, not additional model experiments.

Run file-integrity and local-link checks with:

```sh
uv run --locked python tools/check_publication.py
```

After intentional edits, update the current checksum inventory and confirm it:

```sh
uv run --locked python tools/check_publication.py --refresh-checksums
uv run --locked python tools/check_publication.py
```

The [current inventory](p1-publication-checksums.json) excludes itself and the changing [integrity report](p1-publication-checks.json). Historical artifact hashes are checked before a refresh is permitted. The checker also validates the snapshot lineage inventory and absence of excluded example files. It does not certify editorial quality or prove the absence of every sensitive detail.

See [authorship and third-party material](RIGHTS_REVIEW.md) and [license scope](../LICENSE_SCOPE.md) for reuse terms.
