# 人の利用者評価を前提としない主張の監査

2026-09-27。対象は NAACL 作業原稿と、現存する測定記録・実装・再現性記録である。監査開始時の `paper/naacl2027/main.tex` SHA-256 は `67c5ecbaa420fb04c3afa3d1c6802d335896992fb6f8239c1318d6792765d48e`。以下の行番号はこの版を指す。この監査では原稿、測定結果、凍結条件を変更せず、モデル推論も人の評価も実施していない。

## 判断

**現行論文の中心を、実行可能な型付きインターフェース、その契約の検査、既存条件での比較測定と再解析可能性に置けば、人の評価を待たずに改訂できる。** 主担当が本ターンに再確認した CFP では systematic baseline evaluation が選択肢に含まれる。ただし、実験を用意したことだけで採択が保証されるわけではない。現在の強みは測定範囲の明確さと反例の開示であり、GUI の使いやすさや新しい推論アルゴリズムの優位性ではない。

特に修正すべき実装との不一致を1点発見した。原稿の “candidate-token/logit inspection” は、ライブの公開 API・ブラウザから候補 token ID と生 logit を検査できるように読める。**内部エンジンはこれらを保持するが、公開応答は保持しない。** 確率・型付き値・意味メタデータの表示と、研究用 trace の logit 監査を分けて記述する必要がある。

## 現物と分母の確認

再現性 ZIP `paper/naacl2027/reproducibility/naacl-repro-v1-20260925.zip` を展開せず読み、以下の7予測ファイルの実行記録行数と SHA-256 を `VALIDATION.20260925.json` に照合した。すべて一致した。単に本文の合計を転載したものではない。

| ZIP 内のファイル（先頭 `mini-jev/` を省略） | 実測記録行数 | 台帳との hash 一致 |
|---|---:|---|
| `paper/matched_study/results/predictions.jsonl` | 4,050 | 一致 |
| `paper/journal_robustness/study_v1/results/predictions.jsonl` | 4,000 | 一致 |
| `paper/journal_robustness/cross_model/study_v1/results/qwen2.5-0.5b/predictions.jsonl` | 1,800 | 一致 |
| `paper/journal_robustness/cross_model/study_v1/results/qwen2.5-1.5b/predictions.jsonl` | 1,800 | 一致 |
| `paper/order_ensemble/study_v1/results/qwen2.5-0.5b/predictions.jsonl` | 4,800 | 一致 |
| `paper/order_ensemble/study_v1/results/qwen2.5-1.5b/predictions.jsonl` | 4,800 | 一致 |
| `paper/order_ensemble/study_v1/results/qwen3.6-35b-a3b/predictions.jsonl` | 4,800 | 一致 |
| **合計** | **26,050** | **7/7** |

26,050 は条件・反復を含む研究用 request 数であり、独立した問題数、参加者数、または低水準の `llama_decode` 呼出数ではない。例えば matched study の低水準 decode は 11,322 回で、request 4,050 件とは異なる。matched study は150件のローカル問題を各5回、外部600件を各1回、3条件で実施した。後続の presentation study は同じ外部600件を再使用する。cyclic study は別の600件を使用するが、出典の依存まで解消したわけではない。研究用3パネルに含まれる外部 source item は合計1,200件である。

歴史的ローカル回帰2,400件、以前の external pilot 300件、LMQL 12合成入力、ChainForge 4 request pairs、人向け教材の AI 操作60回答と別AIの30回答は、この26,050へ追加していない。これらを「全件独立の品質評価」へ合算する根拠はない。

## 重要主張と支持できる範囲

