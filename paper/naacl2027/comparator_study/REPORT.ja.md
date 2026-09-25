# LMQL候補採点とのカスタムbackend統合診断：結果

2026-09-25。**全12入力のargmaxは一致したが、事前に固定した確率公差1e-5は3入力で未達だった。公差は変更していない。**

実際のLMQL 0.7.3の`model.score`と`ScoringResult.probs`を実行した。同一checkpoint、量子化、完全prefix token IDs、単一token候補、T=1を確認した。LMQLとMini Jevで共有するpinned llama.cppへ、研究用のLMTP backendを追加した統合診断であり、stock llama-cpp-python backendのベンチマークではない。

|項目|結果|
|---|---|
|合成入力|12（Choice / Noul / Score 各4、各型で英語2・日本語2）|
|native decode API calls|64（direct 12 + LMQL continuation 52）|
|全prefix・候補tokenの一致|12/12、52 continuationすべて一致|
|argmax一致|12/12|
|最大候補確率絶対差|2.6325888176637058e-5|
|確率公差1e-5|9/12合格、3/12未達|
|Noul / Scoreの値の最大絶対差|7.181393344257714e-5|
|値の公差1e-4|8/8合格（Noul 4 + Score 4）|
|算術・入出力trace・frozen hash監査|494/494整合|
|事前のparity検査|29/32合格（確率12、argmax12、値8）|
|終了状態|モデルプロセス終了、入力・モデル・環境のhash不変|

## 入力ごとの差

|入力|確率の最大絶対差|1e-5公差|argmax|値の絶対差|
|---|---:|---|---|---:|
|choice-01|2.29256207e-07|合格|一致|対象外|
|choice-02|1.5048072e-06|合格|一致|対象外|
|choice-03|5.21698531e-07|合格|一致|対象外|
|choice-04|1.04856838e-06|合格|一致|対象外|
|noul-01|1.26979824e-07|合格|一致|1.26979824e-07|
|noul-02|1.50432474e-06|合格|一致|1.50432474e-06|
|noul-03|1.3770884e-07|合格|一致|1.3770884e-07|
|noul-04|1.23241883e-07|合格|一致|1.23241883e-07|
|score-01|2.43458463e-05|未達|一致|5.61503454e-05|
|score-02|8.94784983e-06|合格|一致|1.41589874e-05|
|score-03|2.0047171e-05|未達|一致|1.3239128e-05|
|score-04|2.63258882e-05|未達|一致|7.18139334e-05|

## 不一致について確認できた範囲

確率差が公差を超えたのはscore-01、score-03、score-04。LMQL用の全予測位置を採点するnative経路と、最終位置だけを読み出すdirect経路で、softmax前の生logitに最大0.01061248779296875の差があった。同一入力に対して候補ごとのfull-vocabulary logsumexpは一致しており、その範囲は全ケースで0だった。tokenizationや候補欠落は観測されなかった。ただし、この記録だけでは数値差の根本原因を確定できない。

異なるnative scoring pathsを含む比較であり、この差をLMQLのscoring式固有の誤りと解釈しない。公差を事後的に緩めたり、失敗入力を削除したり、結果が一致するまで再試行したりしていない。固定runは1回のみで、追加のモデル推論は行っていない。

## 原稿に利用できる英語記述

> A diagnostic integration used unmodified LMQL 0.7.3 scoring through a custom LMTP backend sharing our pinned native runtime. Across 12 prespecified synthetic inputs, complete prefix and candidate token IDs matched, and all argmax decisions agreed. The maximum probability difference was 2.63e-5; three cases exceeded the prespecified 1e-5 tolerance. This tests the custom integration, not LMQL’s stock backend or task-level superiority.

## 限界と記録

少数の単純な合成入力で、出力分布は強く集中している。一般の品質・境界付近の判断・複数token候補・別checkpoint・温度・実ユーザーの有用性に外挿しない。時間はログに残すが、両経路の処理範囲と呼出数が異なるため速度比較に使わない。64 decodeは既存の研究用request数とは別であり、既存の測定台帳へ合算していない。

実行前の条件は[PROTOCOL.ja.md](PROTOCOL.ja.md)、固定hashは[FREEZE.json](FREEZE.json)、詳細traceは[run_v1/results.jsonl](run_v1/results.jsonl)、完了記録は[run_v1/SUMMARY.json](run_v1/SUMMARY.json)、実行runnerをimportせずに再計算した監査は[run_v1/AUDIT.json](run_v1/AUDIT.json)。監査は同一保存結果の算術・整合性確認であり、独立した研究チームによる追試ではない。

[LMQL公式API](https://lmql.ai/docs/lib/generations.html) / [公式llama.cpp backend説明](https://lmql.ai/docs/models/llama.cpp.html)。
