# External expanded pilot: frozen preparation for 600 questions

This directory prepares **600 additional public-development examples**, with no model inference. Selection, task instructions, temperature policy, metrics, and failure handling are fixed in [PROTOCOL.json](PROTOCOL.json). The [local preparation record](PREPARATION.json) is not an independently registered protocol. Results were not consulted in choosing the sample or prompts.

The separate [v0.2 matched study](../matched_study/README.md) is using this frozen material in an experiment that is currently in progress. The sample counts here describe preparation; this page does not claim completed inference or report new model-performance results.

| Dataset | Source split | Fixed sample | Readout | Primary outcome |
|---|---|---:|---|---|
| JCoLA v1.0 | in_domain_valid | 100 | Noul | MCC; report each domain separately and combined |
| JCoLA v1.0 | out_of_domain_valid | 100 | Noul | MCC |
| JSTS v1.3 | valid | 200 | Score, six ordered anchors 0–5 | MAE of expected score against original continuous gold |
| JCommonsenseQA v1.3 | valid | 200 | Choice, five alternatives | Accuracy |

Counts follow a 600-question compute budget, not a power calculation. Within each source file, selection takes the first fixed number of IDs after deterministic SHA-256 ordering. It does not balance gold labels or filter on text, length, difficulty, or predictions. Missing or failed examples must not be replaced. The selected JCoLA subsets contain 88/100 and 70/100 acceptable sentences respectively, so accuracy alone would be misleading; an always-acceptable rule attains 79% across the 200 selected examples while its MCC is undefined. Report confusion counts and balanced accuracy alongside MCC.

## Sources and licenses

