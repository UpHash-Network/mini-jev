> Public-release clarification: “manual”, “handwritten”, “手書き”, and “independent reviewer” in these historical records refer to individual writing/review by separate AI agents, not human expert annotation or external independent evaluation. See [DATA_CARD.md](../DATA_CARD.md) for scope and provenance.

# 新規の検証用質問 2,400問

[CSV](questions_2400.csv) と [JSONL](questions_2400.jsonl) に、同じ2,400問を保存しています。
Choice・Noul・Scoreが各800問です。手書き180問と生成2,220問を含み、校正専用の120問は含みません。

各問題にはID、型、出典、family、状態、質問、選択肢、正解があります。CSVはUTF-8 BOM付きです。
CSVのstate・criteria・label列はJSONで表現し、JSONLとの往復一致を検証しています。
手書き問題の分類は原本のtagをfamily列にも補完しています。状態・質問・候補・正解は原本から変更していません。

この問題群は旧版の失敗後に作成した別の受け入れ試験です。旧版との完全重複と生成問題の意味上の重複を検査し、異なる担当者が正解を監査しました。
手書き問題の監査は [MANUAL_AUDIT.json](MANUAL_AUDIT.json)、独立確認は [MANUAL_PEER_REVIEW.json](MANUAL_PEER_REVIEW.json) を参照してください。
固定ファイルのハッシュと件数は [EXPORT_MANIFEST.json](EXPORT_MANIFEST.json) に記録しています。

これらは短い日本語の条件判断・照合・集計などを対象にした検証です。2,400種類の業務領域をカバーするものではありません。
familyごとの成績を併記し、生成問題数だけで汎用性を主張しません。