| 原稿の主張 | 現存する根拠・分母 | 言える範囲／査読で残る穴 |
|---|---|---|
| 凍結モデルから Choice・Noul・Score を返す | `native_engine.py` の `_single`、`service/schema.py` の `public_answer`、`reproducibility/LIVE_SMOKE.json`。再構築 runtime の1 SDK request 内で3型を実推論 | 実装・動作の主張は支持される。新しい学習法、学習済み decision head、別マシンへの移植性の証拠ではない。型の構造が正しいことと意味の正しさは別である。 |
| ブラウザで候補分布、型付き値、意味・校正メタデータ、完了応答と変更後入力の区別を検査できる | `demo/static/app.js` の `renderAnswers` と `completedRequest` 比較、`demo/static/index.html`、保存済み live response | 情報と操作が実装されていることはコードから確認可能。人が正しく解釈する、ミスが減る、速くなるという効果は未測定。内部 candidate IDs/logits は公開 API の返却対象ではない。 |
| 2,400件すべて型が妥当だが162件の top label が誤った | `results/native-acceptance/summary.json`: `overall.count=2400`, `valid=2400`, `correct=2238`。各型800件 | AI作成の参照ラベルに対して162件不一致。45テンプレート家族と180個別AI作成問題であり、開発に使った誤りを含む。独立した人が確定した正解に対する汎化精度とは言えない。本文の “wrong” は参照ラベルとの不一致に限定するとより正確。 |
| direct と native one-token の parity | `paper/matched_study/SUMMARY.json` の `parity`、`parity.csv`、上記 raw predictions。1,350 pairsで prefix・token・candidate IDs・label 一致、最大 logit 差0、最大値の同率0 | この1モデル・同一条件での一致を支持。全モデル・任意の sampler 設定や tie の挙動には外挿しない。本文は既に条件を明示している。 |
| direct の速度優位は確立していない | `paper/matched_study/REPORT.md` / `SUMMARY.json`。150ローカル項目の各5反復平均の paired 差の中央値。one-token − direct = +0.0898 ms、55 family/tag cluster・10,000 resamples による区間 [−0.7483, +0.8449] ms | 1セッション・1マシンの条件付き比較。区間が0を含むことは「差がない」と証明しない。実用的同等性マージンを事前固定した equivalence test でもない。JSON の +160.2958 ms は別 prompt/prefill と serialization を含み、純粋なサンプラ速度や他 framework への優位を示さない。 |
| 外部問題で課題ごとの性能を測定 | matched `SUMMARY.json` の `external_quality`。JCoLA:172/200、MCC .5708207663、always-acceptable158/200。JCQA:190/200対JSON191/200。JSTS:200件、連続 gold に対する期待段階MAE .5065 | ベンチマーク全体や新しい未見問題の性能ではない。public-development subset と不明な training contamination、JSTSの以前のpilotとの6件の依存を残す。3課題を1個のaccuracyへプールしない。JSONには同じ確率ベクトルがなく、期待段階との同一指標比較はできない。 |
| 完全同一入力の再実行は安定でも、表示順で判断が変わる | ZIP内 `journal_robustness` の2つの `analysis/SUMMARY.json` と completion records。600 items × 3 checkpoints の1,800 repeat pairs、native JCQA display-reverse11/200 flips | 入力が同じ時の repeatability と変更時の sensitivity の対比は支持される。three checkpoints を含むが同じ family のモデルであり、backend/precisionの交絡もある。「LLM一般」やモデルサイズ効果の実証ではない。 |
| cyclic averaging の安定化と品質は別 | ZIP内 `order_ensemble/study_v1/analysis/<model>/method_quality.csv` / `SUMMARY.json`。各checkpoint・課題200件。JCQA のsingle→cyclic accuracyは .395→.36、.8→.835、.985→.98。0.5B JCoLA cyclicは200/200でtrue、正解157/200・MCC未定義 | 固定済みパネルでの具体例として支持。アルゴリズムの新規性、安定性と正確性の一般的な新発見、等計算量での改善は主張しない。binaryのforward/reverse一致は同じ2呼出の再集約という構造的結果。平均化はライブUIの機能ではない。 |
| 再解析・再構築可能 | `reproducibility/REANALYSIS_CHECKS.json` と `VALIDATION.20260925.json`。保存観測の6解析・56生成物がbyte identical。fresh compile、cached pinned sourceとhash-verified modelを使用、同じMacで3型smoke | 既存記録を再計算できたことは強い再現性証拠。独立研究者の追試、新推論での同値、fresh download、別マシン実証とは異なる。この監査では当時の成功記録を読み、ZIPの7予測ファイルを照合したのであり、56ファイル再解析を新たに実行したとは主張しない。 |
| LMQL・ChainForge と統合できる | LMQL `comparator_study/run_v1/SUMMARY.json`:12合成入力、argmax12/12、最大確率差2.6326e−5、公差1e−5は3件未達。ChainForge `results.json`:4 request pairs / 8 typed-answer pairs、native HTTP8件 / individual questions16、invalid3件拒否 | カスタム native/LMTP backend または provider の境界診断。LMQL stock backend、ChainForgeブラウザ、実タスク品質、速度の比較ではない。numerical tolerance未達を残す現行記述は適切。 |
| AIの予行評価ができた | 内部保管の `inspection_study/ai_rehearsal_20260927/REPORT.ja.md` とraw log・hash・採点記録（この公開版には含めない補助QA資料）。1つのAI操作主体の2セッション60回答、別コンテキストAIの30回答 | 合成教材と保存・採点経路の点検。Mini Jev推論0、人0。ルーブリックへの既接触、同一問題の反復、DOM/ARIA操作があり、人のユーザビリティ結果や独立90人相当へ変換できない。原稿の人研究欄に追加しない。 |

