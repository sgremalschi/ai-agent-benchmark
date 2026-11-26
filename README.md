# AI Coding Agent Benchmark

This repository presents 11 experiments in implementing, repairing, and reviewing Python software with AI coding agents. It contains 31 source snapshots and an evaluator covering 23 candidate entries.

The tasks range from small algorithms and caches to concurrent scheduling and transactional order processing. Independent tests expose defects that the agents' own tests miss and help assess what a subsequent review improves.

## Main finding

In experiment 018, Sol (`gpt-6.1-sol`) reviewed a scheduler written by Luna (`gpt-6-luna`). Luna then repaired the one independently verified finding: a scheduling race that allowed a newly inserted job into an already-running batch. The repair fixed that defect while leaving two interruption failures unresolved.

| Independent check | Original Luna | Original Sol | Repaired Luna |
|---|---:|---:|---:|
| Original acceptance suite | 18/18 | 18/18 | 18/18 |
| Supplementary interruption suite | 0/2 | 2/2 | 0/2 |
| Scheduling-race regression (R1) | 0/1 | 1/1 | 1/1 |

Review and repair added **68.43 seconds of agent execution**, bringing the collaborative total to **161.09 seconds**. This demonstrates a targeted improvement at a measured cost, with defects still unresolved. It does not establish that collaboration is generally faster, cheaper, or more reliable.

For a short technical review, inspect the [repair diff](results/018/phase23/repair.diff), [verification ledger](results/018/verification-ledger.json), and [final comparison](results/018/phase23/final-report.json).

## Experiments

| Experiment | Task | Available evidence |
|---|---|---|
| 008 | Merge intervals | Implementations and repository tests |
| 009 | TTL/LRU cache | Implementations and repository tests |
| 010 | Cache statistics | Implementations and repository tests |
| 011 | Bounded task queue | Implementations, repository tests, and recovered acceptance suite |
| 012 | Rate limiter repair | Recorded results and independent acceptance tests |
| 013 | Behavior-preserving order refactor | Recorded results and independent acceptance tests |
| 014 | Pair-counting optimization | Recorded results and independent acceptance tests |
| 015 | Concurrent job scheduler | Acceptance and supplementary interruption tests |
| 016 | Inventory reservation repair | Recorded results and independent acceptance tests |
| 017 | Multi-file order system | Recorded results and independent acceptance tests |
| 018 | Cross-model scheduler review and repair | Review finding, repair, and independent comparison |

Both models passed the recorded independent acceptance suites for 012–017. Luna's recorded agent time was lower in each pair. These single runs, in a fixed execution order, do not support a general speed ranking. The scheduler's supplementary failures also show why passing acceptance does not establish complete correctness.

## Run the evaluation

The evaluator makes no model calls and requires no AI credentials or original research repositories. Tests ran on **Python 3.14.7 on macOS**, using `uv`. Other platforms and Python versions remain untested.

From the repository root:

```sh
uv run --locked python tools/evaluate.py
```

To evaluate only experiment 018:

```sh
uv run --locked python tools/evaluate.py --experiment 018
```

Each run writes a new directory under `validation/`, containing a JSON report, Markdown summary, and JUnit XML. Checks run in separate processes against temporary candidate copies. The lockfile pins the test dependencies. `uv` may download Python or public packages if needed.

**Exit 0 means the results match the documented expectations, including known failures. It does not mean every test passed.** Exit 1 indicates an input-integrity mismatch, unexpected outcome (including changed test identities/counts), or a snapshot changed during execution. Invalid arguments and runtime or dependency failures are tool errors.

The [current reproduction results](validation/audit-corrections-2026-11-26/summary.md) cover all 23 candidate entries with zero unexpected outcomes. The [earlier full-test validation](validation/p1-2026-11-26/summary.md) used the pre-exclusion test set. The release omits identified example cases without established distribution permission, so repository-test counts differ. Historical implementations remain unchanged. [Post-audit corrections](provenance/AUDIT_CORRECTIONS.md) strengthen the 011 and 016 acceptance suites; earlier validation records retain their original test sets.

## How to interpret the evidence

Recorded experimental results, source reconstructed from commits, and fresh local validation are distinct evidence classes. Original prompts and structured measurements for 008–011 were unavailable; later passing tests do not recover that missing history. Both experiment 010 candidates began from Luna's 009 implementation.

The study is small and exploratory. Models ran in a fixed Luna-then-Sol order in 012–017. Test coverage differs between candidates, and acceptance suites are incomplete specifications. Do not count overlapping test cases as independent evidence. The results retain known inherited lint failures. The portable evaluator does not measure performance or monetary cost. A [separate reproducible scaling assessment](provenance/AUDIT_CORRECTIONS.md) compares experiment 014 implementations with the quadratic control.

[Methodology and limitations](METHODOLOGY.md) describe experimental controls, reviewer limitations, test portability, and the complete effort accounting. [Provenance](provenance/PUBLICATION.md) explains source identities, sanitization, and the distinction between original evidence and edited release copies.

## License

[MIT](LICENSE), copyright 2026 Stefan Gremalschi, applies to eligible independently created project material. See [license scope](LICENSE_SCOPE.md) for third-party exclusions and AI-assistance qualifications.
