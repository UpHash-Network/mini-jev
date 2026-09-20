# 出力ヘッド学習用の合成データ

生成seed: `20260920`。生成器: `make_training_data.py`。

このデータは日本語の明示ルール適用を人工的に構成したものです。実業務データでも、独立評価データでもありません。既存の eval_ja.jsonl は生成・設計・検証で読んでいません。

## 分割と用途

- train: 768件、出力ヘッドの学習専用。
- dev: 192件、学習条件・停止時点の選択専用。
- calibration: 192件、選択完了後の温度等の校正専用。精度の最終評価には使用しない。
- 各分割はChoice/Noul/Scoreが均等。各型8 family、各familyはtrain32件/dev8件/calibration8件。

各familyは6つの意味設定グループを持ち、業務対象・語彙・規則の数値設定を群ごとに固定します。g00〜g03をtrain、g04をdev、g05をcalibrationへ割り当て、同一群の8例は分割しません。trainは部品倉庫・図書室・生花店・料理教室、devは観測所、calibrationは舞台設備室です。familyのアルゴリズム構造は共有しており、これは同一テンプレート族内の語彙・設定への一般化を確認する分割です。未知の推論構造への一般化を保証しません。

各例の正解は明記された数値・条件から算出します。Choiceの候補順はseed付きで変更し、候補数ごとに正解表示位置を均等化。Scoreの基準は低段階から高段階の順を保持し、候補数ごとに正解段階を均等化。Noulは真偽が同数で、否定形の質問も含みます。

状態に正解キー・正解説明を単独で埋め込む方式は使いません。表の照合・時刻比較・最小費用では対象名が全候補について状態にも現れます。正解が文字列一致だけで決まる例や算術中心の例も含む、限定的な合成タスクです。

Choiceの候補順を無視した全入力の重複検査、ID重複検査、群の分割重複検査、型とfamilyの件数検査、正解位置・真偽の均等性検査を生成時に実施します。model/tokenizerの実行は行いません。入力長の上限は特徴抽出側で確認してください。

## ファイル整合性

```json
{
  "head_train.jsonl": "67eb9f0d60b9b71a9f75ef77fffc52fca5584b78f82b2b0a9bc0e985a552ebc9",
  "head_dev.jsonl": "067753f3d0899467f2c1b661d668638901c7a0cde84153aacedb30e0c11a27f0",
  "head_calibration.jsonl": "8670a2604752fede8d828cbc506a48459e6234037746bd5e828d2a8a4d98589b"
}
```

## 検証集計

