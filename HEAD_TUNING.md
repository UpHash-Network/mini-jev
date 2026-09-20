> Public-release clarification: “manual”, “handwritten”, “手書き”, and “independent reviewer” in these historical records refer to individual writing/review by separate AI agents, not human expert annotation or external independent evaluation. See [DATA_CARD.md](DATA_CARD.md) for scope and provenance.

# 出力ヘッドだけを追加学習する実験

Qwen2.5-1.5B-Instructの本体と元の語彙出力重みを固定し、A〜Fの6候補に対する線形の補正だけを学習します。元モデルの重みファイルは変更しません。

今回の結果は、新規96問で追加学習なし73問正解、線形head67問正解、biasのみ74問正解でした。旧48問では線形headが39→40問に改善しましたが、新規問題では悪化しました。現段階で線形headを標準版へ採用する根拠は得られていません。

```
状態 + 質問 + 選択肢
        ↓
凍結したQwenの最終隠れ状態 h
        ↓
元の候補logits + ΔW × RMS正規化(h) + Δb
        ↓
温度で割る → 実際の候補数の範囲でsoftmax
```

学習パラメータは6×1536＋6＝9,222個です。最初の補正はゼロで、学習前は元の判定と一致します。元モデルの入力embeddingと出力重みが共有されていても、その共有重みを更新しません。

## データと比較条件

- 合成train 768件。Choiceの逆順版256件を同じ訓練分割に追加し、計1,024件。逆順版は入力から特徴を再計算します。
- 合成dev 192件。学習率、補正への罰則、学習回数をNLLで選択。
- 合成calibration 192件。モデルを選んだ後、温度だけを推定。
- 新規の独立手書きtest 96件。訓練・旧評価データを見ない別担当が作成。重みと温度を保存してから評価。
- 旧48件は、前の実験との回帰確認用です。

train/dev/calibrationは意味設定グループで分割しますが、同じ生成器のテンプレートを共有します。未見の推論構造への一般化を保証する分割ではありません。testも小規模な手作りデータであり、実運用評価ではありません。
拡張後の訓練例はChoice 512、Noul 256、Score 256件です。損失は各例を同じ重みで扱うため、拡張後のChoiceが半分を占めます。devとtestは各型を均等に含みます。

追加学習なし、線形補正head、候補文字ごとのbiasだけ（6パラメータ）の3条件を比べます。各条件について温度補正あり・なしを記録します。改善が位置の偏りの補正だけか、隠れ状態を使う効果かを区別するためです。

## 再現

このフォルダで、[旧実験用README](README_EXPERIMENTS.md)のPyTorch・Transformers環境を使用します。現行のネイティブサービス用の標準ライブラリだけの環境とは依存関係が異なります。

```bash
python make_training_data.py
python train_head.py
python validate_head.py
```

学習条件はスクリプトに固定しています。学習率0.001/0.003、補正logitsへの二乗罰則0.01/0.1、最大120回更新。dev NLLを5回ごとに確認して重みを選択します。温度はcalibration NLLを使い0.1〜10の範囲から選択します。testの結果を見て選び直す処理はありません。

本体が固定なので特徴を`work/head_features`にキャッシュし、補正headはCPUで学習します。特徴キャッシュの時間は推論速度として報告しません。特徴処理・選択肢順序・モデルrevision・データが変わるとキャッシュを無効化します。

## 学習したheadを使う

```bash
python head_jev.py --head results/head/checkpoint --input example.json
python head_jev.py --head results/head/checkpoint --input example.json --without-temperature
python head_jev.py --head results/head/checkpoint-bias --input example.json
```

```python
from head_jev import HeadMiniJev

engine = HeadMiniJev("results/head/checkpoint")
answer = engine.decide({
    "type": "noul",
    "state": "申請書は提出済みですが、承認はまだです。",
    "instructions": "この申請は承認済みですか？",
})
```

チェックポイントはJSON設定とsafetensorsのみです。推論時に元モデルのrevision、トークンID、特徴処理のfingerprintを照合します。候補は2〜6個に限定します。候補が多い場合はエラーにし、学習していない範囲へ黙って適用しません。

標準の`mini_jev.py`は学習なしのままです。追加headは明示的に指定したときだけ使います。

## 確率について

温度を掛けても最大確率の候補は変わりません。温度補正は正解率を上げる処理ではありません。
合成データ上で温度を推定したことを`temperature_calibration_applied`で示しますが、未知入力への校正性能は実証していないため、`calibrated`はfalseのままです。

測定値は[追加学習レポート](results/head/REPORT.md)、詳細予測は[experiment.json](results/head/experiment.json)、保存・復元と実推論の検証は[validation.json](results/head/validation.json)に保存します。

温度スケーリングの参考: [Guo et al., 2017](https://proceedings.mlr.press/v70/guo17a.html)。この論文の成績を今回のモデルの成績として扱ってはいません。
