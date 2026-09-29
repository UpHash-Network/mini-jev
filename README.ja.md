# LogitTrail

**2026年9月29日：Mini JevからLogitTrailへ改名しました。** [r-ms/mini-jev](https://github.com/r-ms/mini-jev)との混同を避けるためです。URLとAPIの互換性を維持し、提出済みarXivと過去の記録は旧名で保存しています。[改名と版の対応](NAMING.md)。

**凍結したローカルLLMから、型付き判断と候補の確率を取り出して確認するツールです。**

[English](https://github.com/UpHash-Network/mini-jev/blob/main/README.md) · [研究紹介ページ](https://uphash-network.github.io/mini-jev/) · [現行の研究ブランチ](https://github.com/UpHash-Network/mini-jev/tree/research/naacl2027-demo)

状態と明示した基準から、選択肢を返す**Choice**、true候補の確率を返す**Noul**、段階の期待値を返す**Score**を計算します。ブラウザUIで候補分布・確率の集中度・実際のリクエストと応答JSONを確認できます。公開ネイティブ版は凍結モデルを使い、判断用headの追加学習は行っていません。

**2026年9月27日時点：arXivへ投稿済み、モデレーション待ちです。公開arXiv IDはまだありません。** 学会向け原稿はNAACL 2027 System Demonstrationsへの投稿準備中で、未投稿・未採択・未査読です。現行の研究用ソースは **`research/naacl2027-demo`** ブランチにあります。

## 読む・見る・再現する

| 入口 | 内容 |
|---|---|
| [実験記録の比較画面](https://uphash-network.github.io/mini-jev/explorer/) | 条件・候補確率・共有する推論を比較し、元記録への参照付きJSONを保存。9月28日追加。ライブ推論ではありません |
| [最新原稿PDF](https://uphash-network.github.io/mini-jev/assets/LogitTrail_Manuscript.pdf) | 手法・評価・先行研究・限界 |
| [60秒の実験結果解説](https://uphash-network.github.io/mini-jev/#demo) | 保存済み実験記録から説明する短い動画。新たなライブ実行ではありません |
| [145秒の操作動画](https://uphash-network.github.io/mini-jev/assets/Mini_Jev_Demonstration.mp4) | ローカルUIの操作を収録した字幕付き動画。末尾に以前のブランチ名が残っています |
| [解析再現手順とソース・証拠ZIP](https://github.com/UpHash-Network/mini-jev/blob/research/naacl2027-demo/paper/naacl2027/reproducibility/README.md) | モデル不要の再解析、ビルド検証記録、成果物のハッシュ |
| [ネイティブ起動手順](https://github.com/UpHash-Network/mini-jev/blob/research/naacl2027-demo/README.ja.md#起動) | 実行系のビルド、モデルの取得、API起動 |
| [ブラウザUIの起動手順](https://github.com/UpHash-Network/mini-jev/blob/research/naacl2027-demo/demo/README.md) | ライブ推論、型付き出力とJSONの確認 |
| [検証ガイド](https://github.com/UpHash-Network/mini-jev/blob/research/naacl2027-demo/paper/naacl2027/nonhuman_revision_20260927/REVIEWER_GUIDE.md) | モデル不要の整合性・件数確認とLMQLの後解析 |

## 現行論文で分かったこと

- 直接読出しと1トークン生成は、**1,350組すべてでラベル・logitsが一致**。速度優位性は確認されませんでした。
- 比較・提示方法の感度・確率平均の3研究で**26,050リクエスト**を測定しています。独立した26,050問ではありません。
- 提示方法に対して回答が安定していても、誤答やほぼ一定の回答になる場合があります。確率平均は複数回のモデル呼出しが必要で、品質が一貫して改善するわけではありません。
- 保存済み記録からの再解析で**56 / 56の派生ファイルがバイト単位で一致**しました。別の機器での独立した実験の再現ではありません。

品質評価は1台のApple Silicon Mac上での日本語公開データの部分集合です。学習時のデータ混入は不明で、人間の利用者評価は未実施です。別の2,400問のAI自作評価は初期の検証記録です。[論文と評価範囲の案内](https://github.com/UpHash-Network/mini-jev/blob/research/naacl2027-demo/paper/naacl2027/README.md)をご確認ください。

9月27日の改訂では比較付録と、保存済みLMQL 12例の後解析を追加しました。元の確率公差を超えた3例はそのまま報告しています。公開API・画面で確認できるのは型付き値・候補確率・意味メタデータです。候補token IDと生logitは内部エンジン・研究記録に保持されます。新たな推論結果や人の利用者評価は追加していません。

## 現行版を動かす

```sh
git clone --branch research/naacl2027-demo --single-branch https://github.com/UpHash-Network/mini-jev.git
cd mini-jev
```

続いて[ネイティブ起動手順](https://github.com/UpHash-Network/mini-jev/blob/research/naacl2027-demo/README.ja.md#起動)へ進みます。実測環境はApple M5 Pro、64 GBメモリ、macOS 26.4です。Python 3.10以上、Xcode command-line tools、CMake、Gitと約20.4 GBのモデル取得が必要です。重み・実行バイナリは同梱しておらず、低メモリ機での動作は未検証です。[CPUだけでの解析再現](https://github.com/UpHash-Network/mini-jev/blob/research/naacl2027-demo/paper/naacl2027/reproducibility/README.md)にはモデルは不要です。

確率は指定候補内で正規化した値です。集中度は正解確率ではありません。TypeSafeのJev公開APIを参考にした独立プロジェクトで、TypeSafeとの関係や本家の内部構造・学習・校正・速度の再現は主張しません。候補logitsの利用と期待値スコアには先行研究があり、本研究の貢献は中身を確認できる実装と検証可能な評価です。

[不具合・再現結果を報告](https://github.com/UpHash-Network/mini-jev/issues) · [原稿のBibTeX](https://uphash-network.github.io/mini-jev/citation.bib) · [ソフトウェアの引用情報](https://github.com/UpHash-Network/mini-jev/blob/research/naacl2027-demo/CITATION.cff)

自作コード・作成データは[MIT](https://github.com/UpHash-Network/mini-jev/blob/research/naacl2027-demo/LICENSE)。データセット由来の記録・第三者成果物には各ライセンスと出典表記が適用されます：[NOTICE](https://github.com/UpHash-Network/mini-jev/blob/research/naacl2027-demo/NOTICE.md)。
