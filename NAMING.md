# LogitTrail — name and version mapping

On 29 September 2026, the UPHASH project previously called **Mini Jev** adopted the name **LogitTrail** (ロジットトレイル). The name describes inspecting candidate scores and tracing decisions to recorded evidence. It does not promise calibrated correctness, error prevention, or a new scoring algorithm.

The change avoids confusion with the distinct [r-ms/mini-jev](https://github.com/r-ms/mini-jev) project by Mikhail Rakutko, which provides a frozen-model letter-logit/JSON experiment and inspection bench. It is cited as related work; the naming change does not assert a code derivation or affiliation. TypeSafe's Jev remains the interface inspiration, with no claim to reproduce its architecture, training, or performance.

## Current entry points

- Project and saved-record explorer: <https://uphash-network.github.io/mini-jev/> and <https://uphash-network.github.io/mini-jev/explorer/>.
- Current source: <https://github.com/UpHash-Network/mini-jev/tree/research/naacl2027-demo>.
- Current manuscript: **LogitTrail: An Inspectable Local Interface for Typed Decisions from Frozen Language Models**, [PDF](https://uphash-network.github.io/mini-jev/assets/LogitTrail_Manuscript.pdf).
- Updated 60-second walkthrough: [video](https://uphash-network.github.io/mini-jev/assets/LogitTrail_60s.mp4).

The repository and Pages URL deliberately retain `mini-jev` as a compatibility address. GitHub repository renames do not redirect project Pages URLs, so changing that address would break links in submitted documents and existing posts. The visible project name is LogitTrail.

## Historical records

The preprint submitted to arXiv on 26 September retains the original **Mini Jev** title and submitted package. At this revision it is awaiting moderation, with no verified public arXiv identifier. The LogitTrail conference-preparation PDF is a later revision, not an arXiv replacement or evidence of conference acceptance.

The September 27 manuscript PDF, original videos, frozen source/evidence ZIP, original research observations, model fingerprints, and prior publication receipts remain unchanged. The old interface shown in a recorded video or paper figure is explicitly identified as historical. The new short video reuses the same measured evidence and an identified archival clip; it is not a new inference experiment.

Legacy source/API identifiers, including `MiniJev`, `mini_jev.py`, the `X-Mini-Jev-Demo` header, exported record formats, and ZIP member paths remain compatible. Their spelling does not indicate a different current project.

Use the new name for the current software and manuscript. Cite the actual historical title when referring to a specific earlier version. Past social posts remain dated publication records; future announcements should say **LogitTrail (formerly Mini Jev)** where the distinction matters.

## 日本語

2026年9月29日より公開名を **LogitTrail** に変更しました。候補確率と判断記録を追跡・検査するという機能を表します。同名の別プロジェクト r-ms/mini-jev との混同を避けるための変更です。

既存の論文・SNS・ブックマークからのリンクを維持するため、URLと互換用の内部識別子は従来どおりです。現在の案内・UI・論文改訂版・短い紹介動画は新名称に統一し、提出済みarXivや過去の測定・動画・出版記録は元の名前と内容を残しています。名称変更に伴う追加学習・推論・性能改善はありません。
