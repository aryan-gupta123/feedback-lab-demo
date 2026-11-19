# Selected-action feedback: six-path development pilot

The expected-feedback arm had lower cumulative EV regret on **2/6** paths, higher regret on **1/6**, and tied on **3/6**. The mean paired difference (expected minus realized feedback) was **-0.004323** return units; negative favors expected feedback. This is the predeclared primary descriptive endpoint, not a profitability or general outcome-bias finding.

## What was compared

Two independently initialized copies of the same pinned local Qwen3-4B-Instruct-2507 (Unsloth Q4_K_M) policy saw identical public market observations and execution rules on each path. Both received only their latest executed option ID and one past-return scalar. P&L feedback gave its realized net return; expected feedback gave the simulator expected net return for that SAME chosen action. Neither arm received unchosen expected values or current hidden means. Expected feedback is privileged past simulator information, not a generally available real-market label.

Each arm and coded baseline began with the same two assigned trades, A/B on even seeds and B/A on odd seeds. Feedback was still delivered, but only the latest episode entered the first model call. All later actions were model/policy choices. Agents were rebuilt per arm/path, with no conversation history, memory retrieval, weight training, persistent belief state or extra forced exploration. After policies diverge, chosen feedback differs as a consequence; comparisons are at the path/policy level, not paired causal effects for individual trades.

## Prospective workflow and gates

The [protocol](NATIVE_FEEDBACK_PILOT_PROTOCOL.md), endpoints, seeds and request caps were committed before inference. The market task explicitly changes the validated diagnostic schema to rationale-first + choice only: there is no copied hidden value or prediction field. Its shared prompt distinguishes known-values controls from uncertain market decisions. Six fresh transfer controls passed 6/6. A separate one-path smoke check (seed 1701, eight episodes) returned 12/12 valid replies and passed its input/accounting audit; both arms tied on regret. That smoke path was not pooled into this main batch and did not prompt policy changes.

The unchanged main batch used six predeclared development seeds, ten episodes each, two initial assignments and eight model choices per arm: 96 model requests. Market mean .012, sigma .04, signal noise .02, correlation .3, abrupt regime; initial cash 10000; fees 5 bps plus slippage 5 bps on each side. The regime schedule and generator parameters were not sent to the model. Only public past prices, time, noisy signals and the latest completed feedback were supplied.

Public return signals and feedback were displayed in integer microreturn units, round(x*1e6), with <=0.5-unit quantization error and full precision preserved for audit/scoring. This is an explicit approximation for market data, not a claim that arbitrary returns lie exactly on the prior control grid. Both treatments used the same rule. Cash remains zero; no copied value becomes a forecast.

## Primary and secondary path results

| Path | P&L EV regret | Expected EV regret | Expected − P&L | P&L phase return | Expected phase return | Different actions / 8 |
|---|---:|---:|---:|---:|---:|---:|
| 1802 | 0.047904 | 0.047904 | +0.000000 | -1.02% | -1.02% | 0 |
| 1803 | 0.000000 | 0.000000 | +0.000000 | 45.79% | 45.79% | 0 |
| 1804 | 0.019956 | 0.000000 | -0.019956 | -0.51% | 2.20% | 2 |
| 1805 | 0.033930 | 0.023952 | -0.009978 | 7.04% | 11.44% | 1 |
| 1806 | 0.009978 | 0.009978 | +0.000000 | 23.84% | 28.83% | 2 |
| 1807 | 0.053886 | 0.057882 | +0.003996 | -5.18% | -9.32% | 2 |

EV regret is summed expected-return loss relative to the feasible cash/single-asset oracle on each model-choice episode; it is not compounded portfolio return or a dollar loss. Realized phase return compounds only after the two assigned episodes, relative to equity at that point. Floating-point differences <=1e-12 count as descriptive ties. Hidden truth is used by the evaluator only.

Path 1806 illustrates the distinction: both arms had equal EV regret, although realized phase returns differed. It is a quality tie under the predeclared endpoint. The large percentage gains on path 1803 are synthetic outcomes over eight toy episodes with deliberately high return/noise settings; they are not annualized or calibrated real-market backtest returns.

## Behavior and coded baselines

| Policy | Mean EV regret | Mean phase return | Cash / 48 | Asset A / 48 | Asset B / 48 |
|---|---:|---:|---:|---:|---:|
| pnl | 0.027609 | 11.66% | 7 | 16 | 25 |
| calibrated | 0.023286 | 12.99% | 2 | 17 | 29 |
| cash | 0.079824 | 0.00% | 48 | 0 | 0 |
| fixed_asset_a | 0.119760 | -1.30% | 0 | 48 | 0 |
| public_signal | 0.031601 | 7.91% | 7 | 16 | 25 |

