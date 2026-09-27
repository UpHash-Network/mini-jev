# LMQL saved-run diagnostics

Post-hoc arithmetic analysis of the original frozen 12-case custom LMTP diagnostic. No new inference, no human participants, and no modification to the frozen evidence or thresholds.

- [Japanese summary](SUMMARY.ja.md)
- [English summary](SUMMARY.en.md)
- [Full derived result and evidence hashes](DIAGNOSTIC.json)
- [Standard-library analysis script](analyze.py)

From the repository root:

```sh
python3 paper/naacl2027/nonhuman_revision_20260927/lmql_diagnostic/analyze.py
```

The script verifies and reads the original artifacts under `paper/naacl2027/comparator_study/`; it writes only this directory's derived `DIAGNOSTIC.json`. It can be rerun deterministically without the model, LMQL installation, or network. Success means that reanalysis of the saved evidence completed. **It does not turn the original failed probability gate into a pass.**

All 12 argmax decisions agree, but score-01, score-03, and score-04 remain outside the 1e-5 probability tolerance. The saved inputs have very large margins and confound task type, candidate count, and assistant prefix. These diagnostics are not a task benchmark, a stock-backend comparison, or a human usability evaluation.
