> Public-release clarification: “manual”, “handwritten”, “手書き”, and “independent reviewer” in these historical records refer to individual writing/review by separate AI agents, not human expert annotation or external independent evaluation. See [DATA_CARD.md](../../DATA_CARD.md) for scope and provenance.

# 独立受入評価: 合格

全体 2238/2400 (93.25%).

| 区分 | 正解 | 正解率 |
|---|---:|---:|
| 全体 | 2238/2400 | 93.25% |
| choice | 768/800 | 96.00% |
| noul | 762/800 | 95.25% |
| score | 708/800 | 88.50% |
| 手書き180問 | 172/180 | 95.56% |
| 手書き choice | 56/60 | 93.33% |
| 手書き noul | 59/60 | 98.33% |
| 手書き score | 57/60 | 95.00% |

## 事前の基準との照合

| 基準 | 結果 |
|---|---|
| counts_2400_800_each | PASS |
| overall_accuracy_ge_90pct | PASS |
| each_type_accuracy_ge_85pct | PASS |
| manual_180_accuracy_ge_90pct | PASS |
| manual_each_type_accuracy_ge_85pct | PASS |
| choice_order_semantic_consistency_ge_90pct | PASS |
| all_answers_type_valid | PASS |
| latency_le_512_p95_le_500ms | PASS |
| target_hardware_m5_pro_64gb_metal | PASS |
| every_measured_call_executed_one_llama_decode | PASS |

## 実行条件と速度

- モデル: ggml-org/Qwen3.6-35B-A3B-GGUF
- revision: `baec3ebee244827cda0f4557eafa8b28f7545fa6`
- 実行: metal / Q4_K_M / llama.cpp_flash
- prompt: repeat_typed_score, temperature: 1.34896
- 512 token以下 2291件: p50 282.7ms, p95 379.1ms, 最大 423.4ms
- 512 token超 109件: p50 441.9ms, p95 521.8ms
- 実際のllama_decode API呼び出し: 3207回。単問評価2400＋Choice逆順800＋公開warmup7。
- Choice順序変更時の意味ラベル一致: 800/800。

Choice辞書は実装でキー順を正規化しています。この一致率はモデル固有の順序不変性を証明するものではありません。
遅延はモデル常駐・単問・実forwardの値であり、特徴キャッシュは使いません。入力トークン数はテンプレートと再読部分を含む完全な入力です。複数質問のHTTP所要時間とは別です。llama_decode呼び出し回数はGPUカーネル数を表しません。

## 確率・段階期待値の評価

| 指標 | 温度適用前 | 温度適用後 |
|---|---:|---:|
| nll | 0.188423 | 0.187871 |
| brier_multiclass_sum | 0.097261 | 0.096260 |
| ece_10_equal_width | 0.014863 | 0.015198 |
| score_expectation_mae | 0.169401 | 0.195121 |
| score_normalized_expectation_mae | 0.044948 | 0.051964 |

温度は独立の校正120問で選びました。今回の成績は別分布や実利用での校正を保証しません。Scoreの正解率は最尤段階、MAEは段階番号の期待値について計算しています。

## 課題群ごとの正解率

全familyの単純平均: 94.92%。生成familyの単純平均: 93.02%。

