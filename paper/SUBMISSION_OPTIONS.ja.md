# Mini Jev の投稿先・締切・開催地

確認日: **2026年9月20日（Asia/Tokyo）**。学会・学会誌・ワークショップ主催者の公式資料で確認した。本文の評価は `README.md` と `MANUSCRIPT.md` v0.2 を読んだうえでの判断であり、採択可能性の数値予測ではない。

**準備期間を確保できる第1候補は NAACL 2027 の System Demonstrations。研究論文枠なら、実証結果を軸に TMLR または ARR 経由の国際会議を候補とする。** 最速の EACL Demo は日本時間9月23日締切だが、6ページ原稿だけでなく実演動画も必要になる。NLP2027 は国内で議論を得る候補だが、投稿期限はまだ確認できない。

v0.2では、動く実装と再現資料、既存2,400問、外部4タスク900例、同一モデルでの3方式4,050リクエスト比較、負の学習結果、確率指標の検証が揃った。直接読み出しと1トークン生成の速度差は明確でなく、JSON生成は遅く品質の増減もタスクによる、という実証結果を中心に据える。複数モデル・複数機器での一般化や独立した人のレビューは未実施である。既存の候補logit分類を新アルゴリズムとして売る本会議戦略は採らない。

## 締切が公表されている候補

**AoE は UTC−12。23:59 AoE は翌日20:59 JST。** 下表の「将来締切」は締切が公表済みという意味で、現在投稿ボタンを押せることまでは示さない。抄録について「別締切なし」は、公式CFPに独立した事前登録期限が掲載されていないという意味。

