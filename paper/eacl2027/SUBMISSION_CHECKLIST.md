# EACL 2027 Demo 提出チェックリスト

確認日：2026-09-20。**著者確認用一式を準備済み・未投稿。** チェック済みの規則と、提出物が規則を満たしたかは別に記録する。未チェック項目は未確認であり、不適合が確定したという意味ではない。

## 期限と窓口

| 項目 | 公式日程／換算 |
|---|---|
| 提出締切 | 2026-09-22 23:59 UTC−12 = **2026-09-23 20:59 JST** |
| 採否通知 | 2026-12-18（公式記載日。通知の実時刻は未確認） |
| Camera-ready | 2027-01-06 23:59 UTC−12 = **2027-01-07 20:59 JST** |
| 会議 | 2027-03-09〜14、Athens, Greece |
| 提出先 | [OpenReview EACL 2027 Demo](https://openreview.net/group?id=eacl.org/EACL/2027/Demo) |

根拠：[Demo CFP](https://2027.eacl.org/calls/demos/)、[会議公式](https://2027.eacl.org/)。Demoへ直接提出する。Main ConferenceのARR日程と混同しない。

## 本人が確認する事項

- [ ] OpenReviewの既存プロフィールID、ログイン、メール確認、**有効化完了**を確認する。現在は本人回答待ち。会社ドメインでも未登録組織なら承認待ちになり得る。最大2週間の案内があるため先に確認する。重複アカウントを作らない。[OpenReview登録案内](https://docs.openreview.net/getting-started/creating-an-openreview-profile/signing-up-for-openreview)
- [x] 著者は **Yuki Oshio / UPHASH Inc. / oshio@uphash.net の単著**。本人が確定した情報を使用する。
- [ ] 実フォームで所在地が必要な場合は正確な表記を確認する。連絡先がOpenReviewで確認済みかは別途確認する。
- [ ] 著者本人が研究上の貢献、重要な内容の批判的改訂、最終版承認、内容への責任を確認する。AIによる監査は人間の確認を代替しない。[ACL著者規程](https://www.aclweb.org/adminwiki/index.php/ACL_Policy_on_Publication_Ethics#Authorship)
- [ ] 自分で主要な問い・方法・結果・限界を説明できるまで原稿を読み、必要な訂正を行う。特に「新手法ではない」「one-tokenへの速度優位なし」「候補確率≠正答確率」「単一モデル/端末」「AI作成local問」「公開dev/汚染不明」を確認する。
- [ ] 査読担当候補に指名する**著者1人**と本人の引受を確定する。単著なら候補はYuki Oshioだが、引受済みではない。Demo CFPには別途の資格閾値・免除手続・査読締切の明示なし。能力・時間・利益相反に懸念があればchairへ確認する（この準備では連絡しない）。[Demo CFP](https://2027.eacl.org/calls/demos/)
- [ ] 査読の守秘義務、利益相反申告、自分で論文を読み論旨を書く責任を理解する。AIに査読の初稿を作らせることは認められていない。[ACL査読規程](https://www.aclweb.org/adminwiki/index.php/ACL_Policy_on_Publication_Ethics#Reviewing)
- [ ] 他会議・workshop・journal・ARRで同稿/大幅重複稿が審査中でないことを本人確認する。既存公開原稿・関連投稿は正直に開示する。[重複投稿規定](https://2027.eacl.org/calls/demos/#multiple-submission-policy)、[ACL規程](https://www.aclweb.org/adminwiki/index.php/ACL_Policy_on_Publication_Ethics#Dual_Submission)

## PDF・動画・配布物

現行PDFは本文6ページ、参考文献込み7ページ。未変更の公式ACL style、A4、全フォント埋込を確認済み。以下3点すべて必須。規則の根拠は[Demo Submission Guidelines](https://2027.eacl.org/calls/demos/#submission-guidelines)。

- [x] 公式形式のPDF。**本文6頁以内**、図を含めて設計・対象利用者・実演・既存との差・評価・入手方法・ライセンスを説明する。参考文献・任意の倫理説明・情報補足用付録は制限外。採択後本文は1頁追加可能。
- [x] **single-blind**として氏名・所属を表示する。主会議の匿名化設定をそのまま適用しない。
- [x] 最大**150秒**の実演動画。音声説明を推奨、凝った編集は不要。公開リンクまたはMPEG4補足提出が可能だが、CFPはPDFとフォーム双方への動画リンク記載も指定している。補足添付方式の場合、実際の添付リンクの扱いをフォームで確認する。
- [x] 実行可能Webデモ、またはインストール可能な配布物のリンクをPDFとフォーム双方に記載する。GitHubトップURLだけをもって起動確認済みとしない。動画のみではこの要件を満たさない。
- [x] 動画・PDF・フォーム下書き・配布物が対応する版を示す（投稿フォームは未入力）。録画後のUI変更は専用ブランチへのフッターリンク修正のみ。予定のUI機能を完成機能として記述しない。

[公式ACL style](https://acl-org.github.io/ACLPUB/formatting.html) と [style files](https://github.com/acl-org/acl-style-files) に基づく確認：

- [x] A4・二段組・本文11pt、フォント埋込、review用の頁番号/行番号。字詰めや余白変更で頁数を削らない。
- [x] Abstractは200語以内。PDFとフォームの題名・要旨・著者情報を同期する。
- [x] 図中の実演例は英語であり、日本語の英訳・ローマ字併記は対象なし。紙面の文字サイズを画像で確認済み。
- [x] `Limitations` と `Acknowledgements` を設ける。Demoの6頁例外はCFPを優先する。両節の扱いに疑義が残る場合は本文6頁内に収める保守的編集とし、一般の匿名査読用「謝辞なし」をAI開示省略の理由にしない。
- [x] 重要な結果・実演説明を任意の付録へ追いやらず、本文だけで評価可能にする。

アクセス試験（実施日時・版・結果を記録）：

- [x] 認証なしで公開PDF・動画・デモ手順・GitHubブランチ・ソースZIPへアクセスし、HTTP 200を確認。取得PDF/動画/手順書と全376ソースファイルがローカル版と一致。PDF中とフォーム下書きの配布リンクを照合済み。署名期限付きURLや招待必須リンクは使用しない。記録は `VALIDATION.json`。
- [x] 動画は全編をデコードして異常なし。135秒、H.264、1280×920、音声トラックなし。全6シーンの代表フレームで文字・字幕・表示内容を確認。再生しての著者本人の最終確認は下記のとおり未了。
- [x] 配布用ソースの別ディレクトリ展開から、8件のCPU試験とUI/bridgeの起動・実モデル推論を確認した。既存の検証済みnative runtime/modelを利用するため、新端末でのモデル取得・nativeビルド一式の再検証とは区別する。対応OS、Python/runtime、モデル取得、容量/RAM、ネットワーク要件は記載済み。
- [x] 3種類の型付き出力を実際に操作できる。保存済み結果を表示する場合は録画/再表示であることを明示し、live推論と混同させない。
- [x] ソース、モデル、外部データの権利を区別する。MITは第三者モデル/データに自動適用しない。外部原文の再配布を避ける現行方針とCC BY-SA等のnoticeを保つ。

## AI利用と研究責任

AI利用は謝辞へ、実装・localデータ作成・文献探索・解析・監査・草稿という実際の範囲を記載する。モデル名は確認できたものだけを記す。AIを著者に含めず、これまでの確認を独立した人間査読と表現しない。[ACL Generative Assistance](https://www.aclweb.org/adminwiki/index.php/ACL_Policy_on_Publication_Ethics#Guidelines_for_Generative_Assistance_in_Authorship)

[EACL Main CFP](https://2027.eacl.org/calls/papers/) は entirely AI-generated papers に言及するが、その割合や判定手順、Demo向けの個別定義は公表文面で確認できない。[Paper Integrity Policy](https://2027.eacl.org/calls/paper-integrity-policy/) は引用検証等を全投稿対象として説明し、Demo CFPはACL倫理規程を明示的に採用している。**AI謝辞を付けただけで適合が保証されるわけではない。** Demoに免除があるとも、AI支援の多い研究が一律不可とも判断しない。

- [ ] 著者本人が主張と寄与の位置付けを批判的に確認し、修正内容を記録する。
- [ ] 主要数値と実験条件を元の表・manifestに照合する。期待値とhard label、歴史runとmatched runを区別する。
- [ ] 原典を読み、本文と引用先が対応し、引用が実在することを確認する。
- [ ] 最終PDF・動画・公開物を本人が確認し、現時点の版への責任と投稿内容に同意する。未実施の確認を完了扱いにしない。

本人確認記録（未記入）：確認日 `____`／PDF SHA-256 `____`／配布版 `____`／確認した内容と訂正 `____`／残る疑問 `____`。

## 投稿画面を開いてから確認する事項

2026-09-20の未ログインWeb取得ではOpenReviewページは`Loading`のみ。同日の親タスクによるブラウザ確認では `Verifying your browser / Complete the check below / Sign in to skip this check` を表示し、認証状態を確認できなかった。challenge回避・サインイン送信は行っていない。**実フォームの項目名・必須属性・文字数/容量上限・宣誓文は未取得。** [FORM_DRAFT.md](FORM_DRAFT.md) は転記用準備であり、画面の再現ではない。

- [ ] アカウント有効化後、タイトル/要旨/著者/添付/リンク/査読担当の実際の入力欄を確認し、CFPと差異があれば解消する。
- [ ] 実画面に現れる利益相反・倫理・著作権・重複投稿・資格等の申告/宣誓を本人が読み、事実に即して回答する。未確認の宣誓に自動同意しない。
- [x] PDFに仮のURL・未確定所属・TODOがなく、必須リンクを含むことを確認する。
- [ ] 最終投稿を明示的に実施する段階で、受付ID・時刻・アップロード版の一致を保存する。現在は外部送信していない。

日程上、EACL採否通知よりNAACL 2027 Demo締切（2026-12-05 20:59 JST）が先。結果を待って同年NAACL Demoへ移すことはできない。同稿を移す場合は先にEACLの正式撤回が必要。[NAACL Demo CFP](https://2027.naacl.org/calls/system_demonstration/)
