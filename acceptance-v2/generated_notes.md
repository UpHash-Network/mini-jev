> Public-release clarification: “manual”, “handwritten”, “手書き”, and “independent reviewer” in these historical records refer to individual writing/review by separate AI agents, not human expert annotation or external independent evaluation. See [DATA_CARD.md](../DATA_CARD.md) for scope and provenance.

# Generated blind acceptance block — version 2

Created by `make_generated_eval.py`; master seed `202609201731`.

- Total: 2,220; Choice 740, Noul 740, Score 740.
- Fifteen families per type, 45 total; each family has 49 or 50 cases.
- Each family uses three natural-language question templates and a mixture of natural text and JSON state.
- Choice and Score have 2–8 candidates; Noul has exactly two. Noul truth labels are exactly 370/370. For each candidate count, Choice and Score answer positions differ by at most one case.
- Only `type`, `state`, `instructions`, and `criteria` are inference inputs. IDs, answers, sources, families, seeds, variants, and oracle records must not enter prompts.
- Every answer comes from the executable `solve` oracle applied to recorded facts; no external factual knowledge is required. Oracle facts and explanations are audit metadata.
- Exact-input duplicates: 0. Canonical oracle-fact duplicates: 0. Generation rejected 457 duplicate attempts, including variants that changed only wording or irrelevant names. Unordered record lists and set-like lists are normalized before semantic deduplication.
- In addition to all-case schema, range, truth-balance, uniqueness, template, and answer checks, 54 independently specified oracle test examples passed. The tests include strict/inclusive boundaries, exceptions, latest-record precedence, negation, end-to-start schedules, and weighted-score caps.
- Candidate insertion-order permutations preserve semantic answer keys and descriptions. Score criteria are ordered scales and are deliberately not reordered. Dataset permutation preserves every ID/answer pair.
- Deterministic byte-for-byte second generation checked: True.
- This is a generated behavioral acceptance suite, not a sample of real user traffic. Repeated families and synthetic rubrics mean that overall accuracy measures these documented tasks, not general intelligence or calibration under distribution shift.
- This generator reads the frozen v1 generated block only to exclude all exact inputs and canonical oracle-fact identities. It never reads model outputs, manual/calibration blocks, or training data. No inference or tuning is performed here.
- V1 exact-input overlap: 0. V1 canonical semantic overlap: 0. V1 baseline file SHA-256: `141ee4c379fa8d72df6bca3fe793054c9d2847ca7d16d2fa6622bc92558d4bb3`.
- Finite predicate/scale pools were expanded in nine families without changing per-question logical operators, condition counts, or candidate counts: routing categories, action vocabulary, all/any predicates, checklist attributes, workflow steps, evidence types, satisfaction scale vocabulary, and integer threshold spacing. Required-document sets and redundant scan entries receive stricter order/multiplicity normalization for exclusion.
- Choice answers are balanced within one count at every candidate count after canonical sorting of keys, matching the actual inference prompt. Each case keeps the candidate cardinality from its first draw, preventing positional rejection from favoring small/easy candidate sets. Score positions are also balanced within one. V1 is unchanged; its insertion-order balance should not be interpreted as canonical prompt-position balance.

SHA-256 of `private/generated_2220.jsonl`: `791bd3f43c1f6e01b960ff961c50aacf83da64a23fa7b8292378c529c76a04d9`.

Detailed counts and candidate-position histograms are in `private/generated_stats.json`.
