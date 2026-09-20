> Public-release clarification: “manual”, “handwritten”, “手書き”, and “independent reviewer” in these historical records refer to individual writing/review by separate AI agents, not human expert annotation or external independent evaluation. See [DATA_CARD.md](../../DATA_CARD.md) for scope and provenance.

# Native 数値監査

2026年9月20日 12:06–12:07（日本時間）の監査は **434 項目すべて合格、失敗 0**。対象は公開の簡単な入力 8 問であり、434 問の精度試験ではありません。詳細は [report.json](report.json) に保存しています。

本番エンジンの 39 回と、別途起動した参照用 helper の 12 回、計 51 回の `llama_decode` 呼び出しを確認しました。各有効リクエストは decode 1 回、生成トークン 0 です。バッチ API は入力ごとの逐次・独立実行です。別 helper との比較はサービス再起動試験を意味しません。

8 問・58 個の候補について、全語彙 logits を Python 側で候補 ID により抽出した値と C++ helper の候補 logits が完全一致しました。**最大絶対差は 0**（全件の厳密一致から算出）。別 helper と本番エンジンの候補 ID・logits も全件完全一致しました。

| 公開入力 | 候補数 | 入力トークン数 | 全語彙中の候補確率の合計 | 全語彙で最大の token ID |
|---|---:|---:|---:|---:|
| Choice | 2 | 198 | 99.991495% | 33 |
| Choice | 8 | 342 | 99.999124% | 36 |
| Choice | 26 | 774 | 99.999715% | 49 |
| 長い Choice | 8 | 862 | 99.999672% | 37 |
| Noul false | 2 | 154 | 99.978316% | 32 |
| Noul true | 2 | 154 | 99.992599% | 33 |
| Score | 2 | 203 | 0.010583% | 220 |
| Score | 8 | 275 | 0.009848% | 220 |

返却確率は許可候補だけで再正規化した条件付き確率です。上表の全語彙に対する確率や、答えが正しい確率とは異なります。特に Score の数字候補の全語彙中の確率は小さく、候補内の確率が高くても、通常の次トークン選択でその数字を出しやすいことを意味しません。上表の最大 token ID は logits から求めており、生成はしていません。

単問と混在バッチ、別入力を挟んだ再判定、Choice 辞書の挿入順変更の一致を確認しました。17 問バッチ・27 候補・後半に不正入力を含むバッチ・2,048 トークン超過を推論前に拒否し、入力の切り詰めを行わず、その後の正常な判定へ復帰しました。helper 単体でも不正トークン上限・候補超過・複数トークン候補の拒否と復帰を確認しています。

実行設定は Qwen3.6-35B-A3B Q4_K_M、Metal、6 threads、`repeat_typed_score`、上限 2,048 トークン。**この監査では temperature 1.0、温度校正の適用なし**です。runtime fingerprint は `4d2953166c63f2f1392b661a0331168459ac7cd359638612f37299513a118152`。モデル・native package・設定・検証器の SHA-256 は JSON に記録しています。

この監査は数値取得と API の整合性を検証したものです。未知の問題に対する精度は別の試験で評価します。26 候補の実モデル検証は Choice のみであり、Score の 10→11 候補における数字から英字への切り替え、および Score 26 候補は、この監査の対象外です。
