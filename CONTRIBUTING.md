# Contributing

Bug reports, independent reproductions, and task-family holdout evaluations are welcome. Include your model revision, device, dtype, Python/library versions, complete input-token count, and exact command. Remove private inputs before sharing a report.

Keep training, model selection, temperature fitting, and final evaluation separate. Do not tune on the published 2,400-question acceptance set and then call the result an independent test. Report family-level results and failures as well as the aggregate score.

Distinguish API validity from semantic accuracy, candidate-conditional probabilities from correctness probabilities, and full request latency from per-item throughput. Model or hardware changes require new measurements.

Run the local checks described in the README. GPU tests and model downloads are explicit opt-in operations; the default CI runs validation tests on small fixtures without downloading a model.

AI-assisted contributions are welcome. Describe how code and labels were checked, and identify machine-authored data clearly. By contributing, you agree that your original contribution is provided under this project's MIT license; retain third-party notices.
