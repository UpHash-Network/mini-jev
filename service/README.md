# MiniJev ローカル API / Python SDK

一度ロードしたモデルに対し、共通の状態について複数の質問を送り、文章生成なしで Choice・Noul・Score を受け取ります。HTTP サービスと SDK は Python 標準ライブラリだけで動きます。標準の推論環境は、固定した GGUF モデルを llama.cpp の常駐プロセスで実行する `NativeEngine` です。

## 起動

`mini-jev` ディレクトリで実行します。Python 3.10 以上と、同梱の macOS ARM64 用 native package、検証済みモデルファイルが必要です。モデル取得・ビルドの条件は [NATIVE_BUILD.md](../NATIVE_BUILD.md) を参照してください。

```bash
./run.sh
```

`run.sh` は `run_native_service.py` を起動し、`native_config.json` を読みます。現在の設定は Qwen3.6-35B-A3B の Q4_K_M GGUF、Metal、6 threads、各質問 2,048 input tokens 上限、`prompt_style: repeat_typed_score` です。モデルと native package の整合性検証・ロードが完了してから HTTP listener が起動します。起動時にモデルを自動ダウンロードしません。

```bash
./run.sh --print-config
./run.sh --config native_config.json --port 8765
./run.sh --model-file /path/to/models/Qwen3.6-35B-A3B-Q4_K_M.gguf
./run.sh --without-calibration
```

`--print-config` は実効引数を表示するだけで、モデルや GPU を初期化しません。Python を直接指定する場合は `python3 run_native_service.py` でも起動できます。`run_torch.sh` と `run_service.py` は以前の Torch 実験を再現するための履歴用入口です。

`native_config.json` は平坦な `NativeEngine` 引数の JSON です。モデル・helper・manifest・ログなどの相対パスは、config のあるディレクトリから解決します。モデルファイルの保存先は `--model-file` でも変更できますが、固定されたモデルのサイズ・SHA-256・モデル ID・revision・量子化種別との一致が必要です。

config 内の `temperature_config` が相対パスなら同じ規則で解決します。このキーがなく、config と同じディレクトリに `native_temperature.json` がある場合は自動で読み込みます。キーが明示的に `null` の場合や `--without-calibration` を渡した場合は適用しません。別の校正ファイルは `--temperature-config path/to/native_temperature.json` で指定できます。指定ファイルが存在しない場合、または runtime fingerprint が一致しない場合は起動できません。

```bash
curl http://127.0.0.1:8765/health
python3 -m service.example
```

既定のアドレスは `127.0.0.1:8765`。IPv4 loopback にのみ bind でき、`0.0.0.0` などの外部公開アドレスは受け付けません。ブラウザ Origin と loopback 以外の Host は拒否します。同じ端末のプログラムから使う API で、同じ端末上の他のプロセスにもアクセス可能です。

主な起動オプション（`run.sh` / `run_native_service.py` 共通）:

| オプション | 既定値 | 内容 |
|---|---|---|
| `--config` | `native_config.json` | モデル・推論設定を読む JSON |
| `--model-file` | config の保存先 | 検証対象の GGUF ファイルを指定 |
| `--host` / `--port` | `127.0.0.1` / `8765` | HTTP listener |
| `--max-questions` | `8` | リクエスト内の最大質問数。設定範囲は 1〜16 |
| `--max-pending` | `2` | 実行中を含む推論リクエストの最大数 |
| `--request-timeout` | `30` 秒 | 入力読取・待ち行列・推論を含む deadline |
| `--temperature-config` | config または自動検出 | runtime fingerprint が一致する校正 JSON |
| `--without-calibration` | 無効 | 校正ファイルを適用しない |
| `--print-config` | 無効 | 実効引数を表示して終了 |

モデル、device、dtype、threads、prompt style、token 上限は config の設定です。これらを変更すると runtime fingerprint が変わり、以前の校正ファイルは適用できません。config の `temperature` は校正ファイルを使わない場合の基準値です。校正ファイルを適用すると、その温度が使われます。温度の適用だけで正解確率の校正が保証されるわけではなく、結果の `calibrated`、`probability_semantics` と校正関連フィールドを確認してください。

## API

`GET /health` は `ready`、`model`、`pending_requests`、`max_input_tokens` を返します。

`POST /v1/systemone` の例:

```json
{
  "state": {"message": "二重請求です。至急確認してください。"},
  "questions": {
    "department": {
      "type": "choice",
      "instructions": "対応する部署を選んでください。",
      "criteria": {"billing": "料金・請求", "support": "操作方法"}
    },
    "urgent": {
      "type": "noul",
      "instructions": "至急の対応を求めていますか？"
    },
    "urgency": {
      "type": "score",
      "instructions": "対応の緊急度を評価してください。",
      "criteria": ["通常対応", "早めの対応", "至急対応"]
    }
  }
}
```

`state` は文字列・オブジェクト・配列です。`questions` のキーは回答を対応付ける ID であり、モデルの prompt には入りません。任意の `model` フィールドを付けた場合は起動済みモデルの ID と一致する必要があります。リクエストで別のモデルへ切り替えることはできません。

