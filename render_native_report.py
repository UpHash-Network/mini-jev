"""Create a readable report from an immutable acceptance result."""
import argparse
import json
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('run',type=Path)
args=p.parse_args()
s=json.loads((args.run/'summary.json').read_text())
f=json.loads((args.run/'freeze.json').read_text())
def pct(value): return f'{value*100:.2f}%'
def ms(value): return '対象なし' if value is None else f'{value:.1f}ms'
result='合格' if s['all_evaluation_criteria_passed'] else '不合格'
lines=[f'# 独立受入評価: {result}', '',
 f'全体 {s["overall"]["correct"]}/{s["overall"]["count"]} ({pct(s["overall"]["accuracy"])}).', '',
 '| 区分 | 正解 | 正解率 |', '|---|---:|---:|']
for name,x in [('全体',s['overall']),*s['by_type'].items(),('手書き180問',s['manual']),*[(f'手書き {k}',v) for k,v in s['manual_by_type'].items()]]:
 lines.append(f'| {name} | {x["correct"]}/{x["count"]} | {pct(x["accuracy"])} |')
lines+=['','## 事前の基準との照合','','| 基準 | 結果 |','|---|---|']
for k,v in s['criteria'].items(): lines.append(f'| {k} | {"PASS" if v else "FAIL"} |')
lat=s['latency']['input_tokens_le_512']; large=s['latency']['input_tokens_gt_512']
lines+=['','## 実行条件と速度','',f'- モデル: {f["runtime"]["model"]}',
 f'- revision: `{f["runtime"]["model_revision"]}`',
 f'- 実行: {f["runtime"]["device"]} / {f["runtime"]["dtype"]} / {f["runtime"].get("attention", "unspecified")}',
 f'- prompt: {f["runtime"]["prompt_style"]}, temperature: {f["runtime"]["temperature"]:.6g}',
 f'- 512 token以下 {lat["count"]}件: p50 {ms(lat["p50_ms"])}, p95 {ms(lat["p95_ms"])}, 最大 {ms(lat["max_ms"])}',
 f'- 512 token超 {large["count"]}件: p50 {ms(large["p50_ms"])}, p95 {ms(large["p95_ms"])}',
 f'- 実際のllama_decode API呼び出し: {s.get("actual_llama_decode_calls", s.get("actual_backbone_forwards"))}回。単問評価2400＋Choice逆順800＋公開warmup7。',
 f'- Choice順序変更時の意味ラベル一致: {s["candidate_order"]["same_semantic_label"]}/{s["candidate_order"]["count"]}。',
 '', 'Choice辞書は実装でキー順を正規化しています。この一致率はモデル固有の順序不変性を証明するものではありません。',
 '遅延はモデル常駐・単問・実forwardの値であり、特徴キャッシュは使いません。入力トークン数はテンプレートと再読部分を含む完全な入力です。複数質問のHTTP所要時間とは別です。llama_decode呼び出し回数はGPUカーネル数を表しません。',
 '', '## 確率・段階期待値の評価', '', '| 指標 | 温度適用前 | 温度適用後 |', '|---|---:|---:|']
for key in ['nll','brier_multiclass_sum','ece_10_equal_width','score_expectation_mae','score_normalized_expectation_mae']:
 a=s['probability_metrics_uncalibrated'][key];b=s['probability_metrics_calibrated'][key]
 lines.append(f'| {key} | {a:.6f} | {b:.6f} |')
lines+=['', '温度は独立の校正120問で選びました。今回の成績は別分布や実利用での校正を保証しません。Scoreの正解率は最尤段階、MAEは段階番号の期待値について計算しています。',
 '', '## 課題群ごとの正解率', '',
 f'全familyの単純平均: {pct(s["family_macro_accuracy"])}。生成familyの単純平均: {pct(s["generated_family_macro_accuracy"])}。',
 '', '| family | 正解 | 正解率 |','|---|---:|---:|']
for name,x in sorted(s['by_family'].items()):
 lines.append(f'| {name} | {x["correct"]}/{x["count"]} | {pct(x["accuracy"])} |')
lines+=['', '## 評価の範囲', '',
 '手書き180問＋生成2220問の限定された日本語の受入試験です。生成例は同じ課題・テンプレートを共有し、互いに独立な実利用例2400件を意味しません。一般的な判断能力や本家Jevと同等の品質は主張しません。',
 'このファイルは凍結した結果から作成しています。全予測は [predictions.jsonl](predictions.jsonl)、集計は [summary.json](summary.json)、設定とハッシュは [freeze.json](freeze.json) にあります。',
 '', ('評価基準を満たしました。API・再起動・SDK・数値検証は別の結果で確認します。' if result=='合格' else 'この設定では完成基準に未達です。この問題群は以後の開発・回帰用とし、改善版の最終受入には新規問題を用います。')]
(args.run/'REPORT.md').write_text('\n'.join(lines)+'\n')
print(args.run/'REPORT.md')
