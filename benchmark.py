#!/usr/bin/env python3
"""Compare candidate-only projection, full logits, token and JSON generation.

This is a reproducible smoke benchmark, not a general capability evaluation.
Timings returned by MiniJev synchronize the selected device before measuring.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
import math
import platform
import random
import statistics
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


METHODS = ("selected", "full", "token", "json")
METHOD_DESCRIPTIONS = {
    "selected": "最終隠れ状態を候補トークンの出力重みにのみ射影し、候補内 softmax",
    "full": "全語彙 logits から候補を取り出し、候補内 softmax",
    "token": "1 トークンを greedy 生成し、候補記号から意味ラベルへ変換",
    "json": "greedy 生成で JSON を出力し、意味ラベルを抽出",
}


def label_string(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def percentile(values: list[float], quantile: float) -> float | None:
    """Linear-interpolated quantile; all cases have equal weight."""
    if not values:
        return None
    ordered = sorted(values)
    point = (len(ordered) - 1) * quantile
    lower = int(math.floor(point))
    upper = int(math.ceil(point))
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (point - lower)


def distribution(values: list[float]) -> dict[str, float | None]:
    return {
        "mean": statistics.mean(values) if values else None,
        "median": statistics.median(values) if values else None,
        "p95": percentile(values, 0.95),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }


def load_cases(path: Path, limit: int | None) -> tuple[list[dict], str]:
    raw = path.read_bytes()
    cases = []
    ids = set()
    for line_number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        case = json.loads(line)
        required = ("id", "type", "state", "instructions", "criteria", "label")
        missing = [key for key in required if key not in case]
        if missing:
            raise ValueError(f"{path}:{line_number}: missing fields {missing}")
        if case["id"] in ids:
            raise ValueError(f"Duplicate case ID: {case['id']}")
        ids.add(case["id"])
        if case["type"] not in ("choice", "noul", "score"):
            raise ValueError(f"Unsupported case type: {case['type']}")
        criteria = case["criteria"]
        if case["type"] == "score":
            if not isinstance(criteria, list) or not criteria:
                raise ValueError(f"{case['id']}: score criteria must be a nonempty list")
            keys = [str(i) for i in range(len(criteria))]
        else:
            if not isinstance(criteria, dict) or not criteria:
                raise ValueError(f"{case['id']}: criteria must be a nonempty mapping")
            keys = list(criteria)
        if label_string(case["label"]) not in keys:
            raise ValueError(f"{case['id']}: label is not one of the candidate keys")
        cases.append(case)
    if limit is not None:
        cases = cases[:limit]
    if not cases:
        raise ValueError("The evaluation dataset contains no selected cases")
    return cases, hashlib.sha256(raw).hexdigest()


def invoke(engine: Any, case: dict, method: str) -> dict:
    # Remove the gold answer even though MiniJev's prompt builder ignores it.
    # This keeps the benchmark safe against future prompt-builder changes.
    model_input = {key: value for key, value in case.items() if key != "label"}
    if method in ("selected", "full"):
        return engine.decide(model_input, projection=method)
    return engine.generate(model_input, format=method)


def annotate(result: dict, case: dict, method: str) -> dict:
    result = dict(result)
    prediction = result.get("label")
    if prediction is not None:
        prediction = label_string(prediction)
    result["label"] = prediction
    expected = label_string(case["label"])
    valid = result.get("valid", prediction is not None)
    result["valid"] = bool(valid)
    result["correct"] = bool(valid) and prediction == expected
    for name in ("latency_ms", "model_ms"):
        if name not in result or not math.isfinite(result[name]) or result[name] < 0:
            raise ValueError(f"{case['id']} / {method}: invalid {name}")
    if method in ("selected", "full"):
        probabilities = result["probabilities"]
        if expected not in probabilities:
            raise ValueError(f"{case['id']} / {method}: gold label absent from probabilities")
        if any(not math.isfinite(p) or p < 0 or p > 1 for p in probabilities.values()):
            raise ValueError(f"{case['id']} / {method}: invalid probabilities")
        if not math.isclose(sum(probabilities.values()), 1.0, abs_tol=1e-5):
            raise ValueError(f"{case['id']} / {method}: probabilities do not sum to 1")
        # Clip only for log(0) numerical safety; this is not calibration.
        result["nll"] = -math.log(max(probabilities[expected], 1e-15))
        result["brier"] = sum(
            (probability - float(key == expected)) ** 2
            for key, probability in probabilities.items()
        )
        result["output_tokens"] = 0
    return result


def summarize(entries: list[tuple[dict, dict]], direct: bool) -> dict:
    count = len(entries)
    if not count:
        return {"count": 0}
    values = [result for _, result in entries]
    answer = {
        "count": count,
        "correct_count": sum(result["correct"] for result in values),
        "accuracy": sum(result["correct"] for result in values) / count,
        "invalid_count": sum(not result["valid"] for result in values),
        "latency_ms": distribution([result["latency_ms"] for result in values]),
        "model_ms": distribution([result["model_ms"] for result in values]),
        "input_tokens": distribution([result["input_tokens"] for result in values]),
        "generated_tokens_total": sum(result.get("output_tokens", 0) for result in values),
        "generated_tokens_mean": statistics.mean(result.get("output_tokens", 0) for result in values),
        "by_type": {},
    }
    if direct:
        answer["nll"] = statistics.mean(result["nll"] for result in values)
        answer["brier"] = statistics.mean(result["brier"] for result in values)
        score_errors = [abs(result["score"] - int(case["label"])) for case, result in entries if case["type"] == "score"]
        answer["score_expectation_mae"] = statistics.mean(score_errors) if score_errors else None
        masses = [result["candidate_mass"] for result in values if result.get("candidate_mass") is not None]
        answer["candidate_mass"] = distribution(masses)
        answer["calibrated"] = False
    for kind in sorted({case["type"] for case, _ in entries}):
        kind_values = [result for case, result in entries if case["type"] == kind]
        kind_summary = {
            "count": len(kind_values),
            "correct_count": sum(result["correct"] for result in kind_values),
            "accuracy": statistics.mean(result["correct"] for result in kind_values),
            "invalid_count": sum(not result["valid"] for result in kind_values),
            "latency_ms": distribution([result["latency_ms"] for result in kind_values]),
        }
        if direct:
            kind_summary["nll"] = statistics.mean(result["nll"] for result in kind_values)
            kind_summary["brier"] = statistics.mean(result["brier"] for result in kind_values)
        answer["by_type"][kind] = kind_summary
    return answer


def compare_probabilities(left: dict[str, float], right: dict[str, float]) -> dict:
    if set(left) != set(right):
        raise ValueError("Probability comparison requires identical semantic candidate keys")
    differences = {key: abs(left[key] - right[key]) for key in left}
    return {
        "absolute_difference_by_key": differences,
        "max_absolute_difference": max(differences.values()),
        "total_variation_distance": sum(differences.values()) / 2,
    }


def package_version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def report_markdown(result: dict, output_path: Path) -> str:
    metadata = result["metadata"]
    methods = result["summary"]
    lines = [
        "# 簡易 Jev ベースライン実験",
        "",
        f"実行日時: {metadata['created_at']}。モデル: `{metadata['model']}`。",
        f"デバイス: `{metadata['device']}`、dtype: `{metadata['dtype']}`。"
        f" 評価 {metadata['case_count']} 件（{', '.join(f'{key}: {value}' for key, value in metadata['case_counts_by_type'].items())}）。",
        "",
        "既存モデルの候補トークン出力を直接読む方法と、1 トークン生成、JSON 生成を比較した。"
        "追加学習と確率校正は実施していない。",
        "",
        "| 方法 | 正解率 | 無効出力 | 中央値 ms | p95 ms | 生成トークン計 | NLL | Brier |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for method in METHODS:
        row = methods[method]
        nll = f"{row['nll']:.4f}" if "nll" in row else "—"
        brier = f"{row['brier']:.4f}" if "brier" in row else "—"
        lines.append(
            f"| {method} | {row['correct_count']}/{row['count']} ({row['accuracy']:.1%})"
            f" | {row['invalid_count']} | {row['latency_ms']['median']:.2f}"
            f" | {row['latency_ms']['p95']:.2f} | {row['generated_tokens_total']} | {nll} | {brier} |"
        )
    lines.extend(["", "型ごとの正解率:", "", "| 方法 | Choice | Noul | Score |", "|---|---:|---:|---:|"])
    for method in METHODS:
        cells = []
        for kind in ("choice", "noul", "score"):
            row = methods[method]["by_type"].get(kind)
            cells.append(f"{row['correct_count']}/{row['count']} ({row['accuracy']:.1%})" if row else "—")
        lines.append(f"| {method} | {' | '.join(cells)} |")

    difference = result["projection_comparison"]
    audit = result["choice_order_audit"]
    lines.extend([
        "",
        "## 検証結果",
        "",
        f"候補のみ射影と全語彙射影の最大確率差: {difference['max_absolute_probability_difference']:.8g}。"
        f"意味ラベル一致: {difference['label_agreement_count']}/{difference['count']}。",
    ])
    if methods["selected"].get("score_expectation_mae") is not None:
        lines.append(f"Score期待値の平均絶対誤差（段階単位）: {methods['selected']['score_expectation_mae']:.4f}。")
    if audit["count"]:
        lines.extend([
            f"Choice の候補表示順を逆順にし、意味キーを保つ監査: {audit['count']} 件。"
            f"元の意味ラベルとの一致率 {audit['label_consistency']:.1%}、"
            f"逆順時の正解率 {audit['reversed_accuracy']:.1%}、"
            f"平均 total variation distance {audit['mean_total_variation_distance']:.4f}。",
            "Score は段階の意味順序を保つ必要があるため、Noul は内部順序固定のため、この監査から除外した。",
        ])
    else:
        lines.append("この実行には Choice ケースがなく、候補順序の監査は未実施。")
    candidate_mass = methods["full"]["candidate_mass"]["mean"]
    if candidate_mass is not None:
        lines.append(f"full の全語彙確率に占める候補記号の平均確率質量: {candidate_mass:.4f}。")
    for target in ("full", "token", "json"):
        selected_median = methods["selected"]["latency_ms"]["median"]
        if selected_median:
            ratio = methods[target]["latency_ms"]["median"] / selected_median
            lines.append(f"この実行の {target} / selected 中央値レイテンシ比: {ratio:.2f} 倍。")
    lines.extend([
        "",
        "## 測定条件と限界",
        "",
        f"- シード {metadata['seed']}。各ケースで 4 方式の実行順をシャッフルした。各方式を 1 回ウォームアップ。"
        "モデル読み込み、ウォームアップ、候補順監査の時間は比較表に含まない。",
        f"- モデル読み込み時間（比較対象外）: {metadata['model_load_seconds']:.2f} 秒。"
        f" 最大入力トークン: {metadata['max_input_tokens']}。各ケース・各方式は 1 回計測で、p95 は線形補間。",
        "- レイテンシはプロンプト処理を含む API 呼び出しの値。model_ms はモデル処理の値として JSON に別記。"
        "計測区間ではデバイス同期を実施する。単一プロセス・逐次処理で、バッチ処理は評価していない。",
        "- NLL（自然対数）と Brier（全候補の二乗誤差の和）は direct 方式のみ。"
        "どちらも候補内に再正規化した未校正確率に対する値で、信頼度としての正しさは保証されない。",
        "- Score の正解率は最尤段階ラベルの完全一致。期待値を使う連続スコアの品質評価ではない。",
        "- 小規模な手作り日本語データの動作確認であり、一般化性能や Jev との性能同等性を示さない。"
        "専用テストセット、反復計測、学習・校正は今後の検証項目。",
        "- JSON とトークン出力は出力形式の指示が異なる。速度差には形式指示・出力長・モデル計算の差が含まれる。",
        "- token/json は文法制約なしのgreedy生成。repetition_penalty=1.0。無効出力は不正解として集計。"
        "JSONは短いラベル1個で、全候補の確率を生成させていない。制約付きJSONデコードとの比較ではない。",
        f"- 全ケース入力、予測、出力文字列、候補確率、実行順、監査結果は [{output_path.name}]({output_path.name}) に保存。",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=here / "data/eval_ja.jsonl")
    parser.add_argument("--output", type=Path, default=here / "results/baseline.json")
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-input-tokens", type=int, default=2048)
    parser.add_argument("--allow-download", action="store_true", help="Allow model download if absent from the local cache")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.max_input_tokens < 1:
        parser.error("--max-input-tokens must be positive")
    cases, dataset_hash = load_cases(args.data, args.limit)
    random.seed(args.seed)
    rng = random.Random(args.seed)
    from mini_jev import MiniJev

    print(f"Loading {args.model} on {args.device}; {len(cases)} evaluation cases", flush=True)
    started = time.perf_counter()
    engine = MiniJev(
        model=args.model,
        device=args.device,
        local_files_only=not args.allow_download,
        max_input_tokens=args.max_input_tokens,
    )
    load_seconds = time.perf_counter() - started
    for method in METHODS:
        invoke(engine, cases[0], method)
        print(f"Warmup complete: {method}", flush=True)

    rows = []
    comparisons = []
    for index, case in enumerate(cases, start=1):
        order = list(METHODS)
        rng.shuffle(order)
        outputs = {}
        for method in order:
            outputs[method] = annotate(invoke(engine, case, method), case, method)
            output = outputs[method]
            print(
                f"[{index:02d}/{len(cases):02d}] {case['id']} {method}: "
                f"label={output['label']} gold={label_string(case['label'])} "
                f"correct={output['correct']} latency={output['latency_ms']:.1f}ms",
                flush=True,
            )
        comparison = compare_probabilities(outputs["selected"]["probabilities"], outputs["full"]["probabilities"])
        comparison.update({"case_id": case["id"], "label_agreement": outputs["selected"]["label"] == outputs["full"]["label"]})
        comparisons.append(comparison)
        rows.append({"case": case, "execution_order": order, "results": outputs, "projection_comparison": comparison})

    audit_rows = []
    for row in rows:
        case = row["case"]
        if case["type"] != "choice":
            continue
        reversed_case = copy.deepcopy(case)
        reversed_case["criteria"] = dict(reversed(list(case["criteria"].items())))
        reverse_result = annotate(invoke(engine, reversed_case, "selected"), reversed_case, "selected")
        original_result = row["results"]["selected"]
        comparison = compare_probabilities(original_result["probabilities"], reverse_result["probabilities"])
        audit_rows.append({
            "case_id": case["id"],
            "original_candidate_order": list(case["criteria"]),
            "reversed_candidate_order": list(reversed_case["criteria"]),
            "gold_label": label_string(case["label"]),
            "original_label": original_result["label"],
            "reversed_result": reverse_result,
            "label_consistent": original_result["label"] == reverse_result["label"],
            **comparison,
        })
        print(f"[order audit] {case['id']}: {original_result['label']} -> {reverse_result['label']}", flush=True)

    summary = {
        method: summarize([(row["case"], row["results"][method]) for row in rows], direct=method in ("selected", "full"))
        for method in METHODS
    }
    result = {
        "schema_version": 1,
        "metadata": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model": str(getattr(engine, "model_id", args.model)),
            "model_revision": getattr(engine.model.config, "_commit_hash", None),
            "cpu_brand": subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip() if platform.system() == "Darwin" else platform.processor(),
            "device": str(getattr(engine, "device", args.device)),
            "dtype": str(getattr(engine, "dtype", "unknown")),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": platform.python_version(),
            "packages": {name: package_version(name) for name in ("torch", "transformers", "tokenizers", "safetensors")},
            "data_path": str(args.data.resolve()),
            "data_sha256": dataset_hash,
            "inference_source_sha256": hashlib.sha256((here / "mini_jev.py").read_bytes()).hexdigest(),
            "prompt_revision": "v2-json-without-fixed-answer-example",
            "limit": args.limit,
            "case_count": len(cases),
            "case_counts_by_type": dict(Counter(case["type"] for case in cases)),
            "seed": args.seed,
            "max_input_tokens": args.max_input_tokens,
            "local_files_only": not args.allow_download,
            "warmup_calls_per_method": 1,
            "repetitions_per_case_method": 1,
            "model_load_seconds": load_seconds,
            "model_load_and_warmup_excluded": True,
            "device_synchronization": "MiniJev synchronizes timed model operations",
            "method_descriptions": METHOD_DESCRIPTIONS,
            "generation": {"do_sample": False, "repetition_penalty": 1.0, "constrained_decoding": False, "token_max_new_tokens": 1, "json_max_new_tokens": 32},
            "probability_interpretation": "uncalibrated, conditional on candidate tokens",
            "nll_log_base": "e",
            "nll_probability_floor": 1e-15,
            "brier_definition": "sum over candidate keys of (probability - one_hot_gold)^2",
            "evaluation_scope": "small hand-written smoke evaluation; no generalization claim",
        },
        "summary": summary,
        "projection_comparison": {
            "count": len(comparisons),
            "label_agreement_count": sum(row["label_agreement"] for row in comparisons),
            "max_absolute_probability_difference": max(row["max_absolute_difference"] for row in comparisons),
            "mean_total_variation_distance": statistics.mean(row["total_variation_distance"] for row in comparisons),
        },
        "choice_order_audit": {
            "method": "selected",
            "count": len(audit_rows),
            "label_consistency": statistics.mean(row["label_consistent"] for row in audit_rows) if audit_rows else None,
            "reversed_accuracy": statistics.mean(row["reversed_result"]["correct"] for row in audit_rows) if audit_rows else None,
            "mean_total_variation_distance": statistics.mean(row["total_variation_distance"] for row in audit_rows) if audit_rows else None,
            "changed_case_ids": [row["case_id"] for row in audit_rows if not row["label_consistent"]],
            "cases": audit_rows,
        },
        "cases": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    report_path = args.output.parent / "REPORT.md"
    report_path.write_text(report_markdown(result, args.output), encoding="utf-8")
    print(f"Saved results: {args.output.resolve()}", flush=True)
    print(f"Saved report: {report_path.resolve()}", flush=True)


if __name__ == "__main__":
    main()