根拠表中の `reproducibility/`、`comparator_study/`、`chainforge_integration/`、`inspection_study/` は `paper/naacl2027/` からの相対パスである。ZIP内の `journal_robustness` と `order_ensemble` はこの checkout の直下に存在するディレクトリとは限らないため、提供された ZIP 内の正確なパスを使う。

## 最小の本文修正案

### 1. 公開UIの検査可能範囲を正す（必要）

対象: `main.tex` 223行、Inspection interfaces の最後から2文目。

現状:

> `\system{} supplies local frozen-model candidate-token/logit inspection and auditable system evaluation.`

置換案:

> `\system{} supplies local frozen-model candidate-probability inspection and auditable system evaluation.`

必要なら同節の外に、研究用証拠の範囲として次の短文を置く:

> `Research traces retain candidate token IDs and logits; the public API exposes typed values, probabilities, and semantic metadata.`

根拠: `native_engine.py:420` の内部resultには `candidate_logits` / `candidate_ids` がある。しかし `service/schema.py:171` が公開answerを新しく構成し、同208–215行の公開応答allowlistにもこれらはない。`demo/static/app.js:177` 以降は公開応答の値・確率・意味メタデータを描画する。API全体の `usage.input_tokens` はtoken数であり、candidate token IDではない。`RELATED_WORK_COMPARISON.20260927.md` の「API exposes candidate IDs and logits in metadata」も本文と同時に訂正すること。内部研究経路を公開UIの特色に見せるのは避ける。

### 2. ローカル回帰ラベルの出所を反映する（推奨）

対象: `main.tex` 150行。

現状:

> `All 2,400 outputs were valid, but 162 top labels were wrong: structural validity does not establish correctness.`

置換案:

> `All 2,400 outputs were valid, but 162 top labels disagreed with the authored reference labels: structural validity does not establish task correctness.`

参照作成がAI支援である説明は既に直前にある。数値や判定方法を変えず、独立した正解保証まで含意しない表現になる。

### 3. latencyの結論を「未確立」に統一する（小さな明確化）

対象: Introduction の `Our matched study finds no material latency advantage over native one-token selection.`

置換案:

> `Our matched study does not establish a latency advantage over native one-token selection.`

Abstract の `without an established latency advantage` とEvidenceの限定は維持する。「0を含む区間」を「実用的な差がないことの証明」へ強めない。

## 人を待たずに進める準備の優先順位

1. **公開インターフェースと研究traceの境界を直す。** 新しい機能を付け足すより先に、上の主張を現行実装へ合わせる。特に競合との差分を述べる段落に実装上存在しない特色が残らないようにする。
2. **各比較の一致条件と未測定項目を短い証拠表にする。** direct/one-tokenは入力・候補一致、JSONはserializationを含む別prompt、LMQLはcustom backend、ChainForgeはbackend dispatchである。これなら新しい被験者もモデル実行も不要で、査読者が一括して「baseline不足」と誤読する余地を減らせる。Langfuse/Phoenixのsource-based比較を測定比較と同じ扱いにしない。
3. **具体的な失敗例を既存データに結び付ける。** typed validity・concentration・repeatability・accuracyが異なることを、既存の測定済み反例とその分母で示す。後から選ぶ例は事後的なillustrationであると表示し、選んだ成功例で新しい性能主張を作らない。外部原文を再掲する際は既存データ配布条件を確認する。
4. **提出物の再現性入口を揃える。** 56生成物の再解析とMacでのfresh compileは既に実施済みである。毎回同じ再解析を繰り返すより、論文の数字→raw record→解析→artifact manifestへ辿れる入口、公開branchに実在するファイル、論文版とコード版の対応を仕上げる。immutable commit/archive hashを示すと、可変branch URLだけの場合の曖昧さを減らせる。

人の評価なしで言えないのは、「人が分かりやすく感じた」「GUIで作業が速くなった」「判断ミスが減った」「他ツールより使いやすい」である。一方、ベンチマークの既存参照ラベルによる比較、入出力契約の検査、保存観測の再解析、統合境界の実測は、人の参加者を新たに集めず実施・記述できる。現行論文は後者を中心に完成させ、人の評価は追加実施できる場合の別の証拠として扱うのが妥当である。
