"""Frozen-backbone head experiment with disjoint train/dev/calibration/test data.

Only dev NLL chooses head weights; only calibration NLL chooses temperature.
Test data are opened AFTER both choices and checkpoint saving are complete.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import random
import time
from pathlib import Path

import torch
from safetensors.torch import load_file, save_file
from mini_jev import MiniJev, options_for
from head_jev import normalize_hidden, prompt_fingerprint, feature_fingerprint


def digest(value, preserve_order=False):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=not preserve_order).encode()).hexdigest()


def label_key(value):
    return str(value).lower() if isinstance(value, bool) else str(value)


def read_cases(path):
    cases = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    if not cases or len({c["id"] for c in cases}) != len(cases):
        raise ValueError("empty dataset or duplicate ids")
    for case in cases:
        keys = [k for k, _ in options_for(case)]
        if label_key(case["label"]) not in keys:
            raise ValueError(f"invalid label in {case['id']}")
    return cases


def check_disjoint(groups):
    seen = {}
    for split, cases in groups.items():
        for c in cases:
            # Choice mapping order is ignored here: a permutation is not independent data.
            key = digest({k: c[k] for k in ("type", "state", "instructions", "criteria")})
            if key in seen and seen[key] != split:
                raise ValueError(f"input overlap: {seen[key]} and {split}")
            seen[key] = split


def augment_training(cases):
    result = copy.deepcopy(cases)
    for c in cases:
        if c["type"] == "choice":
            variant = copy.deepcopy(c)
            variant["id"] += "_reverse"
            variant["criteria"] = dict(reversed(list(c["criteria"].items())))
            # The semantic gold key remains unchanged; recompute the whole prompt.
            result.append(variant)
    return result


@torch.no_grad()
def extract(engine, cases, cache_dir, name, batch_size=8, max_choices=6):
    fingerprint = digest({"cases": cases, "model": engine.model_id,
                          "revision": engine.model.config._commit_hash,
                          "features": feature_fingerprint(), "max_choices": max_choices,
                          "dtype": str(engine.dtype), "feature_version": 1}, preserve_order=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{name}-{fingerprint[:16]}.safetensors"
    if path.exists():
        print(f"cache hit: {name}", flush=True)
        return load_file(str(path))
    feature, baseline, targets, counts = [], [], [], []
    _, weight, bias = engine._head(max_choices)
    for start in range(0, len(cases), batch_size):
        chunk = cases[start:start+batch_size]
        prepared = [engine._prepare(c) for c in chunk]
        if any(len(options) > max_choices for options, _ in prepared):
            raise ValueError("too many candidates for trained head")
        inputs = engine._batch([ids for _, ids in prepared])
        hidden = engine.model.base_model(**inputs, use_cache=False, return_dict=True).last_hidden_state[:, -1, :]
        logits = torch.nn.functional.linear(hidden, weight, bias).float()
        feature.append(normalize_hidden(hidden).cpu())
        baseline.append(logits.cpu())
        for c, (options, _) in zip(chunk, prepared):
            targets.append([k for k, _ in options].index(label_key(c["label"])))
            counts.append(len(options))
        if start == 0 or start // batch_size % 10 == 0 or start+batch_size >= len(cases):
            print(f"features {name}: {min(start+batch_size, len(cases))}/{len(cases)}", flush=True)
    tensors = {"x": torch.cat(feature), "base": torch.cat(baseline),
               "target": torch.tensor(targets), "count": torch.tensor(counts)}
    save_file(tensors, str(path), metadata={"fingerprint": fingerprint})
    return tensors


def masked_logits(logits, counts):
    valid = torch.arange(logits.shape[1])[None, :] < counts[:, None]
    return logits.masked_fill(~valid, -1e9)


def get_logits(data, weight=None, bias=None):
    if weight is None:
        return data["base"]
    return data["base"] + torch.nn.functional.linear(data["x"], weight, bias)


def metrics(logits, data, cases, temperature=1.0):
    logits = masked_logits(logits / temperature, data["count"])
    probabilities = logits.softmax(-1)
    predicted = probabilities.argmax(-1)
    correct = predicted.eq(data["target"])
    nll = torch.nn.functional.cross_entropy(logits, data["target"]).item()
    gold = torch.nn.functional.one_hot(data["target"], logits.shape[1]).float()
    brier = (probabilities-gold).square().sum(-1).mean().item()
    confidence = probabilities.max(-1).values
    ece = 0.0
    for low in torch.linspace(0, .9, 10):
        membership = (confidence >= low) & (confidence < low+.1 if low < .89 else confidence <= 1)
        if membership.any():
            ece += membership.float().mean().item() * abs(confidence[membership].mean().item()-correct[membership].float().mean().item())
    score_errors = []
    for i, c in enumerate(cases):
        if c["type"] == "score":
            expected = sum(j * probabilities[i, j].item() for j in range(int(data["count"][i])))
            score_errors.append(abs(expected-int(c["label"])))
    return {"n": len(cases), "correct": int(correct.sum()), "accuracy": correct.float().mean().item(),
            "nll": nll, "brier": brier, "ece_10_bins": ece,
            "score_mae": sum(score_errors)/len(score_errors) if score_errors else None,
            "by_type": {kind: {"n": sum(c["type"] == kind for c in cases),
                               "correct": sum(bool(correct[i]) for i, c in enumerate(cases) if c["type"] == kind)}
                        for kind in sorted({c["type"] for c in cases})}}


def train(train, dev, dev_cases, epochs=120, bias_only=False):
    torch.set_num_threads(4)
    best = None
    trials = []
    for lr in (.001, .003):
        for penalty in (.01, .1):
            torch.manual_seed(42)
            weight = torch.nn.Parameter(torch.zeros(train["base"].shape[1], train["x"].shape[1]), requires_grad=not bias_only)
            bias = torch.nn.Parameter(torch.zeros(train["base"].shape[1]))
            parameters = [bias] if bias_only else [weight, bias]
            optimizer = torch.optim.AdamW(parameters, lr=lr, weight_decay=0)
            history = []
            # epoch zero is the explicit identity control.
            for epoch in range(epochs+1):
                if epoch:
                    optimizer.zero_grad()
                    delta = torch.nn.functional.linear(train["x"], weight, bias)
                    valid = torch.arange(delta.shape[1])[None, :] < train["count"][:, None]
                    loss = torch.nn.functional.cross_entropy(masked_logits(train["base"]+delta, train["count"]), train["target"])
                    loss = loss + penalty * delta[valid].square().mean()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(parameters, 5.0)
                    optimizer.step()
                if epoch % 5 == 0 or epoch == epochs:
                    with torch.no_grad():
                        assessment = metrics(get_logits(dev, weight, bias), dev, dev_cases)
                    history.append({"epoch": epoch, "dev": assessment})
                    candidate = {"lr": lr, "penalty": penalty, "epoch": epoch, "dev_nll": assessment["nll"]}
                    if best is None or assessment["nll"] < best["selection"]["dev_nll"]:
                        best = {"weight": weight.detach().clone(), "bias": bias.detach().clone(), "selection": candidate}
            trials.append({"lr": lr, "penalty": penalty, "history": history})
            print(f"trained bias_only={bias_only} lr={lr} penalty={penalty}; best dev NLL={best['selection']['dev_nll']:.4f}", flush=True)
    return best, trials


def fit_temperature(logits, data):
    # A single scalar, selected exclusively on the calibration split.
    temperatures = torch.logspace(math.log10(.1), math.log10(10), 301)
    losses = [torch.nn.functional.cross_entropy(masked_logits(logits/float(t), data["count"]), data["target"]).item() for t in temperatures]
    index = min(range(len(losses)), key=losses.__getitem__)
    return float(temperatures[index]), {"nll": losses[index], "at_search_boundary": index in (0, len(losses)-1)}


def case_outputs(logits, data, cases, temperature=1):
    probabilities = masked_logits(logits/temperature, data["count"]).softmax(-1)
    rows = []
    for i, c in enumerate(cases):
        keys = [k for k, _ in options_for(c)]
        p = probabilities[i, :len(keys)].tolist()
        label = keys[max(range(len(p)), key=p.__getitem__)]
        rows.append({"id": c["id"], "type": c["type"], "gold": label_key(c["label"]),
                     "label": label, "correct": label == label_key(c["label"]), "probabilities": dict(zip(keys, p))})
    return rows


def evaluate(data, cases, best, temperatures):
    baseline = get_logits(data)
    tuned = get_logits(data, best["weight"], best["bias"])
    conditions = {"baseline": (baseline, 1), "baseline_temperature": (baseline, temperatures["baseline"]),
                  "head": (tuned, 1), "head_temperature": (tuned, temperatures["head"])}
    control = best["bias_control"]
    bias_logits = get_logits(data, control["weight"], control["bias"])
    conditions["bias_only"] = (bias_logits, 1)
    conditions["bias_only_temperature"] = (bias_logits, temperatures["bias_only"])
    return {name: {"metrics": metrics(logits, data, cases, temperature),
                   "cases": case_outputs(logits, data, cases, temperature)}
            for name, (logits, temperature) in conditions.items()}


def write_report(result, path):
    c = result["config"]
    new_test = result["evaluation"]["test"]
    lines = ["# 出力ヘッドだけの追加学習", "",
             f"新規96問では、学習なし {new_test['baseline']['metrics']['correct']}問、線形head {new_test['head']['metrics']['correct']}問、biasのみ {new_test['bias_only']['metrics']['correct']}問が正解。"
             "この訓練データと設定では、線形headによる未見問題の正解率改善を確認できなかった。", "",
             f"モデル: `{c['model']}`。本体は凍結。学習パラメータ数: {c['trainable_parameters']:,}。",
             "", "最終隠れ状態をRMS正規化し、元の候補logitsへ線形の補正を加えた。"
             "開発データのNLLで重みを選択し、別の校正データで温度を決めた。テスト結果はモデル選択に使っていない。", "",
             f"選択した設定: `{c['selection']}`。温度: baseline={result['temperatures']['baseline']:.3f}, head={result['temperatures']['head']:.3f}。", ""]
    for split in ("dev", "calibration", "test", "legacy48"):
        lines += ["", f"## {split}", "", "| 条件 | 正解数 | 正解率 | NLL | Brier | ECE | Score MAE |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for name, row in result["evaluation"][split].items():
            m = row["metrics"]
            lines.append(f"| {name} | {m['correct']}/{m['n']} | {m['accuracy']:.1%} | {m['nll']:.3f} | {m['brier']:.3f} | {m['ece_10_bins']:.3f} | {m['score_mae']:.3f} |")
    lines += ["", "## 型別の新規テスト正解数", "", "| 条件 | Choice | Noul | Score |", "|---|---:|---:|---:|"]
    for name, row in result["evaluation"]["test"].items():
        cells = [f"{row['metrics']['by_type'][kind]['correct']}/{row['metrics']['by_type'][kind]['n']}" for kind in ("choice", "noul", "score")]
        lines.append(f"| {name} | {' | '.join(cells)} |")
    lines += ["", "## Choiceの候補順監査", ""]
    for split, audit in result["order_audits"].items():
        for name, row in audit.items():
            lines.append(f"- {split} / {name}: 意味ラベル一致 {row['consistent']}/{row['n']}、逆順で正解 {row['reverse_correct']}/{row['n']}、平均TV距離 {row['mean_tv']:.3f}。")
    validation_path = path.parent / "validation.json"
    if validation_path.exists():
        validation = json.loads(validation_path.read_text())
        timings = validation["latency"]["summary"]
        checks = validation["checks"]
        lines += ["", "## 保存・復元と実推論", "",
                  f"検証 {sum(x['passed'] for x in checks)}/{len(checks)}項目成功。CPU特徴から再計算した確率と、保存したheadを読み込んだGPU推論との一致を確認した。",
                  f"実forwardの中央値はbaseline {timings['baseline']['latency']['median_ms']:.1f}ms、head {timings['head']['latency']['median_ms']:.1f}ms。"
                  "新規テストの先頭12件（Choiceのみ）を各3回測定した値であり、特徴キャッシュや学習時間を推論時間として扱っていない。",
                  "詳細は[validation.json](validation.json)を参照。"]
    lines += ["", "## 限界", "",
              "合成訓練・開発・校正データは意味設定グループで分割しているが、生成器の共通テンプレートを共有する。"
              "新規96件は訓練・旧評価データを見ない別担当者が執筆した小規模な手作り評価である。実運用や未知分野一般の品質を保証しない。",
              "", "温度スケーリングは順位を変えず、正解率の改善手段ではない。合成校正データの確率特性が実入力にも通用するとは限らない。ECEは少数サンプルとビン分けに影響される。",
              "", "旧48件は前フェーズで分析済みの回帰確認用。候補順だけ変えた例は訓練側にまとめており、独立の評価例として数えない。",
              "", "Choiceの並べ替え拡張後、訓練損失の半分がChoice、各4分の1がNoulとScoreに対応する。devとtestは型ごと均等。",
              "", "既存モデルや標準MiniJevのデフォルトは変更していない。headは明示的に指定したときだけ読み込まれる。", ""]
    path.write_text("\n".join(lines))


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--cache", type=Path, default=here / ".cache/head_features")
    parser.add_argument("--output", type=Path, default=here / "results/head")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    random.seed(42); torch.manual_seed(42)
    started = time.perf_counter()
    groups = {name: read_cases(here / f"data/head_{filename}.jsonl") for name, filename in
              (("train", "train"), ("dev", "dev"), ("calibration", "calibration"))}
    check_disjoint(groups)
    groups["train"] = augment_training(groups["train"])
    engine = MiniJev(model=args.model, device=args.device)
    engine.model.requires_grad_(False)
    assert not any(p.requires_grad for p in engine.model.parameters())
    data = {name: extract(engine, cases, args.cache, name, args.batch_size) for name, cases in groups.items()}
    # Extracted features must exactly reproduce the zero-delta control before training.
    torch.testing.assert_close(get_logits(data["dev"], torch.zeros(6, data["dev"]["x"].shape[1]), torch.zeros(6)), data["dev"]["base"], atol=0, rtol=0)
    best, trials = train(data["train"], data["dev"], groups["dev"], args.epochs)
    bias_control, bias_trials = train(data["train"], data["dev"], groups["dev"], args.epochs, bias_only=True)
    best["bias_control"] = bias_control
    temperatures, calibration_details = {}, {}
    for name, logits in (("baseline", data["calibration"]["base"]),
                         ("head", get_logits(data["calibration"], best["weight"], best["bias"])),
                         ("bias_only", get_logits(data["calibration"], bias_control["weight"], bias_control["bias"]))):
        temperatures[name], calibration_details[name] = fit_temperature(logits, data["calibration"])
    checkpoint = args.output / "checkpoint"
    checkpoint.mkdir(exist_ok=True)
    config = {"model": engine.model_id, "model_revision": engine.model.config._commit_hash,
              "prompt_fingerprint": prompt_fingerprint(), "max_choices": 6, "max_input_tokens": engine.max_input_tokens,
              "feature_fingerprint": feature_fingerprint(),
              "symbol_ids": engine.symbol_ids[:6], "temperature": temperatures["head"],
              "baseline_temperature": temperatures["baseline"], "selection": best["selection"],
              "trainable_parameters": best["weight"].numel()+best["bias"].numel(),
              "backbone_frozen": True, "seed": 42, "train_count_augmented": len(groups["train"]),
              "bias_only_selection": bias_control["selection"],
              "fit_dataset_hashes": {name: digest(cases) for name, cases in groups.items()}}
    save_file({"delta_weight": best["weight"], "delta_bias": best["bias"]}, str(checkpoint / "head.safetensors"))
    (checkpoint / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2))
    bias_checkpoint = args.output / "checkpoint-bias"
    bias_checkpoint.mkdir(exist_ok=True)
    bias_config = dict(config, temperature=temperatures["bias_only"], selection=bias_control["selection"], trainable_parameters=6)
    save_file({"delta_weight": bias_control["weight"], "delta_bias": bias_control["bias"]}, str(bias_checkpoint / "head.safetensors"))
    (bias_checkpoint / "config.json").write_text(json.dumps(bias_config, ensure_ascii=False, indent=2))
    checkpoint_hash = hashlib.sha256((checkpoint / "head.safetensors").read_bytes()).hexdigest()
    print("Head weights and temperatures locked. Opening test data now.", flush=True)
    groups["test"] = read_cases(here / "data/head_test_ja.jsonl")
    groups["legacy48"] = read_cases(here / "data/eval_ja.jsonl")
    check_disjoint(groups)
    for split in ("test", "legacy48"):
        data[split] = extract(engine, groups[split], args.cache, split, args.batch_size)
    evaluation = {split: evaluate(data[split], groups[split], best, temperatures) for split in ("dev", "calibration", "test", "legacy48")}
    order_audits = {}
    for split in ("test", "legacy48"):
        reverse_cases = []
        indexes = []
        for i, case in enumerate(groups[split]):
            if case["type"] == "choice":
                c = copy.deepcopy(case)
                c["criteria"] = dict(reversed(list(c["criteria"].items())))
                reverse_cases.append(c); indexes.append(i)
        reverse_data = extract(engine, reverse_cases, args.cache, split+"_reverse", args.batch_size)
        reverse_results = evaluate(reverse_data, reverse_cases, best, temperatures)
        order_audits[split] = {}
        for name in ("baseline", "head", "baseline_temperature", "head_temperature", "bias_only", "bias_only_temperature"):
            original = [evaluation[split][name]["cases"][i] for i in indexes]
            reverse = reverse_results[name]["cases"]
            order_audits[split][name] = {"n": len(reverse),
                "consistent": sum(a["label"] == b["label"] for a,b in zip(original,reverse)),
                "reverse_correct": sum(b["correct"] for b in reverse),
                "mean_tv": sum(sum(abs(a["probabilities"][k]-b["probabilities"][k]) for k in a["probabilities"])/2 for a,b in zip(original,reverse))/len(reverse),
                "reverse_cases": reverse}
    assert hashlib.sha256((checkpoint / "head.safetensors").read_bytes()).hexdigest() == checkpoint_hash
    result = {"config": config, "temperatures": temperatures, "calibration_details": calibration_details,
              "selection_trials": trials, "bias_only_trials": bias_trials, "evaluation": evaluation, "order_audits": order_audits,
              "checkpoint_sha256_before_and_after_test": checkpoint_hash,
              "all_dataset_hashes": {name: digest(cases) for name,cases in groups.items()},
              "elapsed_seconds": time.perf_counter()-started}
    (args.output / "experiment.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    write_report(result, args.output / "REPORT.md")
    print(f"Saved {args.output}", flush=True)
    for name, value in evaluation["test"].items():
        print(name, value["metrics"], flush=True)


if __name__ == "__main__":
    main()
