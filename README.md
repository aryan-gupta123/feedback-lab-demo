# Feedback Lab: recorded local-model evaluation

[Open the demo](https://aryan-gupta123.github.io/feedback-lab-demo/).

The current page covers the frozen feedback-reliability study: 48 independent synthetic paths per eligible checkpoint, reliable/unrelated/inverted sources, public-only comparisons and same-information statistical baselines. It is a replay of recorded inference, not live trading. Prior failed interfaces and negative results are retained in the study log.

Download this repository, then run `python3 verify.py .` to independently rescore raw evaluation replies, check chronology/pairing and recompute statistical baselines and confidence intervals. Python standard library only; no network or model required. It verifies the arithmetic of recorded evidence, not a signed attestation from the model publisher. The research implementation remains private.

`pilot.html` preserves the earlier six-path pilot. Its data and interface case study are historical and are not pooled into the current study. `verify_pilot.py` is the original historical verifier; the old checksum inventory is preserved separately as `PILOT_SHA256SUMS` because the public homepage and report have changed. The original verifier checks the current release checksums before checking the preserved pilot arithmetic; run `python3 verify_pilot.py` for those historical checks.

See `protocol.md`, `run-log.md`, `report.md`, and `replay.json` for exact scope, pre-evaluation revisions and the complete evaluation evidence. API fees were $0; host compute and storage costs are excluded. This project claims a focused evaluation artifact, not a novel trading algorithm or an investment strategy.


The reliable-source effects were uncertain; noisy and inverted sources increased mean expected-value regret in both tested checkpoints. Qwen3's asset-B concentration is shown openly in the action-count table. A separate post-hoc four-path / 32-response asset-renaming diagnostic found naming/presentation sensitivity; its raw evidence is label-diagnostic.json and it is not pooled into the primary 48 paths. The main study has 443 attempts; the two phases combined have 475 (including retained failures). The different-family Phi candidate failed 4/6 numeric controls and is excluded, so completed performance comparisons remain two Qwen checkpoints.

The forecasts are simulated measurements, not predictions from a trained financial model. The numerical benchmark has specialized prior assumptions, and the source intervention includes both current forecasts and their calibration history. See report.md and positioning.md for the boundaries of the claims.
