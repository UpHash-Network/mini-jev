> Public-release clarification: “manual”, “handwritten”, “手書き”, and “independent reviewer” in these historical records refer to individual writing/review by separate AI agents, not human expert annotation or external independent evaluation. See [DATA_CARD.md](DATA_CARD.md) for scope and provenance.

# Mini Jev 実験結果

第2段階の[出力ヘッド追加学習](HEAD_TUNING.md)も完了しました。新規96問では学習なし73/96、線形head67/96、biasのみ74/96。[詳細結果](results/head/REPORT.md)。以下は第1段階の学習なしベースラインです。

既存モデルから候補のlogitsを直接取り出して、Choice / Noul / Scoreを返す最小版を実装した。今回、ファインチューニングと確率校正は実施していない。

Apple M5 Pro、64GBメモリ、MPS、float32。手作り日本語48件（各型16件）、短い入力、各条件1回、読み込みとウォームアップを除く中央値。

| モデル | 方式 | 正解数 | 中央値 | 無効出力 |
|---|---|---:|---:|---:|
| Qwen2.5 0.5B | 候補logits直接 | 25/48（52.1%） | 30.0ms | 0 |
| Qwen2.5 0.5B | 1トークン生成 | 25/48（52.1%） | 33.8ms | 0 |
| Qwen2.5 0.5B | JSON生成 | 16/48（33.3%） | 231.0ms | 21 |
| Qwen2.5 1.5B | 候補logits直接 | 39/48（81.2%） | 84.2ms | 0 |
| Qwen2.5 1.5B | 1トークン生成 | 39/48（81.2%） | 91.6ms | 0 |
| Qwen2.5 1.5B | JSON生成 | 37/48（77.1%） | 403.6ms | 2 |

## この実験で分かったこと

- 型付きの判定APIは、追加学習なしでも構成できた。出力層から候補に対応する行だけを取り出し、生成ループを通さず分布を得られる。
- 1.5Bの直接読み出しはChoice 15/16、Noul 15/16、Score 9/16。0.5Bより改善したが、段階評価には誤りが残った。
- 1.5BでJSON生成との中央値比は約4.8倍、1トークン生成との比は約1.09倍。全語彙への最終投影との比は約1.06倍。出力層の行削減だけによる大幅な高速化は、この測定では確認していない。
- 直接読み出しと全語彙投影の候補確率は両モデルとも48件すべて一致。候補内で最大値を選ぶ判断も、1トークン生成と全件一致した。
- 1.5BのChoiceは選択肢を逆順にすると2/16件で意味上の答えが変わった。高い確率だけでは判断の頑健さを保証できない。

## 検証の範囲

通常のCausalLM.forwardとの数値一致、左padding付きバッチと単件の一致、評価用正解の入力混入防止、選択肢キーの意味保持、入力上限、型と確率の検証をテストした。両モデルで7テスト成功。

データは曖昧性を避けた小さな手作りセットで、一般化性能や実運用の品質は示さない。Scoreの正解数は最尤段階の一致を数え、期待値の誤差は詳細レポートに別記している。

JSON側は文法制約なしのgreedy生成で、全確率ではなくラベル1個のみを返す。形式指示と出力長も異なるので、JSON形式一般の精度優劣は結論できない。初回には固定の答えAを例示していたが、例示への偏りの疑いから削除して再測定した。修正前の結果も保存した。

確率は候補トークン内で正規化した未校正の値。本家JevのRLCD、共通stateの再利用、専用の並列推論は実装していない。モデルの重みを追加学習した結果ではない。

## 次に検証すべき仮説

凍結した本体＋出力headの学習で、弱かった段階評価と選択肢の順序依存を改善できるかが次の焦点。この評価48件を学習に使わず、別の訓練・校正・評価データを用意して、headのみの学習と必要に応じたLoRAを比較する。

## 保存物

- [実行手順とAPI](README.md)
- [0.5B詳細結果](results/REPORT.md)
- [1.5B詳細結果](results/qwen-1.5b/REPORT.md)
- [1.5Bの出力例](example-output.json)
- [修正前JSONプロンプトの探索記録](results/prompt-example-a/NOTE.md)
- [評価データの説明](data/dataset_notes.md)
