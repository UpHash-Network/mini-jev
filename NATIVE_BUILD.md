# ネイティブ実行環境の取得と再ビルド

公開リポジトリはソース配布です。コンパイル済みバイナリとモデル重みは含みません。現行のビルド手順は **macOS 26.4以上・ARM64** 用で、MetalとApple Accelerateを有効にします。

llama.cppは [固定コミット f072b103](https://github.com/ggml-org/llama.cpp/tree/f072b103714dfa1eee531f80b24512faf38e3dd2)
を使用。`native/BUILD.json` は過去の評価用実行物の記録です。再ビルドした実行物のmanifestは `.build/runtime/BUILD.json` へ作られます。
`native/LICENSE-llama-cpp.txt` と `native/licenses/` に同梱依存物・モデルのライセンスを保存しました。
自作helperのライセンスは `native/LICENSE-helper.txt` です。

## モデルファイル

モデル本体は約20.4 GBあり、この配布フォルダには複製していません。既存ファイルを
起動設定で指定するか、次のスクリプトで任意の保存先へ取得できます。
以下はリポジトリのルートをカレントディレクトリにした例です。

```sh
python3 fetch_native_model.py --info
python3 fetch_native_model.py --output models/Qwen3.6-35B-A3B-Q4_K_M.gguf
```

固定するartifactは `native_model.json` のrepo、revision、filename、bytes、SHA-256です。
`path` は未指定で、保存場所は `--output` と起動設定で選びます。
途中のデータは同じ場所の `.partial` ファイルへ保存し、再実行するとHTTP Rangeで再開します。
サーバーがRangeに対応しない場合は途中ファイルを先頭から取得し直します。
サイズと全体SHA-256が一致した後でのみ、完成ファイル名へatomic renameします。

既存ファイルをネットワーク接続なしで検証するには:

```sh
python3 fetch_native_model.py --verify-only --output models/Qwen3.6-35B-A3B-Q4_K_M.gguf
```

既存の完成ファイルが不一致なら置き換えずに終了します。失敗した `.partial` は調査や
再開のため残します。SHA不一致が続く場合はその途中ファイルを削除して再取得してください。
同時実行は `.download.lock` で防ぎます。強制終了でlockが残った場合は、取得プロセスが
終了したことを確認してlockだけを削除します。`.verified.json` は検証記録であり、
実行環境が起動時検証を省略するための信頼済みcacheではありません。

## 固定ソースからのビルド

Xcode command-line tools、CMake、Git、Python 3.10以上が必要です。
Rosettaを介さないmacOS ARM64で実行します。ソース・中間生成物・新しい配布物を別々に置けます。

```sh
./build_native.sh --work-dir .build/native --output .build/runtime --jobs 2
```

スクリプトは固定コミットを取得し、Release/arm64/macOS 26.4、Metal、Accelerateで
llama.cppと同梱C++ソースをビルドします。完成したライブラリの参照を相対化し、
ad-hoc署名を付け直してmanifestを作ります。既存の出力ディレクトリへは上書きしません。
過去のCMake cacheを引き継がないよう、再実行時も新しいworkディレクトリを使います。
モデルのダウンロードや推論は行いません。

これは固定ソースと手順を再現するビルドです。コンパイラ、SDK、CPU最適化、署名の差により
再ビルド後のSHA-256が過去の評価用バイナリと同一になるとは限りません。新manifestを使って
実モデル検証と校正をやり直してから、起動設定で新しいhelperを指定してください。

```sh
python3 native/package_runtime.py --verify .build/runtime
python3 -m unittest discover -s native -p test_packaging.py -v
```

取得処理は小さなローカルfixtureで、部分取得・再開・不正な範囲・SHA不一致・完成名への
切替・既存ファイル保護を検証しました。過去の評価用packageは別の一時フォルダへ移し、実helperの
CPU用template処理でライブラリ解決とdecode回数0を確認しています。
この包装作業ではモデルの再取得、再ビルド、GPU推論を実行していません。

## Pythonエンジンの起動時検証

`native_engine.NativeEngine` は `model_manifest` と `native_manifest` を受け取り、
GGUFのサイズと全体SHA-256を起動時に一度検証します。モデルID、revision、量子化種別も
manifestと照合します。helper、全共有ライブラリ、C++ソース、package内の各ファイルと
symlinkをmanifestに照合し、外部の `DYLD_*` / `_DYLD_*` 設定を子プロセスから除きます。
各質問の前後にはファイルのidentity/statとaliasを確認し、変更を検出したら停止します。

校正を結び付けるruntime fingerprintは、モデルSHA、helper・ライブラリ・C++・Pythonの
実際のSHA、alias、context上限、threads、device、dtype、prompt style、Python/OS情報から
作ります。保存先パスと温度は含めません。同じ配布物の移動でfingerprintは変わらず、
計算に関係する設定やコードを変更すると新しい校正が必要になります。

## 起動

`native_config.json` は `models/` と `.build/runtime/` を参照します。新しい環境では温度校正を自動適用しません。

```sh
./run.sh --without-calibration
```

元の測定値は元の固定実行物に対するものです。新しいビルドへの温度適用は、その実行物で校正を実施し `--temperature-config` で明示指定してください。手順はREADMEを参照してください。
