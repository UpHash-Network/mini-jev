# Mini Jev

[研究紹介ページ](https://uphash-network.github.io/mini-jev/) — 最新原稿・デモ動画・評価結果・再現手順をまとめています。

**ローカルLLMを、文章を生成しない「型付き判断の関数」として使う実装です。**

[English](README.md) · [技術レポート](paper/TECHNICAL_REPORT.md) · [自分のデータで学習](TRAINING.md) · [データカード](DATA_CARD.md) · [モデルカード](MODEL_CARD.md)

状態と質問から、選択肢を選ぶChoice、真偽の確率を返すNoul、段階の期待値を返すScoreを計算します。候補の次トークンlogitsを読み出して正規化し、Python側で応答を組み立てます。現行版は**凍結したQwen3.6-35B-A3B Q4_K_M**を使い、入力の繰り返しと型別の候補表現を採用しています。現行の35B版に追加学習は行っていません。

[TypeSafeのJev公開API](https://docs.typesafe.ai/api)を参考にした独立プロジェクトです。TypeSafeとの関係、本家の内部構造・RLCD・校正保証・SDK互換性・速度優位性は主張しません。候補logitsの分類利用や入力の繰り返しには先行研究があり、新規アルゴリズムの発表ではありません。

## 実測したこと

2026年9月20日の評価。Apple M5 Pro・64 GB・macOS 26.4・Metal、モデル常駐時です。

| 項目 | 結果 |
|---|---:|
| 最終の日本語2,400問 | **2,238問正解、93.25%** |
| Choice / Noul / Scoreの最尤ラベル正解率 | 96.00% / 95.25% / 88.50% |
| AIによる個別作問180問 | 172問正解、95.56% |
| 完全な入力512トークン以下の単問エンジンp95 | **379.1 ms**、2,291問 |
| 512トークン超のp95 | 521.8 ms、109問 |
| 型・確率・範囲の妥当性 | 2,400 / 2,400 |

**2,400問は自作評価です。** 45のテンプレート群から生成した2,220問と、AIエージェントが個別に作問し別のAIエージェントが確認した180問です。既存ファイルの`manual`や「手書き」は、人間の専門家による評価を意味しません。v2は最終モデル選択に使っていない新しい入力ですが、作問者は旧v1の一部の誤りを把握しており、論理的な課題群も引き継いでいます。外部ベンチマークや未知の課題群への一般化試験ではありません。

弱点も残ります。「約束時刻からの遅れ」29/49、「条件付き義務」31/49、「取消しを反映した件数」33/49。温度校正はNLLをわずかに改善した一方、ECEとScore期待値MAEを悪化させました。[詳細と限界](paper/TECHNICAL_REPORT.md#results)

速度にはテンプレートと繰り返し部分を含む完全な入力を数えています。起動時間・HTTP全体の保証値ではなく、通常生成に対する速度向上も未比較です。複数質問は逐次実行します。

## 起動

ネイティブ実行の確認環境はApple Silicon Mac、macOS 26.4以上です。Python 3.10以上、Xcode command-line tools、CMake、Gitが必要です。モデルは**約20.4 GB**。モデル重みと実行バイナリはソースリポジトリへ同梱していません。

リポジトリのディレクトリで実行します。

```sh
./build_native.sh --work-dir .build/native --output .build/runtime --jobs 2
python3 fetch_native_model.py --output models/Qwen3.6-35B-A3B-Q4_K_M.gguf
./run.sh --without-calibration
```

別のターミナルから:

```sh
curl -fsS http://127.0.0.1:8765/health
curl -fsS http://127.0.0.1:8765/v1/systemone \
  -H 'Content-Type: application/json' --data-binary @request.json
```

停止はControl+C。モデル全体と実行物のSHA-256を起動時に検証します。別の保存先を使う場合は`native_config.json`を`my_config.json`へコピーし、`model_file`・`native_binary`・`native_manifest`を変更して、`./run.sh --config my_config.json --without-calibration`で起動します。[ビルド手順](NATIVE_BUILD.md)

## Pythonから使う

サービスを起動したまま、リポジトリのディレクトリで実行します。ネイティブ版のサービスとSDKはPython標準ライブラリだけで動きます。

```python
from service import Client, Choice, Noul, Score

with Client() as client:
    result = client.system_one(
        state="HPは20%。回復薬を1個持つ。HP30%未満なら回復を優先する。",
        questions={
            "action": Choice("ルールに従う行動は？", {
                "heal": "回復する", "wait": "待つ"
            }),
            "low_hp": Noul("HPは30%未満ですか？"),
            "danger": Score("HPに対応する危険度は？", [
                "HP70%以上", "HP30%以上70%未満", "HP30%未満"
            ]),
        },
    )
    print(result.choices["action"].choice)
    print(result.nouls["low_hp"].noul)
    print(result.scores["danger"].score)
```

確率は**許可した候補の中だけで正規化した値**です。全語彙や現実の全事象の確率とは異なります。`confidence`は正規化エントロピーから作る指標で、正解確率ではありません。Scoreは0始まりの段階の期待値で小数になり、`label`は最尤段階です。[API詳細](service/README.md)

## 自分のデータで学習する

**[TRAINING.md](TRAINING.md)**に、JSONLの検証、凍結モデルからの特徴抽出、小さな補正head/biasの学習、別データでの温度校正、未使用テストでの評価をまとめています。これは現行35Bネイティブ版とは別の実験機能です。対応モデル・依存関係・検証済み機器は同ガイドを確認してください。

先行したQwen2.5-1.5Bの試行では、9,222パラメータの補正headにより新規96問の正解が**73問から67問へ低下**しました。biasだけでは74問でした。学習すれば必ず改善するとは主張しません。[失敗も含む実験記録](HEAD_TUNING.md)

## 評価を再実行する

[2,400問CSV](acceptance-v2/questions_2400.csv) / [JSONL](acceptance-v2/questions_2400.jsonl) / [全予測](results/native-acceptance/predictions.jsonl) / [評価レポート](results/native-acceptance/REPORT.md)

```sh
python3 -m unittest service.test_service test_native_engine
python3 -m unittest discover -s acceptance-v2 -p test_runner.py
python3 -m unittest discover -s native -p test_packaging.py

python3 acceptance-v2/run_acceptance.py calibrate --config evaluation_config.json \
  --output-dir .runs/my-calibration
python3 acceptance-v2/run_acceptance.py evaluate --config evaluation_config.json \
  --temperature-config .runs/my-calibration/temperature.json \
  --output-dir .runs/my-evaluation
```

出力先には新しいディレクトリを指定します。校正後は`./run.sh --temperature-config .runs/my-calibration/temperature.json`で起動します。モデルや実行物の場所を変える場合は、サービス用と評価用の両設定をそろえて変更してください。校正はモデル・プロンプト・実行物・設定・Python/OSを含むfingerprintに結び付きます。公開データを改善に使った後の再評価は、再現・回帰確認であり、新規の独立評価ではありません。公開用に過去ログのローカルパスを伏せているため、過去の凍結ハッシュは元のバイト列を示します。変換内容は公開用の由来記録で確認できます。

APIの候補数上限は26ですが、品質試験は2〜8候補です。26候補は機能試験のみ。Choiceのキーを並べ替えて入力するため、逆順800件の一致は順序の正規化が働くことを示し、モデルが順序不変性を獲得した証拠ではありません。既定8問・最大16問、完全入力2,048トークンまで、localhost専用です。

AIエージェントが、所有者の指示のもと実装・作問・レビュー・実験・文書作成に参加しました。AI同士のレビューは独立した人間のレビューではありません。次の研究課題は、同一モデルの生成方式との比較、外部・課題群を分離した評価、複数seedの学習実験です。[技術レポート](paper/TECHNICAL_REPORT.md)

自作コード・作成データはMITライセンスです。モデル・第三者コード・外部データセットには各配布元のライセンスが適用されます。論文化用JNLIパイロットのデータ由来レコードはCC BY-SA 4.0です（[NOTICE.md](NOTICE.md)）。引用情報は[CITATION.cff](CITATION.cff)にあります。
