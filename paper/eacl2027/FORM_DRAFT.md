# EACL 2027 Demo — 投稿情報の下書き

状態：**未投稿／実フォーム未確認**。2026-09-20。

[公式提出先](https://openreview.net/group?id=eacl.org/EACL/2027/Demo) の未ログイン取得は`Loading`のみだった。親タスクのブラウザ確認でもbrowser verification画面が表示され、認証状態・実フォームは未確認。以下の区分は準備用で、実画面の項目名・必須欄を推測したものではない。実画面で転記先、文字数/ファイル容量上限、選択肢、宣誓文を確認する。根拠：[Demo CFP](https://2027.eacl.org/calls/demos/)。

## 基本情報

| 情報 | 下書き／確認状況 |
|---|---|
| 会議・track | EACL 2027 System Demonstrations |
| 著者 | **Yuki Oshio（単著、本人確定）** |
| 連絡先 | oshio@uphash.net（ユーザー指定。OpenReview確認済みメールかは未確認） |
| 所属 | **UPHASH Inc.（本人確定）** |
| 所在地 | 未確認。実フォームで必要な場合に確認 |
| OpenReview profile ID / 有効化 | **本人確認待ち** |
| 投稿PDF | [`EACL2027_Mini_Jev_Draft.pdf`](EACL2027_Mini_Jev_Draft.pdf)、7ページ（本文6ページ）、SHA-256 `0fc182d22514f07347e3b81cf6181a587fc66c299605e4df396ea07410ab63ba` |
| 査読担当候補の著者 | Yuki Oshio（仮。本人の引受未確認） |
| 発表担当 | 未確認。採択後の登録・live demoとposterへの対応を確認 |

## 題名・要旨（著者確認用）

2026-09-20のPDFソースと同期済み（要旨153語）。著者による最終確認は未了。

Title:

> Mini Jev: An Inspectable Local Interface for Typed Decisions from Frozen Language Models

Abstract:

> Many language-model applications need a small typed decision rather than free-form text. Mini Jev is an open-source local interface that maps a state and explicit criteria to a categorical choice, a true-candidate probability, or an expected ordinal stage. It uses candidate next-token logits from a frozen language model, with no trained decision head. A browser demonstration exposes typed values, candidate distributions, probability semantics, and request/response JSON. Its purpose is to make both the decision and its limitations inspectable. Accompanying artifacts distinguish a 2,400-item self-authored Japanese regression suite from public external evaluation and a 4,050-request matched comparison. Direct readout and native one-token selection agree in all 1,350 pairs; the primary latency interval across 150 local items includes zero. Grammar-constrained JSON is slower in this session, under a different serialization prompt. The contribution is a runnable demonstration and auditable empirical record, not a new learning method or a claim that concentrated candidate probabilities establish correctness.

Keywords候補（フォームに欄がある場合のみ）：typed decisions; language model inspection; constrained decoding; reproducibility; calibration。

## リンク・添付

| 情報 | 候補／残る作業 |
|---|---|
| 公開リポジトリ | https://github.com/UpHash-Network/mini-jev/tree/research/eacl2027-demo |
| インストール可能なデモ配布物 | https://github.com/UpHash-Network/mini-jev/archive/refs/heads/research/eacl2027-demo.zip — 起動手順は [`demo/README.md`](../../demo/README.md)。対応する確定commitと検証範囲は検査記録に記載 |
| WebデモURL | インストール可能な配布物方式。起動後のローカルURLは `http://127.0.0.1:8766/`（外部公開Webホストは用意していない） |
| 150秒以内の動画URL | https://raw.githubusercontent.com/UpHash-Network/mini-jev/refs/heads/research/eacl2027-demo/paper/eacl2027/Mini_Jev_Demonstration.mp4 — 135秒、英語字幕、音声なし。PDF中と同じURL |
| MPEG4添付 | [`Mini_Jev_Demonstration.mp4`](Mini_Jev_Demonstration.mp4)、2,975,547 bytes。添付欄の有無・容量とリンクの扱いは実画面で確認 |
| その他の補足 | 本文で説明する再現用資料だけを選び、権利・実行手順・版を添える。必須欄や容量は未確認 |

## 開示用の内容案

実際に対応する欄があれば転記する。存在しない欄や必須宣誓を作らない。

**AI支援の開示案（Acknowledgementsにも同期）：**

> AI coding agents accessed through OpenAI Codex assisted with implementation, question authoring, software checks, experiment execution, analysis, literature organization, and manuscript drafting under the author's direction. The independent numerical audit was performed by another AI agent; it is not independent human review. We do not claim human-expert validation of the AI-authored evaluation items. The author is responsible for the submitted manuscript and its claims.

利用ツールと支援範囲は原稿と同期済み。著者本人の寄与・責任については最終確認が必要。「著者が全て検証済み」という文は本人による確認完了まで加えない。形式的な謝辞だけで投稿方針への適合を保証しない。[ACLのAI・著者規程](https://www.aclweb.org/adminwiki/index.php/ACL_Policy_on_Publication_Ethics#Guidelines_for_Generative_Assistance_in_Authorship)

**既存公開物：** GitHub上の技術報告、原稿、コード、結果記録が先行して公開されている。査読採択実績として表現しない。本人の他投稿・公刊の有無を確認し、必要なら正確なURLと差分を開示する。

**ライセンス：** Project-authored code/local evaluation material: MIT. Third-party models, runtime components, and external benchmark material retain their respective licenses; JGLUE/JCoLA-derived records follow the repository's CC BY-SA notices. Model weights and benchmark source text are not bundled with the source release. 配布物には既存のライセンス・noticeを保持している。

**評価上の限界：** 1モデル・1端末・1セッション、公開devの事前学習混入不明、同じタスクfamily内の依存、AIによるlocalデータ作成、確率指標のタスク依存を明記する。

## 本人の確定が必要な情報

- OpenReview profile IDと有効化状態、確認済みメール、必要な場合の所在地。著者・単著・所属の意思決定は確定済み。
- 査読担当の引受、利益相反、他投稿との重複、引用/ライセンス/内容への確認と責任。
- 最終PDF・動画・配布物の版への承認。実際の画面に出た申告・宣誓の正確な文面への回答。

PDF・字幕動画・デモソースは完成し、著者確認用に準備済み。本人確認・実フォーム入力・宣誓・最終投稿は未実施。アカウント作成やメール送信も実施していない。
