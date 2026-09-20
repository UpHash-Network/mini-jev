> Public-release clarification: “manual”, “handwritten”, “手書き”, and “independent reviewer” in these historical records refer to individual writing/review by separate AI agents, not human expert annotation or external independent evaluation. See [DATA_CARD.md](DATA_CARD.md) for scope and provenance.

# Mini Jev 開発状況

2026年9月20日。定めた簡易版の完成基準を満たしました。

新規2,400問の最終試験は正答率93.25%、Choice96.00%、Noul95.25%、Score88.50%。独立手書き180問は95.56%でした。入力512トークン以下2,291問の単問p95は379.1msです。型・確率・範囲は全件正常、Choiceの候補順変更800件も意味ラベルが一致しました。

数値監査434項目、Score境界4問に関する93項目、実モデル2回の再起動とSDK/HTTP一致を確認しました。出力ヘッド追加学習は採用せず、凍結したQwen3.6-35B-A3B Q4_K_Mの出力を判断値として使います。

- [起動方法と実装の説明](README.md)
- [検証問題 CSV 2,400問](acceptance-v2/questions_2400.csv)
- [検証問題 JSONL 2,400問](acceptance-v2/questions_2400.jsonl)
- [最終試験の全結果](results/native-acceptance/REPORT.md)
- [数値・API・運用の検証記録](VALIDATION.md)

旧4Bの不合格結果や、小型モデルの追加学習実験も履歴として残しています。試験は限定された課題群を対象としており、本家Jevと同じ性能や任意の業務での精度を保証するものではありません。