| family | 正解 | 正解率 |
|---|---:|---:|
| generated:いずれかの条件 | 50/50 | 100.00% |
| generated:不在時の代理 | 40/49 | 81.63% |
| generated:不足の段階 | 44/49 | 89.80% |
| generated:予定時間の重なり | 46/49 | 93.88% |
| generated:事実と否定質問 | 50/50 | 100.00% |
| generated:二属性照合 | 49/49 | 100.00% |
| generated:件数の段階境界 | 50/50 | 100.00% |
| generated:例外による上限 | 42/49 | 85.71% |
| generated:例外の優先 | 49/50 | 98.00% |
| generated:全条件の充足 | 50/50 | 100.00% |
| generated:出来事の前後関係 | 48/49 | 97.96% |
| generated:利用可能集合の差 | 49/49 | 100.00% |
| generated:参照先の担当 | 49/50 | 98.00% |
| generated:参照表の順序尺度 | 48/49 | 97.96% |
| generated:参照関係の真偽 | 45/49 | 91.84% |
| generated:取消しを反映した件数 | 33/49 | 67.35% |
| generated:否定条件で選択 | 50/50 | 100.00% |
| generated:問い合わせ経路 | 50/50 | 100.00% |
| generated:小数量の比較 | 44/49 | 89.80% |
| generated:工程の依存順 | 49/49 | 100.00% |
| generated:改訂と例外の優先 | 49/49 | 100.00% |
| generated:文章内の順序参照 | 49/49 | 100.00% |
| generated:時刻順の評価更新 | 44/49 | 89.80% |
| generated:時間枠の包含 | 45/49 | 91.84% |
| generated:更新後の状態 | 45/49 | 91.84% |
| generated:最終更新 | 46/50 | 92.00% |
| generated:条件と優先例外 | 50/50 | 100.00% |
| generated:条件付き不足書類 | 44/49 | 89.80% |
| generated:条件付き義務 | 31/49 | 63.27% |
| generated:独立チェックの合計 | 48/50 | 96.00% |
| generated:目標からの差 | 40/49 | 81.63% |
| generated:範囲の開閉境界 | 49/49 | 100.00% |
| generated:約束時刻からの遅れ | 29/49 | 59.18% |
| generated:緊急条件の加点 | 48/50 | 96.00% |
| generated:締切の境界 | 50/50 | 100.00% |
| generated:複数属性の制約 | 49/49 | 100.00% |
| generated:要件への一致数 | 44/49 | 89.80% |
| generated:記述の満足段階 | 50/50 | 100.00% |
| generated:記録と主張の照合 | 49/49 | 100.00% |
| generated:証拠の最高到達段階 | 43/49 | 87.76% |
| generated:識別文字列の完全一致 | 49/49 | 100.00% |
| generated:軽重のある項目 | 38/49 | 77.55% |
| generated:重複を除いた件数 | 43/49 | 87.76% |
| generated:集合と否定所属 | 49/49 | 100.00% |
| generated:順番に進む工程 | 50/50 | 100.00% |
| manual:arithmetic | 10/17 | 58.82% |
| manual:boundary | 9/9 | 100.00% |
| manual:comparison | 5/5 | 100.00% |
| manual:conditional | 4/4 | 100.00% |
| manual:conjunction | 6/6 | 100.00% |
| manual:contrast | 2/2 | 100.00% |
| manual:count | 12/12 | 100.00% |
| manual:disjunction | 3/3 | 100.00% |
| manual:distractor | 1/1 | 100.00% |
| manual:entailment | 2/2 | 100.00% |
| manual:exact_match | 1/1 | 100.00% |
| manual:exception | 4/4 | 100.00% |
| manual:extraction | 6/6 | 100.00% |
| manual:history | 19/19 | 100.00% |
| manual:insufficient | 11/11 | 100.00% |
| manual:intersection | 1/1 | 100.00% |
| manual:meaning | 20/20 | 100.00% |
| manual:negation | 12/12 | 100.00% |
| manual:permission | 2/2 | 100.00% |
| manual:priority | 7/7 | 100.00% |
| manual:quotation | 1/1 | 100.00% |
| manual:range | 4/4 | 100.00% |
| manual:scope | 17/18 | 94.44% |
| manual:sentiment | 5/5 | 100.00% |
| manual:sequence | 3/3 | 100.00% |
| manual:temporal | 5/5 | 100.00% |

## 評価の範囲

手書き180問＋生成2220問の限定された日本語の受入試験です。生成例は同じ課題・テンプレートを共有し、互いに独立な実利用例2400件を意味しません。一般的な判断能力や本家Jevと同等の品質は主張しません。
このファイルは凍結した結果から作成しています。全予測は [predictions.jsonl](predictions.jsonl)、集計は [summary.json](summary.json)、設定とハッシュは [freeze.json](freeze.json) にあります。

評価基準を満たしました。API・再起動・SDK・数値検証は別の結果で確認します。
