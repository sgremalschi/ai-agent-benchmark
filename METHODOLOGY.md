# Methodology and limitations

## Evidence and experimental design

Experiments 008–018 are preserved observations, not a statistically powered model ranking. The recorded 012–017 runner compared Luna (`gpt-6-luna`) with Sol (`gpt-6.1-sol`), both at medium reasoning, in fresh ephemeral Codex CLI sessions. Each pair began from the same commit. Luna always ran first; order was neither randomized nor counterbalanced. Machine load, warming and other order effects may confound timings, and their contribution was not measured.

Tasks specified editable files and required agent-written tests. Repository tests therefore reflect different agent-generated coverage; their counts are not comparable quality scores. Independent acceptance suites were maintained separately. Instructions and information-access controls evolved across experiments; the older harness did not establish a complete access boundary. A single run per model/task was preserved.

Original prompts and structured measurements for 008–011 were unavailable. Their snapshots were reconstructed from existing commits, without inferring missing timings or outcomes. The recovered 011 acceptance suite supports fresh evaluation only. Both 010 candidates started from Luna 009. Recorded 012–014 reports misflag some allowed implementation changes as unexpected; retain those fields as reported and interpret them with that caveat.

The historical task files under experiments/ are model inputs, not instructions for running new experiments. Behavioral fixtures and independent tests remain separate from those inputs.

## Experiment 018

Sol reviewed a history-free copy of original Luna 015 against the original scheduler requirements. Review did not edit the implementation. The reviewer reported one finding, R1, which was independently reproduced in 20 of 20 trials. Only that verified finding was supplied to one fresh Luna repair session. No independent acceptance, supplementary interruption or final-evaluation feedback was supplied for another repair.

Information-access checks supported the intended separation of candidates, prior results and independent tests. They establish the observed controls, not complete isolation. The reviewer did not execute pytest. The repair stage had pytest and Ruff available. Review conclusions must be assessed with that capability difference in mind.

The output was frozen after the single repair. Original Luna, original Sol and repaired Luna were then evaluated independently, with acceptance, interruption and R1 results reported separately. The recorded experiment included cross-candidate scheduler-suite comparisons, retained in the final comparison. The portable evaluator runs repository tests, the supported independent suites and scoped/repository lint; it does not reproduce every historical cross-suite check.

The repair captures an insertion cutoff before reading the injected clock. It adds one short lock acquisition, preserves the public API and scan/sort complexity, and retains the 18 original scheduler tests while adding one regression. Both interruption cases remain failing in repaired Luna. Sol's review did not report those defects. The added Luna regression is not portable to Sol's lock-held clock design; the independent R1 test accommodates either design. No new behavioral regression was observed in the evaluated suites, which is not an exhaustive guarantee.

## Effort accounting

| Stage | Agent seconds | Input tokens | Cached input tokens | Output tokens |
|---|---:|---:|---:|---:|
| Original Luna implementation | 92.66 | 205,862 | 188,416 | 4,271 |
| Sol review | 40.02 | 89,340 | 73,856 | 1,466 |
| Luna repair | 28.41 | 83,016 | 76,160 | 1,076 |
| Total | 161.09 | 378,218 | 338,432 | 6,813 |

Review and repair added 68.43 agent seconds (+73.85%), 172,356 input tokens and 2,542 output tokens over original Luna. Cached input is already included in input totals. Reasoning output is a subset of output and is not added again. Original Sol's 122.98 agent seconds are a comparator, not part of the collaborative total.

Agent execution is not total elapsed engineering effort. Instrumented experimental setup took at least 499.3683 seconds: 485.390464 for the review stage and 13.977846 for repair preparation. Finding verification took 36.06 seconds; independent evaluation took 8.5434 seconds, for 44.6034 seconds combined. Evaluator infrastructure preparation after freezing took another 44.344586 seconds. These categories are separate and must not be described as model execution or measured human labor.

Setup is a lower bound; some infrastructure authoring and initial inspection were outside the measured intervals. Idle time between stages was excluded. Historical orchestration, active human effort and orchestrator token usage were not measured. Applicable billed pricing was unavailable, so no dollar-cost claim is made. The [effort record](results/018/phase23/cumulative-effort.json) preserves the detailed measurements and missing values.

## Reproduction and known failures

The evaluator uses temporary candidate copies, validates implementation import locations, disables third-party pytest plugin autoloading and checks that snapshots remain unchanged during evaluation. It needs no AI credentials or original repositories. Python 3.14.7/macOS is the tested configuration; metadata allowing later Python versions is not evidence that they were tested. Locked tools are pytest 9.1.1 and Ruff 0.16.8.

All 23 release candidate entries match documented outcomes. That includes original/repaired Luna interruption failures, original Luna's R1 failure, and inherited repository-wide Ruff I001 failures for 014–018 in order_processor.py. Experiment 011 passes its recovered 16-case acceptance suite in fresh validation, without establishing its historical outcome. Independent suites for 008–010 are unavailable. Baseline snapshots establish provenance rather than additional implemented candidates.

Release tests omit identified example cases without established distribution permission; historical test counts remain tied to their original test sets. Independent acceptance, interruption and R1 suites are unchanged. Concurrent tests use bounded waits and may behave differently on slow machines. The evaluator does not measure experiment 014 performance, run agents or reconstruct missing independent suites. Supplementary tests are now available to readers; future blinded experiments require a fresh design.

## Reading the records

The results/012–017 reports are preserved measurements. Experiment 018 has review-stage subtotals as well as completed workflow totals; use phase23/final-report.json and phase23/cumulative-effort.json for the final comparison. Public derivatives normalize machine paths, annotate agent self-reports and omit incidental execution records. Original-source and derivative hashes are recorded in the [manifest](provenance/manifest.json).

Integrity checks establish file/link consistency and selected privacy-pattern findings. They do not establish editorial quality, comprehensive privacy review, legal clearance, or correctness beyond the executed tests.
