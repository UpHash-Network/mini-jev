# Sources, rights and portability

The control's original code is covered by the repository's [MIT license](../../../LICENSE). It reuses the already published [bilingual panel and attribution](../generality_20261003/publication/README.md#sources-and-rights), whose exact source revisions and selection are retained in [SELECTION.json](../generality_20261003/publication/bundle_v1/code/SELECTION.json).

- Japanese [JGLUE / JCommonsenseQA](https://github.com/yahoojapan/JGLUE): applicable Japanese-derived selection and outcome material retains CC BY-SA 4.0, with source attribution inherited from the panel.
- English [CommonsenseQA](https://huggingface.co/datasets/tau/commonsense_qa): MIT; [Talmor et al., NAACL 2019](https://aclanthology.org/N19-1421/).
- No source-question text, model weights, participant observations or private machine paths are added by this control. Existing upstream model and dataset terms remain applicable.

For relocation, retain the complete sibling `generality_20261003/publication` input tree: the control checks the context `REPORT.ja.md` hash as well as `bundle_v1`. Every required path is listed relative to this directory in [INPUTS.json](INPUTS.json). A relocated replay from an unrelated working directory reproduced the numerical results exactly apart from the creation timestamp, and reproduced the report and item records byte-for-byte. [CHECKS.json](CHECKS.json) records the checks and the initially incomplete portability harness.

This note was added after the outcome calculation. It does not change the locally frozen protocol, analyzer, tests, README or saved results. Automated verification is not independent human validation or replication on another physical machine.

## CI replay verification

The separate, unfrozen [verify_replay.py](verify_replay.py) checks both result directories against their own `MANIFEST.json`, compares every value in `RESULTS.json` and all 960 `records.jsonl` entries, and requires a byte-identical `REPORT.md`. It permits absolute floating-point differences up to `1e-12` and ignores only the top-level `RESULTS.json/created_at` value. JSON types, dictionary keys, list shapes, integer counts, strings and booleans must match exactly; duplicate JSON keys and nonfinite values fail verification.

After replaying into a new output directory, run from the repository root:

```sh
python3 -B paper/naacl2027/aggregation_control_20261005/verify_replay.py --actual /tmp/logittrail-aggregation-control-replay
python3 -B -m unittest discover -s paper/naacl2027/aggregation_control_20261005 -p 'test_verify_replay.py' -v
```

The expected directory defaults to the saved `results` beside the verifier; `--expected DIR` overrides it. [test_verify_replay.py](test_verify_replay.py) injects altered accuracy, cost, record probability, record count, nested timestamps, types, keys, reports, duplicate keys, nonfinite values and bad hashes. Altered numerical fixtures receive fresh matching manifests, demonstrating that semantic comparison catches changes even when manifest hashes are internally consistent. [VERIFIER_CHECKS.json](VERIFIER_CHECKS.json) records these checks separately from the frozen analysis checks.