JSTS and JCommonsenseQA use the same [official JGLUE commit](https://github.com/yahoojapan/JGLUE/tree/6f071c09316baae89c3d083a90985b4b1cb9968c) as the earlier JNLI pilot. JGLUE was created by Kentaro Kurihara, Daisuke Kawahara, and Tomohide Shibata through Yahoo Japan Corporation and Kawahara Lab, Waseda University. Its [license](https://github.com/yahoojapan/JGLUE/blob/6f071c09316baae89c3d083a90985b4b1cb9968c/LICENSE) is CC BY-SA 4.0; a copy is [LICENSE-JGLUE.txt](LICENSE-JGLUE.txt). [JGLUE paper](https://aclanthology.org/2022.lrec-1.317/).

JCoLA is linked from JGLUE but distributed separately by Taiga Someya, Yushi Sugimoto, and Yohei Oseki. We pin [osekilab/JCoLA commit 736d9eef3af04bb17e4cf59adf01325973234ff9](https://github.com/osekilab/JCoLA/tree/736d9eef3af04bb17e4cf59adf01325973234ff9), whose [README](https://github.com/osekilab/JCoLA/blob/736d9eef3af04bb17e4cf59adf01325973234ff9/README.md) defines binary linguistic acceptability and identifies the sentence/source fields. The separate [license](https://github.com/osekilab/JCoLA/blob/736d9eef3af04bb17e4cf59adf01325973234ff9/LICENSE) is also CC BY-SA 4.0; [LICENSE-JCoLA.txt](LICENSE-JCoLA.txt) preserves its bytes. [JCoLA paper](https://aclanthology.org/2024.lrec-main.828/).

The dataset-derived selection, gold metadata, groups, audit records, predictions, and results are shared under **CC BY-SA 4.0**, with attribution to the respective creators. This directory's external task [PROTOCOL.json](PROTOCOL.json), including its prompt/rubric adaptations and copies embedded in preparation records, carries that data license. Changes are deterministic subsampling, field selection, hashing, grouping, question formatting, and, when evaluated, added model predictions and aggregate metrics. Prompt descriptions for JSTS paraphrase its [official annotation guidelines](https://github.com/yahoojapan/JGLUE/blob/6f071c09316baae89c3d083a90985b4b1cb9968c/task_guidelines.md#jsts) and carry the same attribution. Python preparation, materialization, and fixture code use the repository **MIT** license. Original explanatory prose remains project-authored documentation; attributed dataset/rubric extracts retain their source terms. Dataset material is not relicensed as MIT; no endorsement is implied.

The same data notice follows external records into the [matched-study selection and results](../matched_study/README.md). Redistribute a mixed local/external selection or prediction file with its CC BY-SA 4.0 attribution; the original project-authored local data retain their MIT license. No source text, compiled native artifacts, or model weights are included in this data-preparation package.

## Readout and gold handling

JCoLA uses only the published `sentence` as input. Source citations, original sentences, annotation diacritics, and gold labels are excluded. Label 1 maps to `true` and 0 to `false`. The dataset's “in-domain”/“out-of-domain” names describe its literature-source splits; they do not prove these are unseen domains for the base model.

JSTS's original score remains a floating-point `gold_score`. **There is no generated integer `label`, rounding, or argmax-stage accuracy.** The runtime estimates an expectation over six fixed rubric anchors; compare `sum(k * p[k])` directly with the continuous reference. The sample has 137 noninteger references. Primary MAE, secondary RMSE, Pearson and tie-aware Spearman correlations describe transfer to continuous similarity without fitting an STS-specific model. Class NLL/Brier would require an invented categorical gold distribution and are not part of this protocol.

JCommonsenseQA keeps original candidate order with keys `option_0`…`option_4`. Native canonical sorting therefore preserves that order. Questions and options are inserted unchanged. This is not an option-order robustness test.

Primary probabilities use T=1. The historical temperature 1.3489628825916533 may be applied secondarily to the same saved logits. Nothing is fitted to these samples. Do not aggregate Noul classification, Choice classification, and continuous Score regression into one “overall accuracy.”

For the matched generation comparison, evaluate hard-selected-stage MAE against the same continuous JSTS reference as a separate like-for-like outcome. A selected stage and an expected score are different estimators; do not label their comparison as equal-output functionality. The common timed HTTP contract returns a semantic label, with direct/one-token distributions retained in audit records for the expectation analysis.

## Dependence audit

The [audit](AUDIT.json) records exact-text and caption/image sharing before inference. Eight selected JSTS rows share an exact sentence with another selected JSTS row. Of the 200 JSTS rows, **six share a sentence or image with the earlier 300-row JNLI pilot, including three identical ordered sentence pairs**. None was filtered or replaced after this check. JSTS and JNLI are related caption tasks, not two independent external sources.

The `group` field uses bibliographic-source hashes for JCoLA (34 selected groups), shared-sentence/image connected components for JSTS (196 selected groups, computed jointly with prior JNLI), and exact-question hashes for JCommonsenseQA (200 groups). These are observable dependence proxies. Shared linguistic constructions, concepts, paraphrases, or broader image relationships can remain unmeasured. Small subsets do not justify IID-item confidence intervals or broad power claims. Pretraining and post-training contamination remain unknown.

## Files and reproduction

Only IDs, hashes, gold and group metadata are public. Raw source text and the transformed `questions.jsonl` are written to an explicitly supplied cache outside the repository. Hashes are not encryption; public original data can be downloaded and matched. [SELECTION.json](SELECTION.json) fixes all 600 IDs and their row/question hashes. It also fixes the full transformed question-file SHA-256:

```text
4df650133880c935c885668b46b33d8d49c14fdb82b0703b4bf45e0bc297272b
```

The schema is:

```text
id, source="external", dataset, split, type, state, instructions, criteria, group
+ label (JCoLA: "false"/"true"; JCommonsenseQA: "option_0"..."option_4")
+ gold_score (JSTS only: continuous number in [0,5], no label field)
```

Inference must receive **only `type`, `state`, `instructions`, `criteria`**. Keep all gold and metadata outside the model input.

Tests use synthetic fixtures and require no download, model, GPU, or third-party Python packages:

```bash
python3 -m unittest discover -s paper/external_expanded -p test_prepare.py -v
```

The frozen release already contains preparation records. Reconstruct the data and questions in a fresh external cache, verify every hash, and leave the public records unchanged:

```bash
python3 paper/external_expanded/materialize.py \
  --cache-dir /absolute/path/outside-repository/expanded-cache

python3 paper/external_expanded/prepare.py verify \
  --cache-dir /absolute/path/outside-repository/expanded-cache
```

`materialize.py` calls the frozen verifier, downloads only missing pinned source files with ordinary HTTPS certificate verification, and verifies byte counts/hashes, protocol/script identity, selection, and overlap audit. If the external `questions.jsonl` is absent, it constructs it only after the public index matches; it never overwrites an existing file. A second verification checks its bytes against the frozen file hash. No raw text is written to this repository.

`prepare` is reserved for a new study directory with no existing preparation/selection/audit outputs; it refuses to overwrite the frozen records. A source, script, protocol, index, or question-file mismatch fails closed. No inference tool is imported or invoked by preparation.