| 型 | criteria | 戻り値 |
|---|---|---|
| `choice` | 2〜26 個のキーと説明 | 最大確率のキー `choice` と全候補の `probabilities` |
| `noul` | 省略可能。指定時は `false` と `true` の説明 | `true` の確率 `noul` |
| `score` | 2〜26 個の段階説明を順序付き配列で指定 | 0 始まり段階番号の確率加重平均 `score` と段階説明の対応表 `legend` |

Choice の辞書の挿入順には意味がなく、NativeEngine はキーで並べ替えて prompt を固定します。Score は配列の順序そのものが段階の意味を持ちます。Noul は `false` / `true` の順序に正規化されます。

レスポンスは `model`、質問 ID 別の `answers`、`usage`、`latency_ms`、`request_id` を持ちます。各回答は `type`、`label`、`probabilities`、型別の値、`calibrated`、`probability_semantics` を持ちます。エンジンが提供する場合は `confidence` と `confidence_definition` も返します。confidence は `1 − 正規化エントロピー` であり、正解確率ではありません。校正に関する `temperature_calibration_applied` と `calibration_generalization_validated` も、エンジンが提供した値を返します。temperature の適用と、未知データに対する校正精度の検証は別です。 `probabilities` は許可した候補 token の間で正規化した分布であり、正解確率の保証ではありません。

質問は一つずつ、独立した forward で逐次処理します。各質問の前にモデルの状態をクリアし、完成した prompt を一度入力して候補 token の logits を読みます。質問間で共有状態の KV cache を再利用しません。現在の `repeat_typed_score` は、各質問内で状態・質問・選択肢を繰り返して入力し、Score には段階数に応じた候補表現を使います。文章を生成して回答を解析する処理はありません。

`usage.input_tokens` は、各質問で実際に入力した全 prompt token 数の合計です。質問ごとに読んだ状態に加え、再掲した状態・質問・候補、chat template、回答形式の prefix も含みます。元の state を一度だけ数えた値ではありません。`output_tokens` は常に 0。`latency_ms` はリクエストの読取・検証・待ち行列・全質問の推論・結果検証の所要時間で、質問数で割った値ではありません。

## Python SDK

```python
from service import Client, Choice, Noul, Score

client = Client()  # HTTP loopback のみ。shell の proxy 設定を使用しない
result = client.system_one(
    state={"message": "請求の確認をお願いします"},
    questions={
        "route": Choice("対応部署は？", {"billing": "請求", "support": "操作"}),
        "urgent": Noul("至急の依頼ですか？"),
        "priority": Score("緊急度は？", ["通常", "早め", "至急"]),
    },
)
print(result.answers["route"].choice)
print(result.answers["urgent"].noul)
print(result.answers["priority"].score)
print(result.answers["priority"].legend)
print(result.usage)
```

`with Client() as client:` の context manager も使えます。回答を型で取り出す場合は `result.choices["route"].choice`、`result.nouls["urgent"].noul`、`result.scores["priority"].score` を使います。独自のローカル API / SDK であり、元の Jev 公式 SDK とは非互換です。

SDK は送信前に入力を検証し、受信した全候補確率・候補集合・値の整合性・usage を検証します。型付き質問の代わりに同じ schema の辞書も渡せます。`service.client.APIError` には HTTP `status`、`code`、`request_id` があります。接続失敗は標準ライブラリの接続例外、入力・レスポンスの不整合は `service.schema.ValidationError` です。自動リトライはしません。

## 上限・エラー・並行処理

既定の body 上限は 128 KiB、質問数は 8、各テキストは 32,768 文字、ID は 128 文字、state の nesting は 32。JSON の重複キー、未知フィールド、NaN/Infinity、不正な UTF-8 は拒否します。各質問の token 上限はエンジンが全 prompt を token 化して検査します。どの段階でも黙って切り詰めません。

| HTTP | 用途 |
|---|---|
| `400` / `411` / `415` | 不正な HTTP encoding・length・Content-Type |
| `403` | browser Origin / loopback 以外の Host |
| `408` | body 読取の timeout |
| `413` | body サイズ上限 |
| `422` | JSON/schema/model 不一致、engine の token 上限等 |
| `503` | 推論待ち行列満員、接続数上限、not ready |
| `504` | リクエスト deadline 超過 |
| `500` | 推論エラー・不正な engine 出力。内部例外や traceback は返さない |

単一 worker が GPU を直列使用し、`max_pending` の既定値 2 には実行中の要求も含みます。504 を返した後も実行中の GPU 処理は安全に中断できないため、処理が完了するまでその枠を保持します。待ち行列内で deadline を超過した要求は推論を実行せずに破棄します。接続数も最大 16 に制限しています。接続上限時は、通常の送信中でも 503 を受け取れるよう短い終了猶予を設け、期限と読取量を制限して接続を閉じます。`/health` の pending 数には timeout 後も実行中の要求を含みます。

## モデル不要の検証

```bash
python3 -m unittest service.test_service -v
```

一時 port の本物 HTTP サーバーと fake engine を使い、型・JSON 境界・失敗処理・SDK・同時リクエストの直列化・待ち行列の満員・deadline と timeout 後の復帰・接続上限時の分割送信と容量回復を検証します。実モデルの精度・性能評価とは別のテストです。
