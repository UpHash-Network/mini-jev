# Independent confirmation review

**PASS:** all raw-logit, source-identity, A metric and B budget-replay checks agree.

Checked 2400 physical records, 240 shared question identities, 64 A point metrics, 40 B policy/budget points, exact selected IDs and unique paid indices, token/time sums, and both primary AP bootstrap intervals.

## qwen2.5-1.5b

Primary A: 52/240 errors; AP difference -0.023666, interval [-0.091868, +0.067304].

| 720-call policy | Correct / 240 | Selected | Input tokens |
|---|---:|---:|---:|
| pair_entropy_tv_rank | 197 | 80 | 229538 |
| pair_mean_entropy | 197 | 80 | 229514 |
| pair_random | 194 | 80 | 229544 |
| first_entropy | 200 | 120 | 229656 |

## qwen3.6-35b-a3b

Primary A: 5/240 errors; AP difference -0.101610, interval [-0.464500, +0.124406].

| 720-call policy | Correct / 240 | Selected | Input tokens |
|---|---:|---:|---:|
| pair_entropy_tv_rank | 235 | 80 | 188640 |
| pair_mean_entropy | 235 | 80 | 188610 |
| pair_random | 235 | 80 | 188586 |
| first_entropy | 235 | 120 | 188210 |

No gold or third-to-fifth-call evidence enters allocation. The second diagnostic call is paid. All measured pools contain five calls per item; smaller reported budgets are replays using a subset, not saved collection costs or an online-speed experiment.

This is an independent implementation within the same AI-assisted project and machine. It establishes numerical agreement and evidence integrity, not independent human validation, causal deployment benefit, or freedom from model-training contamination.
