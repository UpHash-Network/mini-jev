# 3 October 2026 diagnostic and import revision

Added a browser-local physical-record importer and a frozen confirmation study on 240 project-unused JCQA questions. Both checkpoints completed five rotations per question: 2,400 measured calls plus 30 excluded synthetic checks/warmups, with no recorded failure.

The two-call entropy-plus-TV diagnostic did not establish an AP improvement over entropy. At the primary 720-call budget their per-item correctness coincides: 197/240 for 1.5B and 235/240 for 35B. The first-entropy reference gives 200/240 and 235/240; this secondary point estimate is not a retuned winning policy. Full scores and budget curves remain in the [portable report](../diagnostic_value_20261003/publication/REPORT.ja.md) and [CPU replay](../diagnostic_value_20261003/publication/README.md).

Separate AI implementations checked all 2,400 logit records, 64 AP/AUROC point metrics and 40 budget-policy points. The portable replay preserves the frozen functions and reproduces the original numerical result exactly. This is arithmetic reproducibility, not independent inference or human evidence.

The [importer](https://uphash-network.github.io/mini-jev/explorer/import/) handles semantic alignment, typed values, unknown references/latency, and exact export without uploading data. Synthetic, archived-record, browser and source-release checks are recorded separately from model results.

The manuscript retains the null result, paired-bootstrap limits and cost accounting. Full PDF review confirms 6 main pages including acknowledgements, ethics/references on pages 7–8 and 2 appendix pages. Frozen arXiv files and the earlier source/evidence ZIP remain byte-identical. See CHECKS.json for exact hashes.
