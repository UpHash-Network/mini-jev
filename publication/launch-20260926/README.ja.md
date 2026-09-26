# Mini Jev 公開告知パッケージ

2026-09-26 作成。日本語・英語の X 原稿、Reddit 用の技術説明原稿、公開後の URL 差し替えツールをまとめています。**このパッケージの作成は外部投稿・予約投稿を意味しません。**

## 使う原稿

- [X 原稿一覧](X_POSTS.md): 日本語・英語それぞれ、単独投稿と 5 投稿スレッド。現在用と arXiv 公開後用を分離。
- [X の構造化原稿](x-posts.json): 生成処理の入力。`{{ARXIV_URL}}` が公開後版だけに存在。
- [Reddit 完成稿](reddit-machinelearning-update.md): r/MachineLearning の公式 Self-Promotion Thread の既存コメントへの研究進捗返信。無料、所属、AI 支援、査読前、実測した変化を明記。
- [Reddit のルール確認](REDDIT_RULES.ja.md): 公式紹介スレッドによる明示的な募集を確認。独立した宣伝投稿と r/LocalLLaMA は使いません。[LocalLLaMA 向け参考稿](reddit-localllama-body.md)は投稿しない資料です。
- [オフライン生成スクリプト](render_release.py): 公開 URL の形式検証、差し替え、X 文字数検証。
- [検証記録](VALIDATION.json): 公式 `twitter-text` 3.1.0 による X 全 24 投稿の検証と、URL 検証の結果。

単独投稿とスレッドは選択肢です。同じ言語の両方を重複告知として出す想定ではありません。おすすめは日本語スレッドを主投稿にし、英語版は別時間帯に内容が重複する旨がわかる形で使うことです。具体的な投稿時間に効果があるという予測は置いていません。

冒頭投稿には短い動画を添付できます。動画は録画 UI と保存済み評価を使った説明であり、新しいライブ推論や 26,050 件全体のリアルタイム再生と説明しません。制作物は [video/](video/) と公開ページの `assets/Mini_Jev_60s.mp4` を参照してください。

## 今使える版の生成

リポジトリのルートから実行します。出力先は新規ディレクトリを指定してください。

```sh
python3 publication/launch-20260926/render_release.py \
  --stage now \
  --output-dir /tmp/mini-jev-launch-now
```

この版は既存の [プロジェクトページ](https://uphash-network.github.io/mini-jev/)を案内します。arXiv 公開済みという表現や内部受付番号は使いません。

## arXiv 公開時の確認・差し替え

1. arXiv の受領メールではなく、公開の通知と公開 abstract ページを確認する。
2. 公開ページでタイトルが **Mini Jev: An Inspectable Local Interface for Typed Decisions from Frozen Language Models**、著者が **Yuki Oshio** であることを確認する。
3. `https://arxiv.org/abs/YYMM.NNNNN` 形式の URL を取得する。`submit/8130148` は受付番号であり公開 ID に使わない。
4. GitHub Pages の論文リンク・公開ステータス・引用情報を同じ版に揃える。動画・コード・再現手順が開けることを確認する。
5. 下記コマンドで `PUBLIC_ABSTRACT_URL` を実在する公開 URL に置き換えて生成する。スクリプトはネットワーク接続せず、URL の実在や内容の一致を証明しない。
6. 出力された X 原稿と動画の説明を読み合わせ、投稿する言語・単独投稿またはスレッドを選ぶ。Reddit は [ルール確認](REDDIT_RULES.ja.md)に記録した公式紹介スレッドの既存コメントへの返信として使い、当日のスレッド・コメント状態を確認する。
7. 実際に投稿した場合だけ、投稿 URL・日時・使用版を記録する。公開、投稿、査読採択を混同しない。

```sh
python3 publication/launch-20260926/render_release.py \
  --stage announced \
  --arxiv-url PUBLIC_ABSTRACT_URL \
  --public-page-checked \
  --output-dir /tmp/mini-jev-launch-announced
```

`--public-page-checked` は上の確認を実施した記録です。形式だけ正しい架空 URL を公開済みとみなすための指定ではありません。スクリプトは `/submit/`、PDF URL、別ドメイン、クエリ付き URL、未解決のプレースホルダー、X の上限超過を拒否します。

## 伝える主張と裏付け

| 告知中の主張 | 提出原稿での位置・条件 |
|---|---|
| 凍結モデル、追加ヘッド学習なし | §2.2。ネイティブ配布設定の説明。別の実験的学習パスとは区別。 |
| 候補確率は正答確率ではない | §2.1。候補集合内で正規化。集中度は正解の保証ではない。 |
| 26,050 リクエスト | §4.5。4,050 + 7,600 + 14,400。独立問題数ではない。 |
| 1,350 組で同一、速度優位なし | §4.2。同一プレフィックス・候補・モデルでの比較。 |
| 安定していても誤り・定数予測がある | §4.4。特に 1.5B の最初の JCoLA 200 件では 42 誤り。後続パネルの 0.5B / 78.5% と混同しない。 |
| Mac 64 GB、約 20.4 GB のモデル | §3。実測環境であって最小要件や全 Mac での動作保証ではない。 |

審査・公開待ちの提出原稿を修正したとは記載しません。先行研究追加を含む次の改訂版ができても、どの版を紹介するかを明示します。

## 原稿の文字数

[X 公式の文字数仕様](https://docs.x.com/fundamentals/counting-characters)に従い、日本語の重み 2、通常の欧文の重み 1、URL の重み 23 を使用しています。絵文字は使っていません。公式実装でも 24 投稿すべてを検証し、最大 259 / 280 でした。添付メディアは公式クライアントで追加する想定です。