```json
{
  "train": {
    "count": 768,
    "by_type": {
      "noul": 256,
      "choice": 256,
      "score": 256
    },
    "by_family": {
      "choice/boolean_pattern": 32,
      "choice/latest_event": 32,
      "choice/minimum_cost": 32,
      "choice/numeric_band": 32,
      "choice/priority_rule": 32,
      "choice/rule_count": 32,
      "choice/stock_decision": 32,
      "choice/symbol_mapping": 32,
      "noul/all_conditions": 32,
      "noul/any_condition": 32,
      "noul/closed_interval": 32,
      "noul/exact_count": 32,
      "noul/quantity_comparison": 32,
      "noul/quota_rule": 32,
      "noul/state_transition": 32,
      "noul/veto_rule": 32,
      "score/completed_count": 32,
      "score/completion_ratio": 32,
      "score/consecutive_checks": 32,
      "score/maximum_risk": 32,
      "score/numeric_band": 32,
      "score/shortage_level": 32,
      "score/violation_count": 32,
      "score/weighted_points": 32
    },
    "answer_positions_by_candidate_count": {
      "choice/2": {
        "0": 24,
        "1": 24
      },
      "choice/3": {
        "0": 16,
        "1": 16,
        "2": 16
      },
      "choice/4": {
        "0": 14,
        "1": 14,
        "2": 14,
        "3": 14
      },
      "choice/5": {
        "0": 12,
        "1": 11,
        "2": 11,
        "3": 11,
        "4": 11
      },
      "choice/6": {
        "0": 8,
        "1": 8,
        "2": 8,
        "3": 8,
        "4": 8,
        "5": 8
      },
      "score/3": {
        "0": 22,
        "1": 21,
        "2": 21
      },
      "score/4": {
        "0": 16,
        "1": 16,
        "2": 16,
        "3": 16
      },
      "score/5": {
        "0": 13,
        "1": 13,
        "2": 13,
        "3": 13,
        "4": 12
      },
      "score/6": {
        "0": 11,
        "1": 11,
        "2": 11,
        "3": 11,
        "4": 10,
        "5": 10
      }
    },
    "noul_labels": {
      "false": 128,
      "true": 128
    },
    "semantic_group_count": 96
  },
  "dev": {
    "count": 192,
    "by_type": {
      "score": 64,
      "noul": 64,
      "choice": 64
    },
    "by_family": {
      "choice/boolean_pattern": 8,
      "choice/latest_event": 8,
      "choice/minimum_cost": 8,
      "choice/numeric_band": 8,
      "choice/priority_rule": 8,
      "choice/rule_count": 8,
      "choice/stock_decision": 8,
      "choice/symbol_mapping": 8,
      "noul/all_conditions": 8,
      "noul/any_condition": 8,
      "noul/closed_interval": 8,
      "noul/exact_count": 8,
      "noul/quantity_comparison": 8,
      "noul/quota_rule": 8,
      "noul/state_transition": 8,
      "noul/veto_rule": 8,
      "score/completed_count": 8,
      "score/completion_ratio": 8,
      "score/consecutive_checks": 8,
      "score/maximum_risk": 8,
      "score/numeric_band": 8,
      "score/shortage_level": 8,
      "score/violation_count": 8,
      "score/weighted_points": 8
    },
    "answer_positions_by_candidate_count": {
      "choice/2": {
        "0": 8,
        "1": 8
      },
      "choice/3": {
        "0": 6,
        "1": 5,
        "2": 5
      },
      "choice/4": {
        "0": 2,
        "1": 2,
        "2": 2,
        "3": 2
      },
      "choice/5": {
        "0": 2,
        "1": 2,
        "2": 2,
        "3": 1,
        "4": 1
      },
      "choice/6": {
        "0": 3,
        "1": 3,
        "2": 3,
        "3": 3,
        "4": 2,
        "5": 2
      },
      "score/3": {
        "0": 6,
        "1": 5,
        "2": 5
      },
      "score/4": {
        "0": 4,
        "1": 4,
        "2": 4,
        "3": 4
      },
      "score/5": {
        "0": 4,
        "1": 3,
        "2": 3,
        "3": 3,
        "4": 3
      },
      "score/6": {
        "0": 3,
        "1": 3,
        "2": 3,
        "3": 3,
        "4": 2,
        "5": 2
      }
    },
    "noul_labels": {
      "false": 32,
      "true": 32
    },
    "semantic_group_count": 24
  },
  "calibration": {
    "count": 192,
    "by_type": {
      "score": 64,
      "noul": 64,
      "choice": 64
    },
    "by_family": {
      "choice/boolean_pattern": 8,
      "choice/latest_event": 8,
      "choice/minimum_cost": 8,
      "choice/numeric_band": 8,
      "choice/priority_rule": 8,
      "choice/rule_count": 8,
      "choice/stock_decision": 8,
      "choice/symbol_mapping": 8,
      "noul/all_conditions": 8,
      "noul/any_condition": 8,
      "noul/closed_interval": 8,
      "noul/exact_count": 8,
      "noul/quantity_comparison": 8,
      "noul/quota_rule": 8,
      "noul/state_transition": 8,
      "noul/veto_rule": 8,
      "score/completed_count": 8,
      "score/completion_ratio": 8,
      "score/consecutive_checks": 8,
      "score/maximum_risk": 8,
      "score/numeric_band": 8,
      "score/shortage_level": 8,
      "score/violation_count": 8,
      "score/weighted_points": 8
    },
    "answer_positions_by_candidate_count": {
      "choice/2": {
        "0": 8,
        "1": 8
      },
      "choice/3": {
        "0": 6,
        "1": 5,
        "2": 5
      },
      "choice/4": {
        "0": 4,
        "1": 4,
        "2": 4,
        "3": 4
      },
      "choice/5": {
        "0": 2,
        "1": 2,
        "2": 2,
        "3": 1,
        "4": 1
      },
      "choice/6": {
        "0": 2,
        "1": 2,
        "2": 1,
        "3": 1,
        "4": 1,
        "5": 1
      },
      "score/3": {
        "0": 6,
        "1": 5,
        "2": 5
      },
      "score/4": {
        "0": 4,
        "1": 4,
        "2": 4,
        "3": 4
      },
      "score/5": {
        "0": 4,
        "1": 3,
        "2": 3,
        "3": 3,
        "4": 3
      },
      "score/6": {
        "0": 3,
        "1": 3,
        "2": 3,
        "3": 3,
        "4": 2,
        "5": 2
      }
    },
    "noul_labels": {
      "false": 32,
      "true": 32
    },
    "semantic_group_count": 24
  },
  "checks": {
    "unique_ids": 1152,
    "unique_inputs_ignoring_choice_order": 1152,
    "cross_split_duplicate_inputs": 0,
    "cross_split_shared_semantic_groups": 0,
    "families_per_type": 8,
    "position_count_max_gap_within_each_candidate_count": 1,
    "source_eval_files_read": false
  }
}
```

## 意味設定グループ

