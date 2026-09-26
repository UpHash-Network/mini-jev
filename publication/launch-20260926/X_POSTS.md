# X 投稿原稿

単独投稿またはスレッドのいずれかを使います。公開後版の `{{ARXIV_URL}}` は正式な公開 abstract URL に差し替えるまで投稿しません。以下の文字数は URL を 23 として計算しています。

## 現在用：プロジェクトページを案内

### 日本語

**単独投稿 (211/280)**

```text
LLMの「安定した答え」は、正しい答えとは限りません。
Mini Jevは、凍結したLLMの候補確率と型付き判断を確認するローカルUIです。追加ヘッド学習なし。著者: 大塩悠貴 / UPHASH。査読前原稿・コード:
https://uphash-network.github.io/mini-jev/
```

**スレッド 1/5 (185/280)**

```text
1/5 LLMの「安定した答え」は、正しい答えとは限りません。
著者の大塩悠貴（UPHASH）です。候補確率と型付き判断を確認できるMini Jevを開発しました。査読前原稿・コード:
https://uphash-network.github.io/mini-jev/
```

**スレッド 2/5 (179/280)**

```text
2/5 モデルは凍結し、追加の判断ヘッドは学習しません。候補の次トークンlogitから、選択・真の候補の確率・順序尺度の期待値を返します。確率は候補内での正規化で、正答確率ではありません。
```

**スレッド 3/5 (169/280)**

```text
3/5 3つの研究で計26,050リクエストを測定。26,050問の独立した問題ではありません。直接読み出しと通常の1トークン選択は1,350組すべてで一致し、速度優位は確認できませんでした。
```

**スレッド 4/5 (166/280)**

```text
4/5 表示順を変えても答えが変わらないモデルが、常に同じラベルを返す場合もありました。型の正しさ・候補への集中・答えの正しさを分けて見ることが、このUIと評価の狙いです。
```

**スレッド 5/5 (191/280)**

```text
5/5 検証環境はMac・64GB。モデルは約20.4GBで、軽量動作を保証するものではありません。日本語タスクでの評価です。再現時に詰まる点や、皆さんの具体的な用途を教えてください。
https://uphash-network.github.io/mini-jev/
```

### English

**単独投稿 (234/280)**

```text
Stable LLM answers can still be wrong.
I'm the author of Mini Jev (UPHASH): a local UI for typed decisions and candidate probabilities from frozen LMs, with no trained head. Manuscript/code (not peer reviewed):
https://uphash-network.github.io/mini-jev/
```

**スレッド 1/5 (237/280)**

```text
1/5 Stable LLM answers can still be wrong. I'm Yuki Oshio (UPHASH), author of Mini Jev: a local UI for inspecting typed decisions and candidate distributions from frozen LMs. Manuscript + code (not peer reviewed):
https://uphash-network.github.io/mini-jev/
```

**スレッド 2/5 (239/280)**

```text
2/5 No trained decision head. Candidate next-token logits yield a choice, a true-candidate probability, or an expected ordinal stage. These probabilities are normalized within the candidate set; they are not probabilities of being correct.
```

**スレッド 3/5 (227/280)**

```text
3/5 Three studies measured 26,050 requests, not 26,050 independent questions. Direct readout and native one-token selection matched in all 1,350 pairs. This run did not establish a material latency advantage for direct readout.
```

**スレッド 4/5 (259/280)**

```text
4/5 Lower sensitivity to display order did not consistently mean better answers. Some small-model conditions returned the same label almost everywhere. The UI and artifacts help separate valid types, concentrated probabilities, accuracy, and computation cost.
```

**スレッド 5/5 (246/280)**

```text
5/5 Tested on a 64GB Mac; the pinned model file is about 20.4GB. Quality evaluations use Japanese tasks. This is an inspectable implementation and evaluation, not a new scoring algorithm. What would you test or use it for?
https://uphash-network.github.io/mini-jev/
```

## arXiv 公開後用：URL の確定後に使用

### 日本語

**単独投稿 (214/280)**

```text
Mini JevのプレプリントをarXivで公開しました（査読前）。
凍結LLMの型付き判断と候補確率を確認するローカルUIです。追加ヘッド学習なし。安定した出力も正解とは限りません。著者: 大塩悠貴 / UPHASH。
{{ARXIV_URL}}
```

**スレッド 1/5 (198/280)**

```text
1/5 Mini JevのプレプリントをarXivで公開しました（査読前）。著者の大塩悠貴（UPHASH）です。凍結LLMの型付き判断と候補確率を確認するローカルUIを、評価記録とともに公開しています。
{{ARXIV_URL}}
```

**スレッド 2/5 (179/280)**

```text
2/5 モデルは凍結し、追加の判断ヘッドは学習しません。候補の次トークンlogitから、選択・真の候補の確率・順序尺度の期待値を返します。確率は候補内での正規化で、正答確率ではありません。
```

**スレッド 3/5 (169/280)**

```text
3/5 3つの研究で計26,050リクエストを測定。26,050問の独立した問題ではありません。直接読み出しと通常の1トークン選択は1,350組すべてで一致し、速度優位は確認できませんでした。
```

**スレッド 4/5 (166/280)**

```text
4/5 表示順を変えても答えが変わらないモデルが、常に同じラベルを返す場合もありました。型の正しさ・候補への集中・答えの正しさを分けて見ることが、このUIと評価の狙いです。
```

**スレッド 5/5 (191/280)**

```text
5/5 検証環境はMac・64GB。モデルは約20.4GBで、軽量動作を保証するものではありません。日本語タスクでの評価です。再現時に詰まる点や、皆さんの具体的な用途を教えてください。
https://uphash-network.github.io/mini-jev/
```

### English

**単独投稿 (240/280)**

```text
My Mini Jev preprint is on arXiv (not peer reviewed): a local UI for inspecting typed decisions and candidate probabilities from frozen LMs, with no trained head. Stable outputs can still be wrong.
Yuki Oshio, UPHASH
{{ARXIV_URL}}
```

**スレッド 1/5 (227/280)**

```text
1/5 My Mini Jev preprint is on arXiv (not peer reviewed). I'm Yuki Oshio (UPHASH). Mini Jev is a local UI for inspecting typed decisions and candidate probabilities from frozen LMs, with no trained head.
{{ARXIV_URL}}
```

**スレッド 2/5 (239/280)**

```text
2/5 No trained decision head. Candidate next-token logits yield a choice, a true-candidate probability, or an expected ordinal stage. These probabilities are normalized within the candidate set; they are not probabilities of being correct.
```

**スレッド 3/5 (227/280)**

```text
3/5 Three studies measured 26,050 requests, not 26,050 independent questions. Direct readout and native one-token selection matched in all 1,350 pairs. This run did not establish a material latency advantage for direct readout.
```

**スレッド 4/5 (259/280)**

```text
4/5 Lower sensitivity to display order did not consistently mean better answers. Some small-model conditions returned the same label almost everywhere. The UI and artifacts help separate valid types, concentrated probabilities, accuracy, and computation cost.
```

**スレッド 5/5 (246/280)**

```text
5/5 Tested on a 64GB Mac; the pinned model file is about 20.4GB. Quality evaluations use Japanese tasks. This is an inspectable implementation and evaluation, not a new scoring algorithm. What would you test or use it for?
https://uphash-network.github.io/mini-jev/
```
