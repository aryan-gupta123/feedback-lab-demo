# Feedback Lab: recorded evaluation demo

This repository contains only the public browser demo and recorded research data. The implementation repository remains private.

Open index.html locally. No model, API key, package installation or internet access is needed. Select all six paths, including the higher-regret path and ties. case-study.html documents a real failed control and its narrower pipeline fix.

To verify the saved evidence: python verify.py (Python 3.11+, no third-party packages; do not use -O). The verifier checks 96 main model choices, 2,257 arithmetic comparisons, and 48 numeric-interface controls. Model API fees were zero; host costs are excluded. Data-only evidence excludes the original bundle's private implementation/review scripts. PUBLICATION.json lists published members, and SHA256SUMS records integrity digests.

To host for free, upload these files and the evidence folder to a public demo-only repository, then choose Settings → Pages → Deploy from a branch → main → /(root). Do not make the implementation repository public or upload its history. Wait for GitHub's Pages build before sharing the URL.

Results are exploratory: expected-return feedback lowered regret on two of six paths, raised it on one, and tied on three. No profitability, significance, broad reasoning improvement or novelty claim is made.
