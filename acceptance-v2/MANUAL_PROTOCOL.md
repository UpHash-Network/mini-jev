> Public-release clarification: “manual”, “handwritten”, “手書き”, and “independent reviewer” in these historical records refer to individual writing/review by separate AI agents, not human expert annotation or external independent evaluation. See [DATA_CARD.md](../DATA_CARD.md) for scope and provenance.

# 第2回独立受入試験の手書き問題

`private/acceptance_test.jsonl` は180問、`private/calibration.jsonl` は120問。それぞれChoice/Noul/Scoreを60問、40問ずつ含む。本文・正解はモデル選定から隔離する。

v1で診断した論理能力を減らさないため、各型のfamily件数、候補数・段階数の分布、自然文と構造化stateの件数をv1と完全に合わせた。Choiceはキー整列後の正解位置を候補数ごとに最大1件差にし、Noulは正負を均等にした。手書き試験は26family、校正用は27familyを維持する。長い記録を含む問題は9問。

新しい問題は、創作・展示・舞台・庭・遊戯・探索・観察など、別の出来事と評価尺度から手書きした。同じ抽象的な論理能力を使うことは意図的であり、全て新しい能力を測るという意味ではない。v1全2520問との完全一致、v2手書き・校正内の完全重複は0件。数字を正規化した文字3-gramによる近似検索の上位も確認した。文字列照合だけで意味の独立性を保証できるわけではない。

作成者はv1の先頭400件を診断した後にこの問題集を作成した。以後のモデル予測、新しいモデルの選定情報、v2の予測は参照していない。v1の誤りfamilyを削ったり、完成基準を変更したりしていない。

モデル・重み・プロンプト・推論方式・校正手順を決めてから校正データを用い、校正結果も固定した後に最終テストを一度行う。合否は既存の `COMPLETION_CRITERIA.md` に従う。生成2220問と合わせる場合も、手書き180問は独立に集計する。

これは限定されたローカル判定器の受入試験であり、汎用的な正解率や本家Jevと同等の能力を保証するものではない。
