# Post-hoc aggregation-only control

This control compares the original arithmetic probability mean with the normalized geometric probability mean on the identical saved five-member fixed-binding pool. The original canonical first order is a lower-cost reference. It is **post hoc**, adds **zero model forwards**, and is **not an AnyJev reproduction**.

The specification was recorded in [PROTOCOL.json](PROTOCOL.json) before computing the new contrasts, after inspecting the already available original panel and arithmetic results. [INPUTS.json](INPUTS.json) records exact input hashes and portable relative paths. [FREEZE.json](FREEZE.json) binds the analysis code and protocol before execution. Source data and original analyzers remain unchanged.

Run from the repository root with Python 3.10 or newer; only the standard library is used:

```sh
python3 -B -m unittest discover -s paper/naacl2027/aggregation_control_20261005 -p 'test_*.py' -v
python3 -B paper/naacl2027/aggregation_control_20261005/analyze.py --out /tmp/logittrail-aggregation-control-replay
```

The output directory must not already exist. No model weights, network, tokenizer, inference runtime or source-question download is used. Keep this directory beside `generality_20261003/publication/bundle_v1` when relocating it; every dependency is resolved relative to the analysis directory. The full public bundle is hash-verified, and its frozen reader validates schedules, candidates, probability reconstruction, item identity and forward accounting.

The saved [report](results/REPORT.md), [machine-readable results](results/RESULTS.json) and [item records](results/records.jsonl) include all four model/dataset strata and every specified contrast. Arithmetic and geometric methods share 1,200 existing responses per stratum, rather than paying for distinct pools. First order uses 240 existing responses per stratum. Bootstrap intervals are paired, exploratory and unadjusted; no multiplicity-adjusted winner is declared.

The tests use independent high-precision probability products, including a fixture in which arithmetic and geometric predictions differ; invariants cover member order, additive logit shifts, semantic candidate alignment, underflow, deterministic ties and paired transition accounting. These are computational checks, not human evaluation or independent machine replication.
