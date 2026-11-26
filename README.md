# What Passing Tests Missed: Reviewing and Repairing AI-Written Code

Both agents' job schedulers passed all 18 independent acceptance tests. Subsequent review and independent testing uncovered a scheduling race and an interruption cleanup defect in Luna's implementation. A focused repair fixed the race; both supplementary interruption checks still failed.

This repository preserves that case alongside ten other Python coding experiments with AI agents. It includes task inputs where available, source snapshots, agent-written tests, independent checks, and recorded results. Software engineers can use it to study how a passing test suite, a plausible review, and a successful repair each leave different questions unanswered.

A second coding agent can uncover defects the first one missed, but neither agent replaces independent verification.

## Three minutes: The finding and the lesson

In experiment 018, Sol (`gpt-6.1-sol`) reviewed Luna's (`gpt-6-luna`) scheduler from experiment 015. Only the independently verified finding was supplied to one fresh Luna repair session. Its output was then frozen and evaluated.

| Independent check | Original Luna | Original Sol | Repaired Luna |
|---|---:|---:|---:|
| Original acceptance suite | 18/18 | 18/18 | 18/18 |
| Scheduling-race regression (R1) | 0/1 | 1/1 | 1/1 |
| Supplementary interruption checks | 0/2 | 2/2 | 0/2 |

These are the [recorded experiment 018 outcomes](results/018/phase23/final-report.json), also reproduced by the local evaluator. The interruption checks cover `KeyboardInterrupt` and `SystemExit`: two cases exposing the same cleanup defect. They supplement the original task requirements.

Review and repair added **68.43 seconds of recorded agent execution** (+73.85%), bringing the implementation/review/repair total to **161.09 seconds**. Setup and evaluation took additional time; active human effort was not measured. See the [effort breakdown](METHODOLOGY.md). This is one successful targeted repair, with unresolved failures, rather than evidence of a general model ranking.

### How the race works

`run_due()` chooses a batch of jobs, then runs their callbacks. Jobs inserted after the batch boundary should wait for the next invocation, even if their scheduled time has already arrived.

The [original Luna implementation](snapshots/015/luna/problems/job_scheduler.py) reads the injected clock before capturing that boundary. If the clock pauses while another thread inserts a job, the new job can enter the current batch. The [repair](results/018/phase23/repair.diff) captures the insertion sequence under a short lock before reading the clock. The new job then waits for the next invocation. The API and existing scan/sort approach stay the same.

A separate problem remains: Luna reserves the whole batch before running callbacks. If a callback raises `KeyboardInterrupt` or `SystemExit`, execution escapes the loop and leaves jobs that have not run reserved. Later invocations select only pending jobs, so those jobs are stranded. The review missed this defect, and the targeted repair leaves it visible.

### Lessons to apply

- Test specific sequences of thread actions. A worker announcing that it started does not prove it reached a blocking wait.
- Reproduce a review finding before supplying repair feedback. Keep the regression focused on behavior so it permits alternative locking designs.
- Freeze a repair and report remaining failures. Passing the original acceptance suite did not establish scheduler correctness.
- Check the validator itself. Later audit corrections added exact output-type checks, quantity-type boundaries, and protection against missing or reduced test suites.

## Ten minutes: Reproduce the scheduler case

From the repository root, with `uv` installed:

```sh
uv run --locked python tools/check_publication.py
uv run --locked python tools/evaluate.py --experiment 018
```

The locked environment uses Python 3.14 and may download Python or packages on first use. Validation has been tested on Python 3.14.7/macOS. Other environments remain unverified. These commands make no model calls and need no AI credentials.

The evaluator checks published input hashes, runs temporary candidate copies, and enforces the expected test identities and counts. Each run writes a new directory under `validation/` with a summary, JSON report, and JUnit XML.

**Exit 0 means the observed results match the documented expectations, including known failures. It does not mean every test passed.** Original and repaired Luna should fail the interruption checks; original Luna should also fail R1. Inherited repository lint failures are recorded separately.

Run the integrity checker before generating local reports: its full publication inventory also notices added output files. Keep local reruns separate from retained publication evidence.

## Deeper inspection

| Interest | Start here |
|---|---|
| Scheduler behavior | [Independent R1 regression](results/018/phase23/test_r1.py), [interruption probes](acceptance/test_015_interrupt.py), [repaired source](snapshots/018/repaired-luna/problems/job_scheduler.py) |
| Experimental design and measurement limits | [Methodology](METHODOLOGY.md), [verification ledger](results/018/verification-ledger.json) |
| All 11 experiments, 008–018 | [Task inputs](experiments/), [starting fixtures](fixtures/), [31 snapshot lineages](snapshots/), [recorded results](results/) |
| Stronger validation after the audit | [Acceptance corrections](provenance/AUDIT_CORRECTIONS.md), [technical validation](validation/technical-closeout-2026-11-26/summary.md), [validation after cleanup](validation/final-editorial-2026-11-26/summary.md) |
| Source history, omissions, and reuse | [Publication provenance](provenance/PUBLICATION.md), [MIT license](LICENSE), [license scope](LICENSE_SCOPE.md) |

For the full evaluation, validator regression probes, and the separate pair-counting scaling assessment:

```sh
uv run --locked python tools/evaluate.py
uv run --locked python -B tools/test_evaluate.py
uv run --locked python tools/assess_scaling_014.py
```

Historical acceptance results retain their original test sets. Post-audit validation strengthens experiments 011, 013, and 016; it does not revise those historical outcomes. Independent acceptance suites for 008–010 are unavailable. The study uses single runs and evolving controls, with incomplete coverage and limited public primary evidence for historical timing and token counts.

This project was created with AI assistance, including agent-generated implementations and tests. Authorship statements and third-party exclusions are documented in [rights and authorship](provenance/RIGHTS_REVIEW.md).
