# Data card: Mini Jev evaluation and training data

## Purpose and ownership

This repository contains project-authored Japanese decision tasks for implementation checks, model development, and a final local acceptance run. The project owner is Yuki Oshio. AI agents wrote the generation code, individually authored examples, and performed peer checking under the owner's direction. There was no independent human-expert annotation study.

Original authored data is released under the repository's MIT license. Model weights and third-party resources are governed by their own licenses. The original local-suite release did not import an external public benchmark and does not claim representative coverage of real customer data. The working paper adds a separate JNLI pilot and a v0.2 study using three further public datasets, described below; these do not change the local suite or its historical results.

## Primary release: acceptance v2

| Split or subset | Count | Composition | Role |
|---|---:|---|---|
| Final test, template-generated | 2,220 | 45 template families | Final quality measurement |
| Final test, individually AI-authored | 180 | 60 per output type; 26 broad skill tags | Separately reported quality subset |
| Final test, combined | **2,400** | **800 Choice, 800 Noul, 800 Score** | Main published figure |
| Calibration | 120 | 40 per output type | Temperature only; excluded from 2,400 |
| Reversed Choice maps | 800 | Same original Choice examples | Canonicalization check; not new questions |
| Warm-up inputs | 7 | Runtime warm-up | Not quality data |

The final export is [JSONL](acceptance-v2/questions_2400.jsonl) or [UTF-8 BOM CSV](acceptance-v2/questions_2400.csv). The calibration and original evaluation split files live under `acceptance-v2/private/`; “private” is a historical directory name, and those files are public in this repository.

The retained `source: manual` metadata means **individually AI-authored rather than generated from the programmatic template loop**. It does not mean a human wrote or verified the question. Historical files may say “manual,” “hand-authored,” “手書き,” or “別担当者”; interpret those terms using this disclosure. AI peer review is not external peer review.

## Schema and labels

Each JSONL row contains an `id`, `type`, `state`, `instructions`, `label`, and provenance fields. Choice uses a criteria object mapping semantic keys to descriptions. Score uses an ordered criteria list; its gold label identifies a zero-based stage. Noul is a binary decision. `state` can be text or structured JSON. `family` supplies the analysis group; individually authored examples also retain a `tag`.

The exported gold label must not be included in the model prompt. The evaluation runner prepares questions without gold or authoring metadata and compares outputs afterward. CSV preserves structured fields as JSON text; the export script checks round-trip equivalence. The public export adds a `family` field copied from `tag` where appropriate; question content and gold labels are unchanged.

Tasks cover stated facts, negation, conditions, exceptions, timelines, reference resolution, counts, and ordinal boundaries. Most generated families contain 49 or 50 instances. They share templates, so examples within a family are correlated. Quality cases contain 2–8 candidates, while the API permits up to 26. Higher cardinality receives functional checks only.

## Construction, overlap, and meaning of held out

An earlier v1 suite was used during development. Its failures informed later work. Before authoring v2, the authoring AI agent had diagnosed the first 400 frozen v1 predictions. The v2 authoring audit says that no v2 predictions or selected new model were consulted; new situations and rubrics were created while retaining skill-family and cardinality distributions.

Exact input overlap with v1 is reported as zero, and within-v2 duplicate checks passed. Normalized lexical similarity was also inspected. Neither exact deduplication nor low lexical similarity proves semantic independence: v1 and v2 deliberately exercise related abstract skills. The 180-item authored subset and 120-item calibration set were reviewed by another AI agent.

The final model configuration, formatter, temperature, and data were fixed before evaluating v2. Thus v2 was held out at the level of new evaluation items used for the final run. It is **not** a family-disjoint, externally supplied, independently human-reviewed, or fully blind benchmark. The term “independent” in older acceptance documents has this narrower operational meaning.

[Authoring and review audit](acceptance-v2/MANUAL_AUDIT.json) · [Generated statistics](acceptance-v2/private/generated_stats.json) · [Export manifest](acceptance-v2/EXPORT_MANIFEST.json)

## Results and limitations

The frozen native run answered 2,238/2,400 correctly; the individually AI-authored subset scored 172/180. Published per-family results expose weak areas rather than masking them in the overall average. For example, delay-from-promised-time scored 29/49, conditional obligation 31/49, and counts after cancellation 33/49. The individually authored arithmetic subset scored 10/17.

The benchmark does not establish accuracy in other languages, new domains, open-ended tasks, adversarial inputs, subjective annotation settings, or high-stakes decisions. Gold labels were project-authored and may contain errors. Please report suspected errors with row IDs and reasoning; corrections should version the data and retain the original results rather than silently changing the historical test.

Reversing a Choice dictionary does not produce an independent item: the runtime sorts semantic keys, and the same resulting prompt is recomputed. It is a useful software check, not evidence of learned option-order invariance.

## Earlier training experiment

The `data/head_*.jsonl` files support a separate Qwen2.5-1.5B-Instruct experiment:

