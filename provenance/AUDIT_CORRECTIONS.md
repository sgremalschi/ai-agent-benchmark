# Stronger validation after the audit

The audit of publication commit `730653289bc64db44674f63c1bde9a6bcab31775` exposed gaps in acceptance coverage and the evaluator. Technical commit `7962df7b46711e54556ccd052192d1f6362d4a3a` addresses them. These are changes to validation, not new model experiments or repairs to historical implementations. [Publication history](PUBLICATION.md) explains the later removal of empty and duplicate artifacts.

## Input integrity and test preservation

Before running candidate code, the evaluator verifies the current publication hashes for snapshots, acceptance suites, fixtures, task inputs, tools, dependency metadata, the independent R1 test, and the expected test baseline. Generated validation directories are outputs, outside this input boundary. The inventory is a reviewed local trust anchor, not an external signature.

The [expected test identities](expected-test-cases.json) come from the original release reproduction, updated for the eight additional inventory cases under the evaluator configuration. Sorted JUnit class/name pairs preserve counts, including repeated identities. Missing suites or changed collections cause an unexpected outcome even when every collected test passes. The evaluator never refreshes the inventory or baseline automatically.

An initial run exposed a JUnit `classname` difference between standalone pytest and the evaluator configuration. Its [diagnostic report](../validation/audit-baseline-check-2026-11-26/report.json) remains available; the corrected baseline passes subsequent validation.

The [regression probes](../tools/test_evaluate.py) exercise a missing acceptance suite, a modified implementation, smoke-test substitution, and environment-driven deselection through `PYTEST_ADDOPTS`. Smoke tests fail collection preservation even after deliberate checksum resealing.

## Acceptance coverage

| Experiment | Added validation |
|---|---|
| 011: bounded queue | Observe entry into Python's `Condition.wait` while its lock is held, so controller actions cannot overtake entry into the wait |
| 013: order refactor | Recursively compare exact output types before values; mutation probes reject an integer replaced by an equal-valued float or boolean |
| 016: inventory | Reject fractional and boolean quantities; verify stock, existing reservations, and reservation-ID reuse after rejection |

The queue instrumentation assumes implementations use Python's `Condition` primitive. Bounded fallback waits let notification-failure probes terminate. The refactor still uses the legacy baseline as its oracle, preserving legacy behavior rather than redefining it. Its 30 golden cases and test identities are unchanged. Inventory acceptance grows from 22 to 30 cases per candidate.

The [technical validation](../validation/technical-closeout-2026-11-26/summary.md) reproduces all 23 candidate entries with zero unexpected outcomes. Its [regression record](../validation/technical-closeout-2026-11-26/technical-checks.json) also records the comparison of 656 historical files before publication cleanup. Original shared acceptance suites remain in the publication commit, with their pre-audit hashes in the manifest. Original agent tests and experimental measurements remain distinct from these stronger checks.

## Separate experiment 014 scaling assessment

```sh
uv run --locked python tools/assess_scaling_014.py
```

The script makes no model calls and prints JSON. It measures five repetitions at each of four doubling input sizes for both implementations and the quadratic fixture. Unique integers with target `n-1` yield exactly `n/2` pairs.

Median doubling ratios near 2 support linear scaling for this input family. Ratios near 4 resemble the quadratic control and call the optimization claim into question. Inconsistent ratios are inconclusive: rerun on an idle machine and inspect larger sizes. This finite check cannot prove asymptotic complexity or cover every input family. No absolute timing threshold is a correctness gate. The [retained measurement](../validation/technical-closeout-2026-11-26/scaling-014.json) shows ratios near 2 for both candidates and near 4 for the control.

## What survives of the historical control recipe

The retained records support this sequence: create a history-free copy of Luna 015 for Sol review against the scheduler specification; verify R1 independently; supply only that finding to one fresh Luna repair session; freeze the output; evaluate original Luna, original Sol, and repaired Luna. See the [methodology](../METHODOLOGY.md) and [isolation probes](../results/018/isolation-probes.json) for observed controls. This reconstructs the procedure, not an executable copy of the original harness.

The [review record](../results/018/review.execution.json) and [repair record](../results/018/phase23/repair.execution.json) expose timestamps, elapsed seconds, return codes, and usage arrays. Timestamps agree with the rounded stage durations. Cumulative effort combines implementation, review, and repair measurements. Cached input is part of input; reasoning output is part of output. Setup and independent verification are separate categories.

Primary event logs and machine setup records are unavailable publicly. The exact event parsing and timing-clock implementation cannot be recovered from these derivatives. Token counts remain recorded measurements whose extraction cannot be independently authenticated from published primary events.
