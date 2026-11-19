# What the reliability experiment adds—and what it does not

This is a focused evaluation artifact, not a new learning algorithm or a demonstrated literature-first result. Its contribution to this project is a controlled source-calibration test with known scoring truth, independent held-out paths, explicit validation gates, ordinary statistical baselines and inspectable negative evidence.

## Closest in-context regression comparison

Garg, Tsipras, Liang and Valiant, *What Can Transformers Learn In-Context? A Case Study of Simple Function Classes* (2022), is directly relevant. The [author repository](https://github.com/dtsip/in-context-learning/tree/338337192195827c58356f9b627e5f999ea703d2) exposes trainable models, linear-regression tasks, noisy prediction targets and a least-squares baseline. In this pass the author README and the relevant definitions in `src/tasks.py` and `src/models.py` were inspected and pinned; the full paper was not reviewed. Exact source URLs and digests are recorded in the research repository's literature receipt.

Our forecast-to-settlement calibration is itself an in-context regression problem. Inferring a signed relationship from numerical examples, comparing with a linear estimator, and learning from noisy targets are therefore not claimed as new ideas. This project uses fixed off-the-shelf quantized instruction checkpoints and asks for a discrete risk-neutral decision (cash or either asset), with a public signal and reliable/unrelated/inverted source conditions. The endpoint is paired expected-value regret rather than regression prediction error. Those are differences in this test's design, not proof that no prior work has used the same combination. No external paper's models were rerun or outperformed in a matched comparison.

## Relation to the earlier feedback comparison

The earlier focused review inspected full author-hosted copies of Self-Refine and Lee JiaQie's outcome-bias report, with their versions and limitations recorded separately. Self-Refine already investigates informative/actionable feedback versus generic feedback. Lee's design concerns retrospective judgments under different outcomes. This study does not introduce informative feedback, self-refinement, or an outcome-bias intervention: a source changes the available evidence about a new decision, so reacting to it can be rational.

Compared with this project's earlier factorial experiment, the new source test replaces privileged past expected-return feedback with noisy settled calibration outcomes, fixes wording across source arms, doubles the number of independent held-out paths per eligible checkpoint to 48, and includes a predeclared numerical calibration rule. Current forecasts remain synthetic noisy measurements of simulator latent returns, not forecasts produced by a real trained financial predictor.

## Boundaries that prevent stronger claims

- The intervention supplies current forecasts and calibration history together. A history ablation holding current forecasts fixed is needed to attribute a benefit specifically to historical calibration.
- Inverted and reliable sources have equal information content for an observer that knows their signs; unrelated forecasts remove predictive information. Inversion is not an adaptive adversary.
- The regression benchmark shares the observed records but has specialized structural assumptions, including a variance floor matching a simulator noise scale absent from the model prompt. Do not describe this as identical total prior knowledge or a proven optimal policy.
- Phi-3.5-mini failed the fixed numeric gate (4/6) and was excluded. This is a failure of this checkpoint/runtime/prompt combination, not a general claim about the Phi family. Completed decision-performance results remain two Qwen checkpoints.
- A single stationary Gaussian mechanism and direct-choice prompt do not establish real-market forecasting, regime adaptation, or robustness across task families.

A manuscript still needs a broader full-paper comparison around source credibility, noisy demonstrations and in-context decision making. The current evidence can support a narrowly described controlled study and engineering artifact; it cannot certify novelty or guarantee workshop acceptance.
