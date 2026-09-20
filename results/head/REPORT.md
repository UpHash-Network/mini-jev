> Public-release clarification: “manual”, “handwritten”, “手書き”, and “independent reviewer” in these historical records refer to individual writing/review by separate AI agents, not human expert annotation or external independent evaluation. See [DATA_CARD.md](../../DATA_CARD.md) for scope and provenance.

# 出力ヘッドだけの追加学習

新規96問では、学習なし 73問、線形head 67問、biasのみ 74問が正解。この訓練データと設定では、線形headによる未見問題の正解率改善を確認できなかった。

モデル: `Qwen/Qwen2.5-1.5B-Instruct`。本体は凍結。学習パラメータ数: 9,222。

最終隠れ状態をRMS正規化し、元の候補logitsへ線形の補正を加えた。開発データのNLLで重みを選択し、別の校正データで温度を決めた。テスト結果はモデル選択に使っていない。

選択した設定: `{'lr': 0.003, 'penalty': 0.01, 'epoch': 120, 'dev_nll': 0.9935372471809387}`。温度: baseline=7.356, head=1.184。


## dev

| 条件 | 正解数 | 正解率 | NLL | Brier | ECE | Score MAE |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 87/192 | 45.3% | 1.857 | 0.844 | 0.339 | 0.993 |
| baseline_temperature | 87/192 | 45.3% | 1.084 | 0.623 | 0.100 | 1.045 |
| head | 100/192 | 52.1% | 0.994 | 0.568 | 0.086 | 0.861 |
| head_temperature | 100/192 | 52.1% | 0.983 | 0.563 | 0.056 | 0.871 |
| bias_only | 93/192 | 48.4% | 1.713 | 0.814 | 0.315 | 0.989 |
| bias_only_temperature | 93/192 | 48.4% | 1.075 | 0.618 | 0.137 | 1.033 |

## calibration

| 条件 | 正解数 | 正解率 | NLL | Brier | ECE | Score MAE |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 84/192 | 43.8% | 2.087 | 0.902 | 0.400 | 1.014 |
| baseline_temperature | 84/192 | 43.8% | 1.082 | 0.626 | 0.086 | 1.029 |
| head | 107/192 | 55.7% | 0.946 | 0.537 | 0.049 | 0.721 |
| head_temperature | 107/192 | 55.7% | 0.942 | 0.537 | 0.057 | 0.743 |
| bias_only | 85/192 | 44.3% | 1.924 | 0.877 | 0.386 | 1.011 |
| bias_only_temperature | 85/192 | 44.3% | 1.074 | 0.621 | 0.134 | 1.012 |

## test

| 条件 | 正解数 | 正解率 | NLL | Brier | ECE | Score MAE |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 73/96 | 76.0% | 1.078 | 0.402 | 0.156 | 0.426 |
| baseline_temperature | 73/96 | 76.0% | 0.868 | 0.456 | 0.261 | 0.856 |
| head | 67/96 | 69.8% | 0.810 | 0.408 | 0.079 | 0.487 |
| head_temperature | 67/96 | 69.8% | 0.774 | 0.400 | 0.063 | 0.495 |
| bias_only | 74/96 | 77.1% | 1.014 | 0.390 | 0.162 | 0.404 |
| bias_only_temperature | 74/96 | 77.1% | 0.819 | 0.427 | 0.248 | 0.796 |

## legacy48

| 条件 | 正解数 | 正解率 | NLL | Brier | ECE | Score MAE |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 39/48 | 81.2% | 0.823 | 0.321 | 0.143 | 0.640 |
| baseline_temperature | 39/48 | 81.2% | 0.719 | 0.375 | 0.266 | 0.842 |
| head | 40/48 | 83.3% | 0.528 | 0.227 | 0.093 | 0.739 |
| head_temperature | 40/48 | 83.3% | 0.518 | 0.232 | 0.129 | 0.728 |
| bias_only | 39/48 | 81.2% | 0.781 | 0.308 | 0.150 | 0.616 |
| bias_only_temperature | 39/48 | 81.2% | 0.671 | 0.343 | 0.241 | 0.813 |

## 型別の新規テスト正解数

| 条件 | Choice | Noul | Score |
|---|---:|---:|---:|
| baseline | 25/32 | 25/32 | 23/32 |
| baseline_temperature | 25/32 | 25/32 | 23/32 |
| head | 22/32 | 25/32 | 20/32 |
| head_temperature | 22/32 | 25/32 | 20/32 |
| bias_only | 25/32 | 26/32 | 23/32 |
| bias_only_temperature | 25/32 | 26/32 | 23/32 |

## Choiceの候補順監査

- test / baseline: 意味ラベル一致 25/32、逆順で正解 23/32、平均TV距離 0.259。
- test / head: 意味ラベル一致 24/32、逆順で正解 23/32、平均TV距離 0.247。
- test / baseline_temperature: 意味ラベル一致 25/32、逆順で正解 23/32、平均TV距離 0.121。
- test / head_temperature: 意味ラベル一致 24/32、逆順で正解 23/32、平均TV距離 0.255。
- test / bias_only: 意味ラベル一致 25/32、逆順で正解 23/32、平均TV距離 0.255。
- test / bias_only_temperature: 意味ラベル一致 25/32、逆順で正解 23/32、平均TV距離 0.140。
- legacy48 / baseline: 意味ラベル一致 14/16、逆順で正解 15/16、平均TV距離 0.104。
- legacy48 / head: 意味ラベル一致 14/16、逆順で正解 14/16、平均TV距離 0.148。
- legacy48 / baseline_temperature: 意味ラベル一致 14/16、逆順で正解 15/16、平均TV距離 0.077。
- legacy48 / head_temperature: 意味ラベル一致 14/16、逆順で正解 14/16、平均TV距離 0.155。
- legacy48 / bias_only: 意味ラベル一致 14/16、逆順で正解 15/16、平均TV距離 0.113。
- legacy48 / bias_only_temperature: 意味ラベル一致 14/16、逆順で正解 15/16、平均TV距離 0.086。

## 保存・復元と実推論

検証 30/30項目成功。CPU特徴から再計算した確率と、保存したheadを読み込んだGPU推論との一致を確認した。
実forwardの中央値はbaseline 99.1ms、head 104.1ms。新規テストの先頭12件（Choiceのみ）を各3回測定した値であり、特徴キャッシュや学習時間を推論時間として扱っていない。
詳細は[validation.json](validation.json)を参照。

## 限界

合成訓練・開発・校正データは意味設定グループで分割しているが、生成器の共通テンプレートを共有する。新規96件は訓練・旧評価データを見ない別担当者が執筆した小規模な手作り評価である。実運用や未知分野一般の品質を保証しない。

温度スケーリングは順位を変えず、正解率の改善手段ではない。合成校正データの確率特性が実入力にも通用するとは限らない。ECEは少数サンプルとビン分けに影響される。

旧48件は前フェーズで分析済みの回帰確認用。候補順だけ変えた例は訓練側にまとめており、独立の評価例として数えない。

Choiceの並べ替え拡張後、訓練損失の半分がChoice、各4分の1がNoulとScoreに対応する。devとtestは型ごと均等。

既存モデルや標準MiniJevのデフォルトは変更していない。headは明示的に指定したときだけ読み込まれる。
