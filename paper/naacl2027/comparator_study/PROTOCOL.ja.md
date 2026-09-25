# LMQL 0.7.3 native adapter integration diagnostic

2026-09-25。モデルの測定前にこの文書と実行ファイル・入力・依存を FREEZE.json で固定する。

## 目的と比較対象

候補採点・候補内正規化は既存の LMQL にある機構であり、新規性または Mini Jev の優位性とは主張しない。実際にインストールした未改変 LMQL 0.7.3 の `model.score(prompt, labels)` と `ScoringResult.probs(agg="sum")` を通し、同一 tokenized prefix、同一単一 token 候補、同一 T=1 の Mini Jev native direct readout に一致するかを診断する。

LMQL の標準 llama.cpp backend は llama-cpp-python に依存する。今回は既存の GGUF と pinned llama.cpp ライブラリを完全に共通化するため、公式 LMTPModel registry 拡張点を使う**カスタム backend**を用意した。stock backend の動作・導入容易性・速度を測った実験ではない。LMQL の tokenizer、DcModel、LMTP scheduler、sequence scoring、ScoringResult はインストール済み package の実コードを実行する。LMQL 関数をコピーした自作計算ではない。

## 固定条件

- checkpoint: ggml-org/Qwen3.6-35B-A3B-GGUF、revision baec3ebee244827cda0f4557eafa8b28f7545fa6、Q4_K_M、SHA256 671e47e0ec53c665d048b98c3ecbfd5236b5ca9c3e02ed19fc8f81f7b85140c7。
- tokenizer: Qwen/Qwen3.6-35B-A3B、revision 995ad96eacd98c81ed38be0c5b274b04031597b0。4ファイルを取得し、LMQL の transformers tokenizer として渡す。
- llama.cpp: f072b103714dfa1eee531f80b24512faf38e3dd2。既存確認済み runtime の共有ライブラリを hash 検証してコピー。
- Metal、6 CPU threads、context=2048、各 request の state を clear、バッチは独立した単一 sequence。T=1、sampler/grammar/量子化/追加 logit processor の変更なし。候補生成や EOS 生成なし。
- 12 合成入力: Choice 4、Noul 4、Score 4。各型で英語2・日本語2。CASES.json の prompt は既存 native Jinja renderer で作り、同じ内容を直接比較と LMQL に渡す。Choice 5候補、Noul 2候補、Score 6候補。
- 入力は英語システム文と英語ラベル説明書式に統一し、state/question/candidate meaning を2言語で変える。これは合成機構診断であり、原稿の実データ評価ではない。
- 一件あたり1 direct と候補数回の LMTP score。合計12 direct +52 continuation requests =64 llama_decode API calls。ウォームアップ・再試行なし。GPU は他の本タスク推論と同時使用しない。

## 実装と監査可能性

既存 matched native helper に `lmql_score` モードだけを追加し、direct/one_token/json の経路は変更しない。score モードは LMTP が渡した sequence の最後の target token を除いた prefix を decode、全予測位置の全語彙 logits を実際に計算する。各位置について full-vocabulary logsumexp を引き、実 token の logprob 配列を LMTP に返す。LMQL はそのうち continuation を取り出し、候補間の確率へ正規化する。巨大な全語彙ベクトルを保存する代わりに各候補の最終生 logit、full-vocabulary logsumexp、sequence logprobs、全 input IDs を保存する。

`--preflight` は人工 logprob を返す専用fixtureであり、ライブラリ経路・tokenizer・境界確認だけに使う。モデル実測や competitor parity の証拠には数えない。失敗した開発 preflight 記録も work 配下で保持する。測定後は入力・コード・モデル・依存の frozen hash が不変か確認する。

## 事前固定した合格条件と停止規則

- native と LMQL の完全 prefix ID 配列が同一。
- 各候補が独立でも prefix へ連結しても同一の単一 token。
- LMTP の全52 continuation request の prefix と候補IDが予期した通りで、BOS追加・prefix切り捨て・候補欠落なし。
- 全ケースで候補確率の最大絶対差 ≤ 1e-5。
- 全ケースで argmax 候補一致（tieが発生した場合は別記し、都合よく候補順を変更しない）。
- Noul の yes 値（候補値1,0）と Score の期待値（候補値0..5）の絶対差 ≤ 1e-4。
- 全ケース完了、64 calls、実行プロセス終了、frozen hashes不変。
- 不一致は失敗として保存し、閾値・条件を結果に合わせて緩めない。根本の実装不具合を直す場合は旧結果を残し、新版として明記する。

## 解釈の範囲

この診断は当該12入力・checkpoint・量子化・T=1・単一token候補に限定する。複数token continuation、一般の accuracy/有用性、人の理解、速度優位を検証していない。LMQL の canonical llama-cpp-python backend への外挿も行わない。時間は単なる実行記録として保持し、同一機械であっても処理範囲と batching が異なるのでランキングに使わない。

一次情報: [LMQL Generations API](https://lmql.ai/docs/lib/generations.html)、[LMQL llama.cpp backend](https://lmql.ai/docs/models/llama.cpp.html)、[LMTPModel extension interface](https://github.com/eth-sri/lmql/blob/main/src/lmql/models/lmtp/backends/lmtp_model.py)。実行に用いる版の実コードは installed package の hash を記録する。