- Training: 768 synthetic rows plus 256 reversed Choice variants, all retained in the training split; total 1,024.
- Development: 192 rows for selecting training settings and checkpoints.
- Calibration: 192 rows for fitting temperature after model selection.
- Test: 96 newly, individually AI-authored rows, balanced across types.
- Legacy evaluation: 48 already-examined rows for regression checks.

Training, development, and calibration are grouped by semantic scenario, but share generator templates. Augmentation makes Choice half of the training rows; development and test remain balanced. The 96-row test is small, authored within the same project, and not evidence of broad transfer. The full residual head reduced accuracy from 73/96 to 67/96; bias-only obtained 74/96. The final native 35B model was not trained on these data.

The reusable training workflow accepts user-supplied datasets; its own validation and split controls are documented in [TRAINING.md](TRAINING.md). Sharing a schema does not turn project-generated examples into a suitable training set for every application.

## Recommended reuse and provenance

Use the published data for reproduction, regression, inspecting failure modes, and building new evaluation protocols. Once results or items guide development, use new held-out data for a new performance claim. For research, separate whole families or domains and add independent annotation. Report family counts and annotation methods, not only raw row counts.

The original final JSONL SHA-256 is `9c1309168c407360b22f64af771784a216874ad4b120024b18dc674cc71f04c7`; CSV SHA-256 is `c4b9d4f5b486a7619088d234a7392589a3a6bfbecac43eab8398109a13ba74d3`. Public release logs have local paths redacted; historical freeze hashes describe original bytes. Consult the publication transformation record when comparing logs or source snapshots. The actual question exports contain no local filesystem paths and retain the listed content hashes unless a later dataset version explicitly changes them.

## External pilot added for the working paper

`paper/external_pilot/` records a fixed 300-item, 100-per-class sample of JGLUE JNLI v1.3 public development data. It is Choice-only, externally authored, and not a hidden test or a full benchmark run. The unchanged prompting configuration achieves 243/300 correct. Data provenance, same-sentence overlap, sampling, runtime hashes, before-inference local freeze records, and limits are in the [pilot data and run description](paper/external_pilot/README.md). Original sentences are downloaded outside the source repository and are not redistributed. Dataset-derived selection and result records use **CC BY-SA 4.0**, not the project MIT license; runner/test source remains MIT. Do not combine this pilot with the 2,400-item local suite into a single accuracy claim.

## Expanded external data and matched study for v0.2

The [expanded preparation](paper/external_expanded/README.md) fixes 600 additional public-development examples before model inference. All selected examples have now been evaluated in the completed v0.2 comparison. The [analysis](paper/matched_study/REPORT.md) reports task-specific metrics and full coverage; repeated/multi-mode requests do not increase the number of distinct questions.

| Dataset | Selected examples | Decision type | Evaluation target |
|---|---:|---|---|
| JCoLA | 200: 100 in-domain and 100 out-of-domain | Noul | Binary acceptability; MCC primary, with confusion counts and accuracy |
| JSTS | 200 | Score | Original continuous similarity score in [0,5]; expected-score MAE primary |
| JCommonsenseQA | 200 | Choice | Original correct alternative; accuracy primary |

Selection uses fixed ID-hash ordering within each source file, with no gold balancing or filtering by content, difficulty, length, or model results. JSTS gold scores are not rounded into stage classes: no stage-label accuracy or categorical NLL/Brier is invented for these continuous targets. The generation comparison additionally measures hard-selected-stage MAE, separately from expected-score MAE.

Together with the earlier JNLI pilot, these cover four named public datasets. They do not constitute four independent source populations: JSTS and JNLI share caption/image origins, and the [overlap audit](paper/external_expanded/AUDIT.json) records cross-task dependence. JCoLA source groups and exact-question groups for JCommonsenseQA are limited proxies for further correlations. The dataset names “in-domain” and “out-of-domain” do not establish that either source is unseen by the base model. Pretraining and post-training overlap are unknown.

The [matched study](paper/matched_study/README.md) also selects 150 existing local questions: three from each of 45 generated families and five individually AI-authored items per decision type. It uses five repetitions per local item and one per external item, each under direct readout, one-token constrained decoding, and grammar-constrained JSON generation. Repeated requests are not new semantic examples. The local subset is public regression material; the external samples are public development data. Do not pool their tasks, repetitions, or distinct target types into a common accuracy.

Only IDs, hashes, gold/group metadata, protocols, and derived records are distributed. Source texts and transformed external inference questions stay in a cache outside the repository. Inference receives only `type`, `state`, `instructions`, and `criteria`; labels and provenance are withheld from the model input. Compiled binaries and model weights are separate downloads/builds.

External dataset-derived metadata, selection, audits, predictions, results, and task protocols/rubrics retain **CC BY-SA 4.0**, with JGLUE or JCoLA attribution as applicable. Mixed local/external prediction or selection files carry this data notice; the original local data retain MIT. Preparation, inference, analysis, tests, and build code remain MIT. See [NOTICE.md](NOTICE.md) and the dataset-specific README/license copies for the full boundaries and transformations.
