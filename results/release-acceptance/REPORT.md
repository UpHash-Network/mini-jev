> Public-release clarification: “manual”, “handwritten”, “手書き”, and “independent reviewer” in these historical records refer to individual writing/review by separate AI agents, not human expert annotation or external independent evaluation. See [DATA_CARD.md](../../DATA_CARD.md) for scope and provenance.

# 独立受入評価: 不合格

全体 1713/2400 (71.38%).

| 区分 | 正解 | 正解率 |
|---|---:|---:|
| 全体 | 1713/2400 | 71.38% |
| choice | 619/800 | 77.38% |
| noul | 604/800 | 75.50% |
| score | 490/800 | 61.25% |
| 手書き180問 | 160/180 | 88.89% |
| 手書き choice | 52/60 | 86.67% |
| 手書き noul | 53/60 | 88.33% |
| 手書き score | 55/60 | 91.67% |

## 事前の基準との照合

| 基準 | 結果 |
|---|---|
| counts_2400_800_each | PASS |
| overall_accuracy_ge_90pct | FAIL |
| each_type_accuracy_ge_85pct | FAIL |
| manual_180_accuracy_ge_90pct | FAIL |
| manual_each_type_accuracy_ge_85pct | PASS |
| choice_order_semantic_consistency_ge_90pct | PASS |
| all_answers_type_valid | PASS |
| latency_le_512_p95_le_500ms | FAIL |
| target_hardware_m5_pro_64gb_mps | PASS |
| every_measured_call_executed_one_backbone_forward | PASS |

## 実行条件と速度

- モデル: Qwen/Qwen3-4B-Instruct-2507
- revision: `cdbee75f17c01a7cc42f958dc650907174af0554`
- 実行: mps / torch.float32 / eager
- prompt: compact, temperature: 6.30957
- 512 token以下 2400件: p50 337.6ms, p95 518.8ms, 最大 868.2ms
- 512 token超 0件: p50 対象なし, p95 対象なし
- 実際の本体計算: 3207回。単問評価2400＋Choice逆順800＋公開warmup7。
- Choice順序変更時の意味ラベル一致: 800/800。

Choice辞書は実装でキー順を正規化しています。この一致率はモデル固有の順序不変性を証明するものではありません。
遅延はモデル常駐・単問・実forwardの値であり、特徴キャッシュは使いません。複数質問のHTTP所要時間とは別です。

## 確率・段階期待値の評価

| 指標 | 温度適用前 | 温度適用後 |
|---|---:|---:|
| nll | 3.578349 | 0.805052 |
| brier_multiclass_sum | 0.544099 | 0.419935 |
| ece_10_equal_width | 0.263272 | 0.105914 |
| score_expectation_mae | 0.748987 | 0.742614 |
| score_normalized_expectation_mae | 0.185011 | 0.189359 |

温度は独立の校正120問で選びました。今回の成績は別分布や実利用での校正を保証しません。Scoreの正解率は最尤段階、MAEは段階番号の期待値について計算しています。

## 課題群ごとの正解率

全familyの単純平均: 78.40%。生成familyの単純平均: 69.88%。