| 候補・トラック | 状態 | 抄録・本文の公式締切 → 日本時間 | 開催日・開催地 | Mini Jev との適合・必要な補強 |
|---|---|---|---|---|
| **EACL 2027 System Demonstrations** | **受付中・近締切**（8/18開始） | 抄録: 別締切なし。本文: **2026/9/22 23:59 AoE → 9/23 20:59 JST** | **2027/3/9–14、アテネ／ギリシャ** | 公開研究プロトタイプと適合。6頁以内、2.5分以内の実演動画、live demo または配布パッケージが必須。実演の有用性と比較を示す必要がある。採択後は発表者登録とlive demoが必要。[公式CFP](https://2027.eacl.org/calls/demos/)・[開催地](https://2027.eacl.org/) |
| **NAACL 2027 System Demonstrations** | **受付前・締切確定**（11/1開始） | 抄録: 別締切なし。本文: **2026/12/4 23:59 AoE → 12/5 20:59 JST** | **2027/6/1–5、サンフランシスコ／米国** | **準備期間込みの第1候補。** 完了した比較実験と利用場面を、6頁＋動画＋動作する配布物にまとめる。公式CFPは単なるAPIラップや既存モデルの組合せだけでは不十分と明記。[公式CFP](https://2027.naacl.org/calls/system_demonstration/) |
| **COLING 2027 Main、long / short** | **将来締切・公表済み** | 抄録: 別締切なし。ARR本文: **2026/10/12 23:59 AoE → 10/13 20:59 JST**。会議commit: **12/23 23:59 AoE → 12/24 20:59 JST** | **2027/5/9–14、マカオ／中国**。オンライン発表は**5/6–7** | 外部評価、対照実験、失敗分析を中心にした実証論文の候補。現状をそのまま出すより、研究上の知見を増やしたい。long 8頁／short 4頁。[公式CFP](https://2027.coling-iccl.org/calls/main_conference_papers/)・[時刻・開催地](https://2027.coling-iccl.org/) |
| **NAACL 2027 Main、long / short（Findingsを含む審査経路）** | **将来締切・公表済み** | 抄録: 別締切なし。ARR本文: **2026/10/12 23:59 AoE → 10/13 20:59 JST**。会議commit: **12/23 23:59 AoE → 12/24 20:59 JST** | **2027/6/1–5、サンフランシスコ／米国**。本会議は対面・オンライン発表あり | 推論時手法・評価・再現性に適合するが、明確な研究貢献が必要。COLINGと同じARR周期なので重複投稿する必要はない。[公式CFP](https://2027.naacl.org/calls/main_conference_papers/)・[公式FAQ](https://2027.naacl.org/faq/) |
| **TMLR（Transactions on Machine Learning Research）** | **随時投稿** | 抄録事前登録・会議一斉締切なし。rolling submission。JST換算対象なし | **オンライン学術誌。開催日・開催都市なし** | **研究論文枠の候補。** 手法の新規性より、正確な証拠と読者に役立つ知見を重視する。ただし単なる既存手法の再実装では不十分。著者別投稿quotaあり。[公式案内](https://jmlr.org/tmlr/)・[採択基準](https://jmlr.org/tmlr/acceptance-criteria.html)・[投稿規定](https://jmlr.org/tmlr/editorial-policies.html) |

## 開催は公表済み、投稿条件は未確定の候補

| 候補・トラック | 状態・締切 | 開催日・開催地 | 位置づけと公式根拠 |
|---|---|---|---|
| **ACL 2027 Main／Findingsを想定** | **具体的CFP・日付未公表。** ARR公式表には最終ARR投稿時期として**2027年1月**のみ記載。抄録、具体日、時刻、commit日は未確認。JST換算しない | **2027/8/17–22、京都／日本** | 比較実験と一般化の検証を積む中期目標。月だけの予告を確定締切として扱わない。[公式サイト](https://2027.aclweb.org/)・[ARR日程表](https://aclrollingreview.org/dates) |
| **言語処理学会第33回年次大会 NLP2027、一般発表を想定** | **発表募集・申込／原稿締切未確認。** 日付や原稿形式を前年から推定しない | **2027/3/15–19、福岡国際会議場／福岡・日本＋オンライン** | 日本語評価と実装について国内の研究者から意見を得る候補。国際査読会議と同じ区分では扱わず、2027年CFPで発表・審査方式を確認する。[学会公式案内](https://www.anlp.jp/guide/nenji.html) |
| **ICLR 2027 の関連ワークショップ（個別名称未決定）** | **個別CFP未公表。** 主催者向け資料の**2027/2/1は推奨投稿日**であり、個別論文の確定締切ではない。時刻も未指定のためJST換算しない | **2027/4/29–30、サンフランシスコ／米国**。個別WSはこのうち1日 | calibration・evaluation・efficient inferenceに合う採択WSが公表されれば候補。名称とCFPを確かめて選ぶ。[公式WS募集](https://www.iclr.cc/Conferences/2027/CallForWorkshops)・[2027日程表](https://iclr.cc/Conferences/2027/Dates) |

## 関連はあるが、今回は新規投稿できない候補

| 候補 | 終了した締切 | 開催日・開催地 | 判断 |
|---|---|---|---|
| **ICLR 2027 Main** | **必須抄録: 2026/9/18 23:59 AoE → 9/19 20:59 JST、終了。** 本文は9/25 23:59 AoE → 9/26 20:59 JST | 本会議 **2027/4/26–28**、全体4/26–30。サンフランシスコ／米国 | **事前抄録登録済みでなければ新規投稿不可。** 本文期限だけを見て「まだ間に合う」としない。現状の新規性・実験規模からも優先しない。[公式著者規定](https://iclr.cc/Conferences/2027/AuthorGuidelines)・[日程](https://iclr.cc/Conferences/2027/Dates) |
| **NeurIPS 2026 On-Device Intelligence（ODI）Workshop** | 8/29から延長後の**2026/9/5 23:59 AoE → 9/6 20:59 JST、終了** | **2026/12/12、ICC Sydney／シドニー・オーストラリア** | ローカル推論・計測として内容の相性はよいが受付終了。2027年の同名開催は仮定しない。5頁・non-archivalだった。[公式CFP](https://odi2026.github.io/)・[公式日程データ](https://odi2026.github.io/content/dates.md)・[公式開催情報](https://odi2026.github.io/content/hero.md) |

NeurIPS 2026については、全WSが終了したと一括断定しない。例えば[Agentic AI for Biological Discovery](https://agenticls.github.io/)は9月26日AoEまでの募集を掲げるが、現在のMini Jevには生物研究上の貢献がないため推薦対象に含めなかった。近い締切に合わせるためだけにテーマを変える理由はない。

## 投稿経路で気を付ける具体点

- **ARRは会議ではなく査読サービス。** 次回は10月12日締切、2027年1月は月のみ公表。ARRに提出して査読・meta-reviewを受けた後、COLINGまたはNAACLへcommitする。同じ原稿を両会議の第一希望に同時commitはできない。第二希望への考慮は保証されない。[ARR日程](https://aclrollingreview.org/dates)・[NAACLの説明](https://2027.naacl.org/calls/main_conference_papers/)
- **EACL 2027本会議は今回の新規原稿には遅い。** 最終ARR締切は8月3日で終了しており、10月11日のcommit期限は未査読原稿の新規投稿期限ではない。Demoは別募集のため9月22日まで可能。[本会議CFP](https://2027.eacl.org/calls/papers/)
- **同じ内容でDemoとARRを並行審査に出さない。** EACL／NAACLのDemo CFPはいずれもARRを含む重複審査を禁じている。EACL Demoに出す場合、審査結果前の10月ARR投稿と両立する前提では計画しない。[EACL Demo規定](https://2027.eacl.org/calls/demos/)・[NAACL Demo規定](https://2027.naacl.org/calls/system_demonstration/)
- **TMLRを後の増補版の行き先と決め打ちしない。** 同誌は既存のarchival査読済み会議論文の拡張版を認めず、文章・図・結果の再利用にも制限がある。公開GitHubやpreprint、明示的non-archival WSとの重複は別扱い。[TMLR投稿規定](https://jmlr.org/tmlr/editorial-policies.html)

## 公式資料間の不一致と扱い

1. **ICLR WS募集ページの冒頭に「April 29 and 30, 2026」とある。** 同ページの対象はICLR2027で、公式2027トップは4/26–30、日程表はWS 4/29–30を示す。本表は2027年として記録し、年の誤記と思われる箇所があることを残した。都市はWS募集本文のSan Franciscoを根拠にした。トップの会場詳細には未掲載表示が残るため、建物名は確定情報に含めない。[WS募集](https://www.iclr.cc/Conferences/2027/CallForWorkshops)・[トップ](https://iclr.cc/Conferences/2027)・[日程](https://iclr.cc/Conferences/2027/Dates)
2. **NAACL CFPとARR表で著者reviewer登録日が異なる。** NAACLは10/12、ARRは10/14。meta-review公開もNAACL 12/18、ARR 12/17と異なる。論文本体締切10/12とcommit 12/23は一致する。準備上は早い10/12までに登録を完了する計画とし、実際の投稿画面・通知で再確認する。[NAACL CFP](https://2027.naacl.org/calls/main_conference_papers/)・[ARR表](https://aclrollingreview.org/dates)
3. **ODIの初期告知は8/29だったが公式の現在データは9/5への延長とClosedを記載。** サイトはブラウザでMarkdownを読み込む構成のため、公式ページ自身が参照する `content/dates.md`、`content/topics.md`、`content/hero.md`を確認した。開催日は12/12に具体化している。[日程](https://odi2026.github.io/content/dates.md)・[CFP](https://odi2026.github.io/content/topics.md)

実行順の推奨は、**完了した比較を軸にNAACL Demo向けの6頁と動画を作る**、または**実証結果と読者に役立つ知見を中心にTMLR／ARR経由に一本化する**。EACL Demoは必要資料とOpenReviewプロフィールが既に用意できる場合の最短案であり、締切だけを理由に証拠の弱い原稿を送る案ではない。この一覧作成時点で投稿・登録・支払いは行っていない。
