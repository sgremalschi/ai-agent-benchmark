# Corrections following the publication audit

These changes follow the audit of publication commit 730653289bc64db44674f63c1bde9a6bcab31775. Historical snapshots, agent tests, results and earlier validation generations remain unchanged. Optional removal and consolidation of publication artifacts are deferred.

The portable evaluator now verifies evaluation input hashes against the current publication inventory before execution. It covers snapshots, acceptance suites, fixtures, task inputs, tools, dependency metadata, the independent R1 test and the expected test identity baseline. Fresh validation directories are outputs, not inputs. The inventory is a reviewed local trust anchor, not a cryptographic signature or proof of historical truth.

The expected identities in expected-test-cases.json were derived from the editorial validation JUnit records, with experiment 016 acceptance identities updated from fresh execution of the eight added type cases under the evaluator configuration. An initial baseline check exposed a JUnit classname difference from standalone pytest; that check is retained under validation/audit-baseline-check-2026-11-26. Sorted classname/name pairs preserve counts, including repeated identities. A collection mismatch is an unexpected outcome even when every collected test passes. Updating this baseline or the inventory requires deliberate review; the evaluator never refreshes either automatically.

Experiment 016 adds fractional and boolean stock/reservation quantities, checking existing stock and reservation state after rejection and subsequent ID reuse. Experiment 011 instruments the standard Condition.wait boundary while the condition lock is held, eliminating the pre-operation event race. This instrumentation assumes implementations use Python's Condition primitive; it does not inspect queue fields. Bounded fallback waits allow failed-notification probes to terminate.

## Separate experiment 014 scaling assessment

Run from the repository root:

```sh
uv run --locked python tools/assess_scaling_014.py
```

This runs no agents and writes JSON to stdout. It measures five repetitions at each of four doubling input sizes for each preserved implementation and the quadratic fixture. Unique integers with target n-1 yield exactly n/2 pairs. Median timings and doubling ratios permit comparison on the same machine: ratios near 2 support linear scaling for this family; ratios near 4 resemble the quadratic control. Persistent ratios resembling the control call the optimization claim into question. Noisy or inconsistent ratios are inconclusive; rerun on an idle machine and examine larger sizes. This finite empirical check cannot prove asymptotic complexity or cover every input family. No absolute timing threshold is a correctness gate.

## Historical control and measurement reconstruction

The surviving structured records support this partial recipe: create a history-free copy of Luna 015 for Sol review against the original scheduler specification; verify R1 independently; supply only the verified finding to one fresh Luna repair session; freeze its output; evaluate original Luna, original Sol and repaired Luna separately. See METHODOLOGY.md and results/018/isolation-probes.json for observed controls and limitations. This is a reconstruction from retained records, not an executable copy of the historical harness.

The retained review.execution.json and phase23/repair.execution.json expose started_utc, ended_utc, seconds, returncode and usage arrays. The timestamps are consistent with the rounded recorded stage durations. The cumulative effort record combines implementation, review and repair stage measurements; cached input is included in input, and reasoning output is included in output. Setup and independent verification intervals are separate categories. Original primary event logs and machine setup records are unavailable publicly. The exact historical event parsing and timing-clock implementation cannot be recovered from these derivatives; no replacement parser is presented as original. Token counts remain recorded measurements whose extraction cannot be independently authenticated from the published primary events.


## Technical closeout checks

Experiment 013 now recursively checks exact output types before comparing values against the legacy golden results, including nested dictionary/list contents. Mutation probes replace an integer quantity with an equal-valued float or boolean and require rejection. The 30 golden cases and their test identities remain unchanged.

The evaluator also requires suites named by the expected identity baseline, independently of filesystem discovery. Regression probes cover a missing acceptance suite, modified implementation input, smoke-test replacement before and after checksum resealing, and deselection through PYTEST_ADDOPTS. Environment-driven deselection is rejected as a collection mismatch rather than silently accepted.

All tracked paths under snapshots/, results/ and the three pre-audit validation generations are compared byte-for-byte with publication commit 730653289bc64db44674f63c1bde9a6bcab31775 during closeout. Shared acceptance suites 011, 013 and 016 are intentionally strengthened; their original versions remain in that commit and their pre-audit hashes remain in the provenance manifest. These revised acceptance suites are not historical agent-written tests. New validation has evidence_class newly_executed_publication_validation and is stored in separate directories. No historical execution measurements are regenerated.