| family | 正解 | 正解率 |
|---|---:|---:|
| generated:いずれかの条件 | 50/50 | 100.00% |
| generated:不在時の代理 | 24/49 | 48.98% |
| generated:不足の段階 | 20/49 | 40.82% |
| generated:予定時間の重なり | 24/49 | 48.98% |
| generated:事実と否定質問 | 47/50 | 94.00% |
| generated:二属性照合 | 47/49 | 95.92% |
| generated:件数の段階境界 | 41/50 | 82.00% |
| generated:例外による上限 | 26/49 | 53.06% |
| generated:例外の優先 | 38/50 | 76.00% |
| generated:全条件の充足 | 47/50 | 94.00% |
| generated:出来事の前後関係 | 35/49 | 71.43% |
| generated:利用可能集合の差 | 47/49 | 95.92% |
| generated:参照先の担当 | 36/50 | 72.00% |
| generated:参照表の順序尺度 | 44/49 | 89.80% |
| generated:参照関係の真偽 | 27/49 | 55.10% |
| generated:取消しを反映した件数 | 12/49 | 24.49% |
| generated:否定条件で選択 | 41/50 | 82.00% |
| generated:問い合わせ経路 | 49/50 | 98.00% |
| generated:小数量の比較 | 26/49 | 53.06% |
| generated:工程の依存順 | 41/49 | 83.67% |
| generated:改訂と例外の優先 | 32/49 | 65.31% |
| generated:文章内の順序参照 | 43/49 | 87.76% |
| generated:時刻順の評価更新 | 30/49 | 61.22% |
| generated:時間枠の包含 | 23/49 | 46.94% |
| generated:更新後の状態 | 35/49 | 71.43% |
| generated:最終更新 | 29/50 | 58.00% |
| generated:条件と優先例外 | 50/50 | 100.00% |
| generated:条件付き不足書類 | 32/49 | 65.31% |
| generated:条件付き義務 | 23/49 | 46.94% |
| generated:独立チェックの合計 | 30/50 | 60.00% |
| generated:目標からの差 | 21/49 | 42.86% |
| generated:範囲の開閉境界 | 49/49 | 100.00% |
| generated:約束時刻からの遅れ | 17/49 | 34.69% |
| generated:緊急条件の加点 | 26/50 | 52.00% |
| generated:締切の境界 | 33/50 | 66.00% |
| generated:複数属性の制約 | 47/49 | 95.92% |
| generated:要件への一致数 | 18/49 | 36.73% |
| generated:記述の満足段階 | 44/50 | 88.00% |
| generated:記録と主張の照合 | 48/49 | 97.96% |
| generated:証拠の最高到達段階 | 28/49 | 57.14% |
| generated:識別文字列の完全一致 | 32/49 | 65.31% |
| generated:軽重のある項目 | 29/49 | 59.18% |
| generated:重複を除いた件数 | 27/49 | 55.10% |
| generated:集合と否定所属 | 36/49 | 73.47% |
| generated:順番に進む工程 | 49/50 | 98.00% |
| manual:arithmetic | 10/17 | 58.82% |
| manual:boundary | 7/9 | 77.78% |
| manual:comparison | 5/5 | 100.00% |
| manual:conditional | 4/4 | 100.00% |
| manual:conjunction | 6/6 | 100.00% |
| manual:contrast | 2/2 | 100.00% |
| manual:count | 11/12 | 91.67% |
| manual:disjunction | 3/3 | 100.00% |
| manual:distractor | 1/1 | 100.00% |
| manual:entailment | 2/2 | 100.00% |
| manual:exact_match | 1/1 | 100.00% |
| manual:exception | 3/4 | 75.00% |
| manual:extraction | 5/6 | 83.33% |
| manual:history | 16/19 | 84.21% |
| manual:insufficient | 10/11 | 90.91% |
| manual:intersection | 1/1 | 100.00% |
| manual:meaning | 20/20 | 100.00% |
| manual:negation | 12/12 | 100.00% |
| manual:permission | 2/2 | 100.00% |
| manual:priority | 5/7 | 71.43% |
| manual:quotation | 1/1 | 100.00% |
| manual:range | 4/4 | 100.00% |
| manual:scope | 16/18 | 88.89% |
| manual:sentiment | 5/5 | 100.00% |
| manual:sequence | 3/3 | 100.00% |
| manual:temporal | 5/5 | 100.00% |

## 評価の範囲

手書き180問＋生成2220問の限定された日本語の受入試験です。生成例は同じ課題・テンプレートを共有し、互いに独立な実利用例2400件を意味しません。一般的な判断能力や本家Jevと同等の品質は主張しません。
このファイルは凍結した結果から作成しています。全予測は [predictions.jsonl](predictions.jsonl)、集計は [summary.json](summary.json)、設定とハッシュは [freeze.json](freeze.json) にあります。

この設定では完成基準に未達です。この問題群は以後の開発・回帰用とし、改善版の最終受入には新規問題を用います。
