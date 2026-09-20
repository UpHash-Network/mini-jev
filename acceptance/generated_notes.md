> Public-release clarification: “manual”, “handwritten”, “手書き”, and “independent reviewer” in these historical records refer to individual writing/review by separate AI agents, not human expert annotation or external independent evaluation. See [DATA_CARD.md](../DATA_CARD.md) for scope and provenance.

# Generated blind acceptance block

Created by `make_generated_eval.py`; master seed `202609200731`.

- Total: 2,220; Choice 740, Noul 740, Score 740.
- Fifteen families per type, 45 total; each family has 49 or 50 cases.
- Each family uses three natural-language question templates and a mixture of natural text and JSON state.
- Choice and Score have 2–8 candidates; Noul has exactly two. Noul truth labels are exactly 370/370. For each candidate count, Choice and Score answer positions differ by at most one case.
- Only `type`, `state`, `instructions`, and `criteria` are inference inputs. IDs, answers, sources, families, seeds, variants, and oracle records must not enter prompts.
- Every answer comes from the executable `solve` oracle applied to recorded facts; no external factual knowledge is required. Oracle facts and explanations are audit metadata.
- Exact-input duplicates: 0. Canonical oracle-fact duplicates: 0. Generation rejected 191 duplicate attempts, including variants that changed only wording or irrelevant names. Unordered record lists and set-like lists are normalized before semantic deduplication.
- In addition to all-case schema, range, truth-balance, uniqueness, template, and answer checks, 54 independently specified oracle test examples passed. The tests include strict/inclusive boundaries, exceptions, latest-record precedence, negation, end-to-start schedules, and weighted-score caps.
- Candidate insertion-order permutations preserve semantic answer keys and descriptions. Score criteria are ordered scales and are deliberately not reordered. Dataset permutation preserves every ID/answer pair.
- Deterministic byte-for-byte second generation checked: True.
- This is a generated behavioral acceptance suite, not a sample of real user traffic. Repeated families and synthetic rubrics mean that overall accuracy measures these documented tasks, not general intelligence or calibration under distribution shift.
- The generator never reads previous training/evaluation data, the manual block, or model outputs. No inference or tuning was performed while creating this block.

SHA-256 of `private/generated_2220.jsonl`: `141ee4c379fa8d72df6bca3fe793054c9d2847ca7d16d2fa6622bc92558d4bb3`.

Detailed counts and candidate-position histograms are in `private/generated_stats.json`.