Identical action sequences between feedback arms occurred on 2/6 paths. Choices matching the coded public-signal policy: P&L 34/48, expected feedback 39/48. These are descriptive behavioral matches, not proof of what the model internally attended to or whether its explanations are faithful.

Cash, fixed-A and signal-greedy controls used the same assigned exploration. The signal policy maximizes cost-adjusted estimated net return from the same rounded PUBLIC signals; it never reads latent means. Coded policies make zero model calls. No return-based seed selection, clipping, output repair or favorable-action forcing was used.

## Integrity, usage and limits

All 96/96 main responses were received, with 0 invalid responses/fallbacks. The independent audit verified identical public observations, assignments, pre-request feedback timing, selected-only content, provider identity/usage, raw choices versus executed weights, every reported endpoint and paired difference. It recalculated fees/slippage, turnover, equity and EV/regret independently of the portfolio return helper. 2965 numeric comparisons passed; max difference 1.64e-11, tolerance 1e-09. Source digests and earlier artifact hashes matched.

The regression suite passed 107 tests, including selected-only feedback isolation, causal diagnostic snapshots, common exploration, baseline accounting, and preservation of attempted calls when provider usage is unavailable. Touched Python files passed lint.

The auditor detected all four deliberate corruptions in copies of smoke artifacts: altered equity, wrong feedback value, injected hidden expected values and a missing response. Originals remained unchanged. Full raw inputs/responses and full-precision source diagnostics were retained, including rationales and assigned actions.

Main provider-reported usage: 84,485 input / 14,196 output tokens. Model API fees $0; cloud compute/storage costs are excluded. Local CPU inference is serialized; virtual bars do not wait on real-time prices, so this is not a deployment latency/deadline test. Config: b12242, four CPU threads, context 4096, one slot, temperature 0, seed 42, output cap 256, timeout 120s, no retries.

The shared market prompt does not explicitly fix a risk-utility function beyond the paper-trading task. EV regret is an external risk-neutral reference score; conservative cash choices should not be labeled universally irrational. A larger study should state the decision objective and risk preference explicitly. 

Across all gates there were 114 unique received responses: 6 controls, 12 smoke and 96 main. The final physical model/runtime checksum and server context/identity check passed, and credential scans found no key in the raw artifacts.

| Main request latency | P&L | Expected |
|---|---:|---:|
| Mean seconds | 17.79 | 17.71 |
| Summed seconds | 854.06 | 850.00 |

Request times exclude rate-limiter waits and are not total setup/study wall time. They are descriptive CPU resource measurements, not a latency-matched efficacy result.

The return-type label and numeric feedback value both change between arms; this pilot does not isolate numerical noise reduction from label interpretation. There are only six independent paths, one deterministic model run per arm and one short synthetic regime family. Decisions and permutations are dependent. No p-values, confidence intervals, power claim or evidence of equivalence is reported. This chosen-action expected-value treatment is privileged simulator feedback and may not transfer to noisy real feedback. Latest-only context restricts adaptation; a cash choice can subsequently yield only zero feedback. Shared past prices permit both arms to infer historical realized outcomes. The prior interface checks do not guarantee optimal uncertain-market decisions. No reserved evaluation paths or real trades were used.

## Next step

Keep this frozen pilot and its negative/null outcomes intact. Before a larger study, use the observed action patterns and coded baselines to decide whether a prospective feedback-response probe or a better policy/task formulation is needed. Any changed prompt, context policy, model or exploration schedule needs a separate development version and fresh validation. Only then perform prospective power analysis and freeze a disjoint evaluation study. This batch alone cannot establish that better feedback generally helps or does not help AI decisions.

## Reproduction and evidence

Runner: `research/experiments/outcome_bias/native_pilot.py`; agent: `research/agents/native_feedback.py`; independent auditor: `research/evaluation/native_feedback_audit.py`. CLI defaults to a no-inference plan. Stage order is controls → audited smoke → main; populated directories cannot be automatically resumed or overwritten. Commit source before live collection.

Raw stages are `research/results/native_feedback_v1_controls/`, `native_feedback_v1_smoke/` and `native_feedback_v1_main/`. They are ignored by Git. The review archive contains all stages, plots, audit/probe scripts and implementation, excluding weights/keys. Report and compact structured audit are committed. Fresh-task restoration of cached weights/raw results has not been independently verified.
