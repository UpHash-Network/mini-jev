> Public-release clarification: “manual”, “handwritten”, “手書き”, and “independent reviewer” in these historical records refer to individual writing/review by separate AI agents, not human expert annotation or external independent evaluation. See [DATA_CARD.md](DATA_CARD.md) for scope and provenance.

# Mini Jev — ローカルの判定モデル実験

既存LLMの最終隠れ状態から、選択肢に対応する単一トークンのlogitsを読み出す試作です。
文章生成もファインチューニングもせず、Choice / Noul / Scoreを返します。Jevの再実装や同等性能を意味しません。

実測済みの比較は[実験結果](RESULTS.md)を参照してください。0.5Bと1.5Bの両方を試しています。
出力ヘッドだけの追加学習も実施しました。[学習方法と再現手順](HEAD_TUNING.md)・[追加学習の評価結果](results/head/REPORT.md)を参照してください。

## 動作原理

1. `state`、`instructions`、`criteria`をチャット形式の入力にする。
2. 候補をA〜Zに対応付け、実際のプロンプト境界でも1トークンであることを検証する。
3. 本体のforwardを1回実行し、最後のトークン位置の隠れ状態を取る。
4. 語彙全体のLM headから候補トークンの行だけを取り出し、その小さな行列で投影する。
5. 候補内softmaxを計算し、結果をPythonで型付き出力に変換する。

`selected`投影は既存の出力重みを選択するだけで、学習済み重みを書き換えません。
`full`は同じ最終隠れ状態を語彙全体に投影する対照条件です。モデル本体の計算はどちらにも残ります。
Qwen2.5-0.5B-Instructを使い、float32、MPS/CUDA/CPUを選択できます。
対応アーキテクチャはQwen2/Qwen2.5に限定します。他のモデルでは出力層後の変換が異なる場合があるため、エラーにします。

## 実行

Python 3.10以上で、このフォルダに移動して実行します。Apple SiliconではARM版Pythonを使用してください。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python mini_jev.py --input example.json
.venv/bin/python benchmark.py --output results/baseline.json
.venv/bin/python -m unittest test_mini_jev -v
```

今回比較した1.5Bモデルで動かす場合:

```bash
.venv/bin/python mini_jev.py --model Qwen/Qwen2.5-1.5B-Instruct --input example.json
.venv/bin/python benchmark.py --model Qwen/Qwen2.5-1.5B-Instruct --output results/qwen-1.5b/baseline.json
MINI_JEV_TEST_MODEL=Qwen/Qwen2.5-1.5B-Instruct .venv/bin/python -m unittest test_mini_jev -v
```

デフォルトはローカルキャッシュのみを読みます。モデルをまだ持っていない場合は初回に明示的にダウンロードします（約1GB）。

```bash
.venv/bin/python mini_jev.py --input example.json --allow-download
```

1.5Bは`--model Qwen/Qwen2.5-1.5B-Instruct --allow-download`を付けます（約3.1GB）。このタスクでは両モデルをキャッシュ済みです。
測定時の依存関係を厳密に合わせる場合は、`requirements.txt`の代わりに`requirements.lock.txt`を使用してください。

このタスク内で準備した実験環境をそのまま使う場合は、`.venv/bin/python`を`../../work/clean-runtime/bin/python`に置き換えます。
重みの配布元: https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct

## Pythonから使う

```python
from mini_jev import MiniJev

engine = MiniJev()
answer = engine.decide({
    "type": "choice",
    "state": "請求書の金額について確認したいです。",
    "instructions": "問い合わせの担当部署を選んでください。",
    "criteria": {"billing": "請求や支払い", "technical": "技術的な不具合"},
})
print(answer["choice"], answer["probabilities"])
```

- Choice: `criteria`は文字列キー→説明の辞書。`choice`と確率分布を返す。
- Noul: `criteria`は省略可能。指定時は`false`と`true`の説明を含める。`noul`はYesの候補内確率。
- Score: `criteria`は順序付きの説明配列。`score`は0始まりの段階番号の期待値。`label`は最多確率の段階。

候補は2〜26個、各説明は空でない文字列に限定しています。入力が2,048トークンを超える場合はエラーにし、黙って切り詰めません。
`decide_many`は通常のpadding付きバッチ処理です。各質問でstateを読み直し、Jevの共通stateを共有する並列処理は実装していません。

## 確率の読み方

`probabilities`は「次のトークンが指定した候補のいずれかである」という条件付きの分布です。
正解確率の保証ではなく、`calibrated`は常に`false`です。独立した検証データで校正するまでは、高確率だけを根拠に自動承認しないでください。
`full`時の`candidate_mass`は候補が語彙全体で占める確率質量です。候補内で自信が高くても、この質量は低い場合があります。
型が保証されることと、判断内容が正しいことは別です。選択肢の並びにも影響され得ます。

## 評価と次の実験

`benchmark.py`は手作り日本語48件で、候補行のみ投影・全語彙投影・1トークン生成・短いJSON生成を比較します。
結果と測定上の限界は`results/REPORT.md`、ケース別の出力は`results/baseline.json`に保存します。
これは小規模な動作確認です。公開ベンチマークやJev実測との比較ではありません。実用途での品質・安全性は検証していません。

次に出力headの学習を試す場合は、この48件を学習に混ぜず、別の訓練・校正・評価データを用意します。
凍結本体＋head、必要なら本体のLoRA、という順で改善量を比較できます。

参考:
- Jev公式API: https://docs.typesafe.ai/api
- Jev公式発表: https://typesafe.ai/blog/introducing-system-one-models-and-jev
- Transformers出力仕様: https://huggingface.co/docs/transformers/main/en/main_classes/output