```json
{
  "train": [
    "choice/numeric_band/g00",
    "choice/numeric_band/g01",
    "choice/numeric_band/g02",
    "choice/numeric_band/g03",
    "choice/priority_rule/g00",
    "choice/priority_rule/g01",
    "choice/priority_rule/g02",
    "choice/priority_rule/g03",
    "choice/boolean_pattern/g00",
    "choice/boolean_pattern/g01",
    "choice/boolean_pattern/g02",
    "choice/boolean_pattern/g03",
    "choice/minimum_cost/g00",
    "choice/minimum_cost/g01",
    "choice/minimum_cost/g02",
    "choice/minimum_cost/g03",
    "choice/latest_event/g00",
    "choice/latest_event/g01",
    "choice/latest_event/g02",
    "choice/latest_event/g03",
    "choice/stock_decision/g00",
    "choice/stock_decision/g01",
    "choice/stock_decision/g02",
    "choice/stock_decision/g03",
    "choice/symbol_mapping/g00",
    "choice/symbol_mapping/g01",
    "choice/symbol_mapping/g02",
    "choice/symbol_mapping/g03",
    "choice/rule_count/g00",
    "choice/rule_count/g01",
    "choice/rule_count/g02",
    "choice/rule_count/g03",
    "noul/all_conditions/g00",
    "noul/all_conditions/g01",
    "noul/all_conditions/g02",
    "noul/all_conditions/g03",
    "noul/any_condition/g00",
    "noul/any_condition/g01",
    "noul/any_condition/g02",
    "noul/any_condition/g03",
    "noul/veto_rule/g00",
    "noul/veto_rule/g01",
    "noul/veto_rule/g02",
    "noul/veto_rule/g03",
    "noul/closed_interval/g00",
    "noul/closed_interval/g01",
    "noul/closed_interval/g02",
    "noul/closed_interval/g03",
    "noul/quantity_comparison/g00",
    "noul/quantity_comparison/g01",
    "noul/quantity_comparison/g02",
    "noul/quantity_comparison/g03",
    "noul/quota_rule/g00",
    "noul/quota_rule/g01",
    "noul/quota_rule/g02",
    "noul/quota_rule/g03",
    "noul/state_transition/g00",
    "noul/state_transition/g01",
    "noul/state_transition/g02",
    "noul/state_transition/g03",
    "noul/exact_count/g00",
    "noul/exact_count/g01",
    "noul/exact_count/g02",
    "noul/exact_count/g03",
    "score/completed_count/g00",
    "score/completed_count/g01",
    "score/completed_count/g02",
    "score/completed_count/g03",
    "score/numeric_band/g00",
    "score/numeric_band/g01",
    "score/numeric_band/g02",
    "score/numeric_band/g03",
    "score/shortage_level/g00",
    "score/shortage_level/g01",
    "score/shortage_level/g02",
    "score/shortage_level/g03",
    "score/weighted_points/g00",
    "score/weighted_points/g01",
    "score/weighted_points/g02",
    "score/weighted_points/g03",
    "score/completion_ratio/g00",
    "score/completion_ratio/g01",
    "score/completion_ratio/g02",
    "score/completion_ratio/g03",
    "score/maximum_risk/g00",
    "score/maximum_risk/g01",
    "score/maximum_risk/g02",
    "score/maximum_risk/g03",
    "score/violation_count/g00",
    "score/violation_count/g01",
    "score/violation_count/g02",
    "score/violation_count/g03",
    "score/consecutive_checks/g00",
    "score/consecutive_checks/g01",
    "score/consecutive_checks/g02",
    "score/consecutive_checks/g03"
  ],
  "dev": [
    "choice/numeric_band/g04",
    "choice/priority_rule/g04",
    "choice/boolean_pattern/g04",
    "choice/minimum_cost/g04",
    "choice/latest_event/g04",
    "choice/stock_decision/g04",
    "choice/symbol_mapping/g04",
    "choice/rule_count/g04",
    "noul/all_conditions/g04",
    "noul/any_condition/g04",
    "noul/veto_rule/g04",
    "noul/closed_interval/g04",
    "noul/quantity_comparison/g04",
    "noul/quota_rule/g04",
    "noul/state_transition/g04",
    "noul/exact_count/g04",
    "score/completed_count/g04",
    "score/numeric_band/g04",
    "score/shortage_level/g04",
    "score/weighted_points/g04",
    "score/completion_ratio/g04",
    "score/maximum_risk/g04",
    "score/violation_count/g04",
    "score/consecutive_checks/g04"
  ],
  "calibration": [
    "choice/numeric_band/g05",
    "choice/priority_rule/g05",
    "choice/boolean_pattern/g05",
    "choice/minimum_cost/g05",
    "choice/latest_event/g05",
    "choice/stock_decision/g05",
    "choice/symbol_mapping/g05",
    "choice/rule_count/g05",
    "noul/all_conditions/g05",
    "noul/any_condition/g05",
    "noul/veto_rule/g05",
    "noul/closed_interval/g05",
    "noul/quantity_comparison/g05",
    "noul/quota_rule/g05",
    "noul/state_transition/g05",
    "noul/exact_count/g05",
    "score/completed_count/g05",
    "score/numeric_band/g05",
    "score/shortage_level/g05",
    "score/weighted_points/g05",
    "score/completion_ratio/g05",
    "score/maximum_risk/g05",
    "score/violation_count/g05",
    "score/consecutive_checks/g05"
  ]
}
```
