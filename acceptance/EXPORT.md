> Public-release clarification: “manual”, “handwritten”, “手書き”, and “independent reviewer” in these historical records refer to individual writing/review by separate AI agents, not human expert annotation or external independent evaluation. See [DATA_CARD.md](../DATA_CARD.md) for scope and provenance.

# 検証質問 2,400 問の一括配布

凍結済みの手書き問題 180 問と生成問題 2,220 問を統合した配布用コピーです。元データ、正解、生成器は変更していません。モデルの予測や評価結果を参照せずに作成しました。

## ファイル

- `questions_2400.jsonl`: UTF-8。1 行に 1 問。元ファイルの全フィールドを保持し、必要に応じて `source` と `family` を補っています。監査用の seed、variant、oracle 等も元データに存在すれば保持しています。
- `questions_2400.csv`: UTF-8 BOM 付き。列は `id,type,source,family,state,instructions,criteria,label`。`state` と `criteria` は JSON 文字列です。自然文の `state` も JSON の文字列値として符号化しているため、どちらの形式も JSON パースで元の型へ戻せます。カンマ、引用符、改行は標準 CSV の規則でエスケープされています。

JSONL は完全な監査用記録、CSV は上記 8 列の取り出し用です。並びは手書き 180 問の元順、続いて生成 2,220 問の元順です。`source` は `manual` または `generated`。元の `family` がない場合は `tag` を `family` に複写し、元の `tag` も JSONL に保持しています。

## 件数と検証

| 種別 | 手書き | 生成 | 合計 |
|---|---:|---:|---:|
| Choice | 60 | 740 | 800 |
| Noul | 60 | 740 | 800 |
| Score | 60 | 740 | 800 |
| 合計 | 180 | 2,220 | 2,400 |

2400 件の ID はすべて一意です。JSONL 全フィールドと元正解の一致、JSONL の再読込一致、CSV 全 8 列の型を含む復元一致を確認済みです。元の 2 データファイルと生成器の SHA-256 はコピー作成前後で一致しました。

推論へ渡すのは `type`, `state`, `instructions`, `criteria` のみです。`label` は正解であり、`id`, `source`, `family`, `tag`, `seed`, `variant`, `oracle` 等の監査メタデータとともにモデル入力から除いてください。

## SHA-256

| ファイル | SHA-256 |
|---|---|
| `questions_2400.jsonl` | `ee5e5d595470f262f346f8ae551a06decdad9743dcd51aed5364b65037fda234` |
| `questions_2400.csv` | `f1c1c1edbbc29a8a52a12ad93a8935a43da9b08029d40ce0bdb27ffe9d0a9ea5` |
| 元 `private/acceptance_test.jsonl` | `16436f5e31f092f79ec3d4f39530ccd15521bf092539a9d21195e2059a7840bd` |
| 元 `private/generated_2220.jsonl` | `141ee4c379fa8d72df6bca3fe793054c9d2847ca7d16d2fa6622bc92558d4bb3` |
| 元 `make_generated_eval.py` | `a210e973782264cd14371501a248488fb8c39db51be05e0fe8b94b2907aadc69` |

これらは試験用質問のエクスポートであり、予測や精度集計は含みません。
