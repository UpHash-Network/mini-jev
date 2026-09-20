> Public-release clarification: “manual”, “handwritten”, “手書き”, and “independent reviewer” in these historical records refer to individual writing/review by separate AI agents, not human expert annotation or external independent evaluation. See [DATA_CARD.md](DATA_CARD.md) for scope and provenance.

# 完成条件の検証記録

2026年9月20日。 [COMPLETION_CRITERIA.md](COMPLETION_CRITERIA.md) に従い、最終モデル・プロンプト・dtypeを固定してから新規の2,400問を評価しました。
評価中に設定を変更していません。失敗した旧4B版の問題は開発用に分け、独立の校正120問も最終試験へ含めていません。

| 確認 | 結果・根拠 |
|---|---|
| 新規2,400問・各型800問 | 全体93.25%、Choice96.00%、Noul95.25%、Score88.50%。[最終レポート](results/native-acceptance/REPORT.md) |
| 手書き180問の別集計 | 172/180。各型56/60、59/60、57/60 |
| 全出力の型・確率・範囲 | 2,400/2,400が正常。逆順800件も正常 |
| 候補順変更 | 800/800で意味ラベル一致。Choiceキー順の正規化による性質 |
| 常駐モデルの実推論 | 3,207 llama_decode呼び出し。入力512以下のp95 379.1ms、512超は521.8msとして別集計 |
| 数値読み出し | 公開8入力・58候補の全語彙参照との差0。計434検査。[数値監査](results/native-release-validation/REPORT.md) |
| Scoreの分岐・最大候補数 | 公開4問で2・10・11・26候補を実行。数字から英字への切り替え、段階順・期待値・legendを含む93検査成功。[記録](results/native-score-edges/report.json) |
| 再起動・SDK・HTTP | 実モデルを2回ロード。確率まで完全一致、8問処理、重複JSON拒否、SIGINTによる通常終了。[統合検証](results/native-integration/report.json) |
| 温度校正 | 別の120問でT=1.3489628826を選定。校正データのNLL 0.148213→0.135233。[校正記録](results/native-calibration/summary.json) |
| 実行物の固定 | 重み全体SHAを起動時検証。モデル・全nativeファイル・alias・Pythonコード・設定を結ぶfingerprint。試験中の変更検査も成功。[凍結記録](results/native-acceptance/freeze.json) |

実行環境はApple M5 Pro・64GB、macOS 26.4、ARM64 Python 3.10.5です。実ログでMetalのApple M5 Proと41/41層のGPU配置を確認しました。
runtime fingerprintは `4d2953166c63f2f1392b661a0331168459ac7cd359638612f37299513a118152` です。

HTTP再起動試験では、ファイル検証を含む起動が約9.18秒、3問まとめたHTTPリクエストが約579〜582msでした。OSファイルキャッシュのあるこのセッションでの観測です。単問速度へ割り算して使用していません。
複数質問は独立した逐次実行です。stateの共有prefill、回答キャッシュ、文章生成は使っていません。

CPUでの確認は、サービス36テスト、接続上限時の拒否処理100回の反復、モデル・native成果物の検証14テスト、評価ランナー18テスト、取得・包装13テストなどです。
接続上限時に未読の本文を残して閉じると送信エラーになる競合を再現し、制限付きの受信待ちを加えた修正版で解消しました。
モデルを使わないこれらのチェックは2,400問の精度試験に数えていません。

温度校正は全指標を改善する処理ではありません。最終試験のNLLは0.188423→0.187871、ECEは0.014863→0.015198、Score期待値MAEは0.169401→0.195121でした。校正の目的は校正用データのNLL最小化です。
Scoreの数字候補は全語彙に対する確率質量が小さい例があり、返す確率は許可候補だけで再正規化した条件付き確率です。confidenceも正解確率ではありません。

品質試験の候補数は2〜8です。API上限の26候補は機能確認の対象であり、2,400問で得た正解率をそのまま26候補へ適用しません。
生成問題は45の課題群でテンプレートを共有します。family別成績と弱点を[最終レポート](results/native-acceptance/REPORT.md)に掲載しています。
