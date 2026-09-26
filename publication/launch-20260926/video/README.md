# 60-second evidence walkthrough

[Watch](https://uphash-network.github.io/mini-jev/assets/Mini_Jev_60s.mp4) · [Project page](https://uphash-network.github.io/mini-jev/) · [Provenance](PROVENANCE.json) · [Exact evidence](EVIDENCE.json)

60.00 seconds, 1920 × 1080, H.264, 25 fps, silent, with embedded English explanatory text. This is an edited walkthrough combining an **archival real-time interface recording** with **visualizations of frozen study records**. It is not a new live experiment. The UI excerpt uses Qwen3.6-35B-A3B and English support examples; the later evidence cards describe a separate Qwen2.5-1.5B-Instruct JCoLA study.

On the first 200-item JCoLA panel, Qwen2.5-1.5B predicted acceptable for all 200 items, before and after display reversal. There were zero label flips and 42 errors (158 correct, 79%). The illustrative error was selected as the highest baseline P(true) among those 42 errors; it is not randomly sampled. A candidate probability is not a calibrated probability of correctness. The original dataset sentence is not reproduced.

The video and poster have not been posted to X or Reddit by this preparation step. No arXiv public identifier or conference acceptance is asserted in the video.

## Timing and English transcript

| Time | Content |
|---|---|
| 0–6 s | Same answer. Still wrong. Inspect typed decisions, candidate probabilities, and failure cases from frozen local language models. |
| 6–18 s | Archival live recording: run Choice, Noul, and Score; inspect the candidate distributions. |
| 18–32 s | Archived Qwen2.5-1.5B JCoLA panel: every sentence was called acceptable; zero labels changed after reversal, yet 42 of 200 answers were incorrect. |
| 32–48 s | Illustrative error: corpus label unacceptable, model choice acceptable. P(acceptable): original 99.88%, exact-input repeat 99.88%, reversed 99.92%. Candidate probability does not measure correctness. |
| 48–54 s | Inspect typed output, candidate distribution, and task quality together. |
| 54–60 s | Explore the manuscript, full demo, code, and frozen evidence at uphash-network.github.io/mini-jev/. |

## 日本語の説明

| 時間 | 内容 |
|---|---|
| 0–6秒 | 同じ答えが返っても、正しいとは限りません。型付きの判断、候補確率、失敗例を確認できるローカルLLMの検査ツールです。 |
| 6–18秒 | 過去に収録した実際の操作映像です。Choice・Noul・Scoreを実行し、候補分布を確認します。 |
| 18–32秒 | 別途保存されたQwen2.5-1.5BのJCoLA評価では、200件すべてを「容認可能」と判断。表示順序を逆転してもラベル変更は0件ですが、42件が誤答でした。 |
| 32–48秒 | 誤答の説明例です。正解ラベルは「容認不可能」なのに、モデルは「容認可能」に元順序99.88%、同一入力の再実行99.88%、逆順序99.92%を割り当てました。42誤答中、元順序の候補確率が最も高い例を選んでいます。 |
| 48–54秒 | 型の妥当性、候補分布、課題の正解率を合わせて確認します。 |
| 54–60秒 | プロジェクトページから原稿・長いデモ・コード・保存済み評価記録を確認できます。 |

## Rebuild

Run from the repository root with Python 3.10+, Pillow, ffmpeg and ffprobe:

```sh
python3 publication/launch-20260926/video/build_video.py --work-dir .runs/launch-video
```

The default fonts are macOS Arial. On other systems supply `--font` and `--bold-font` with compatible installed font files. The script reads the frozen source/evidence ZIP, asserts the counts, renders new explanatory cards, and combines them with the existing video. It makes no model or network calls. Intermediate files are kept in the supplied work directory.

## Attribution and license

Yuki Oshio / UPHASH Inc. The composed evidence video, poster and data-derived visualization records are available under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Rendering code remains under the repository's MIT license. Original code/model/data retain their own terms.

JCoLA: Taiga Someya, Yushi Sugimoto and Yohei Oseki (2024), [Japanese Corpus of Linguistic Acceptability](https://aclanthology.org/2024.lrec-main.828/), [dataset repository](https://github.com/osekilab/JCoLA). Changes: aggregate prediction counts and selected probability records rendered as visual explanations; no original dataset sentence is included. The exact archived input files and SHA-256 hashes are in `EVIDENCE.json` and `PROVENANCE.json`.
