# LMQL比較：保存ログの追加診断

2026-09-27。事後的な算術再解析。新規推論0回、人の参加者0人。元の凍結データ・公差・監査記録は変更していない。

**全12例でargmaxは一致するが、3例の確率公差違反は残る。これを「LMQLと完全一致」「他の条件でも判断は同じ」とは扱えない。** 原稿の公差未達の記述を維持し、以下の範囲まで説明を具体化できる。

|公差未達例|確率の最大絶対差|nativeの上位2候補確率差|LMQLの上位2候補確率差|両経路のargmax|Score期待値の絶対差|
|---|---:|---:|---:|---:|---:|
|score-01|2.43458463e-5|0.97991772|0.97988456|4|5.61503454e-5|
|score-03|2.00471710e-5|0.98971216|0.98968674|3|1.32391280e-5|
|score-04|2.63258882e-5|0.99067197|0.99063545|5|7.18139334e-5|

確率公差1e-5は9/12例で達成、Noul/Score値の公差1e-4は8/8例で達成。失敗3例のnative→LMQL期待値は、順に3.9710321015→3.9709759512、2.9960876907→2.9960744516、4.9824092728→4.9823374589。離散ラベルの一致と連続値の一致は別であり、値も完全同一ではない。

## 確認できたこと

- 全12例のnative最大候補確率は0.98453087以上、上位2候補差は0.97991772以上。保存された誤差の最大値の2倍を引いても全例で正なので、この比較におけるargmaxの不変は算術的にも説明できる。境界に近い例の頑健性は未評価。
- LMTPの保存生logitを候補間でdouble精度softmaxすると、LMQL保存確率との差は最大3.63670e-9。各例で候補間の語彙logsumexpは完全同値のため、候補正規化では共通項として相殺される。保存された2つのnative経路のlogit差から、ほぼ同じ大きさの確率差を再現できる。
- LMQL保存スコアは、LMTP保存logprobをfloat32へ丸めた値と全候補で一致する。この丸めと、その後の正規化による保存値との差だけでは1e-5超の差を説明できない。これは保存値の算術的な分解であり、丸めが起こるライブラリ内部の全経路を再実行した結果ではない。
- native生logitの最大絶対差は0.0106124878。候補ごとのlogit変化は一様な定数移動ではなく、候補間確率にも差が生じている。

## 実装経路と限界

directは1回のprefix decode後に最終位置logitを取得し、候補だけに正規化する。LMQLは未改変0.7.3の`model.score`/`ScoringResult.probs`を通すが、カスタムLMTP backendが候補ごとに全予測位置のlogitを要求してprefixをdecodeし、語彙全体で正規化したsequence logprobを返す。元の実行はdirect12回、LMTP52回の計64 decode。今回の再解析で追加した呼出しではない。

コード上の経路差とlogit差は確認できるが、Metal kernel、演算精度、batch設定などのどれが根本原因かは、この1回のログでは確定できない。LMQLの正規化式の欠陥とも、Mini Jevの優位性とも解釈しない。

さらに、凍結済み12入力は全てstate/question/candidatesの本文を2回連結している。Choice/Noul/Scoreはそれぞれ候補数5/2/6で、Scoreだけassistant prefixが`{"answer":`、他は空。したがって型・候補数・prefixが交絡している。失敗がScoreに集中した事実だけでは、Score固有の原因を示せない。両経路に同一の完全prefixを渡した内部比較は維持されるが、通常の単一記述prompt・境界付近・複数token・stock LMQL backend・速度・使いやすさへ一般化しない。

次の実証が必要なら、旧runを残して新たな事前固定版で、同じprefixに対する最終位置/全位置logitの反復比較、保存した同一logitからの正規化対照、候補数とprefixを揃えた条件、上位候補が拮抗する入力を設計する。今回は実行していない。

## 再現

リポジトリ直下で、標準Pythonのみで実行できる。

```sh
python3 paper/naacl2027/nonhuman_revision_20260927/lmql_diagnostic/analyze.py
```

[DIAGNOSTIC.json](DIAGNOSTIC.json)は全12例・52候補の差分、上位margin、期待値、入力とコードのSHA-256を含む。scriptはモデルやLMQLをimportせず、元ファイルを読み取り、既存receiptとhashを照合し、処理前後の同一性を検証する。元の494項目監査は過去の記録であり、今回モデル重みや元実行環境の全hashを再検証したとは主張しない。

根拠：[生ログ](../../comparator_study/run_v1/results.jsonl)、[凍結条件](../../comparator_study/FREEZE.json)、[元protocol](../../comparator_study/PROTOCOL.ja.md)、[native helper](../../comparator_study/llama_lmql_helper.cpp)の223–260/309–335行、[runner](../../comparator_study/run.py)の32–45/68–98行、[ケース生成](../../comparator_study/make_cases.py)の本文連結処理。
