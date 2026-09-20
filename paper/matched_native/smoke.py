#!/usr/bin/env python3
"""Eight-request native smoke: mode parity, JSON completion, and error recovery."""
import argparse
import hashlib
import json
from pathlib import Path
import selectors
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from native_engine import NativeEngine, options_for


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=False)
    formatter = object.__new__(NativeEngine)
    formatter.prompt_style = "repeat_typed_score"
    fixtures = [
        {"type": "choice", "state": "色は赤です。", "instructions": "状態に明記された色はどれですか。", "criteria": {"blue": "青", "red": "赤"}},
        {"type": "score", "state": "整数の値は2です。", "instructions": "整数の値をそのまま選んでください。", "criteria": ["0", "1", "2"]},
    ]
    requests = []
    for index, question in enumerate(fixtures):
        options = options_for(question)
        labels, prefix, kind = formatter._candidate_spec(question, options)
        messages = formatter._messages(question, options)
        for mode in ("direct", "one_token"):
            requests.append({"id": f"{index}-{mode}", "mode": mode, "messages": messages,
                             "candidates": labels, "assistant_prefix": prefix, "max_input_tokens": 2048})
        choices = "\n".join(f"{label}: {description}" for label, (_, description) in zip(labels, options))
        content = f"状態:\n{question['state']}\n質問:\n{question['instructions']}\n選択肢:\n{choices}\n"
        content += ('回答はJSONだけ。形式は {"answer":"選択肢の英大文字"}。' if kind == "string" else '回答はJSONだけ。形式は {"answer":段階の数値}。')
        requests.append({"id": f"{index}-json", "mode": "json", "messages": [{"role": "user", "content": content + "\n\n" + content}],
                         "candidates": labels, "json_value_kind": kind, "max_input_tokens": 2048, "max_output_tokens": 32})
    requests.append({**requests[2], "id": "expected-token-limit-error", "max_output_tokens": 1})
    requests.append({**requests[0], "id": "recovery-direct"})
    replies = []
    with (output / "stderr.log").open("w") as error_log:
        proc = subprocess.Popen([args.binary, "--model", args.model, "--ctx", "2048", "--threads", "6"],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=error_log, text=True, bufsize=1)
        selector = selectors.DefaultSelector()
        selector.register(proc.stdout, selectors.EVENT_READ)
        def read():
            if not selector.select(120):
                raise TimeoutError("helper response deadline")
            line = proc.stdout.readline()
            if not line:
                raise RuntimeError("helper exited early")
            return json.loads(line)
        try:
            ready = read()
            if ready.get("ready") is not True:
                raise RuntimeError("helper startup failed")
            for request in requests:
                proc.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
                proc.stdin.flush()
                reply = read()
                replies.append(reply)
                print(json.dumps({"id": request["id"], "error": reply.get("error"),
                                  "output_tokens": reply.get("output_tokens"), "decode_count": reply.get("decode_count")}), flush=True)
            for index in range(2):
                direct, one, generated = replies[index * 3:index * 3 + 3]
                assert all("error" not in r for r in (direct, one, generated))
                for field in ("logits", "probabilities", "label_index", "prompt_sha256", "input_token_ids_sha256", "candidate_ids"):
                    assert direct[field] == one[field], field
                assert not direct["argmax_tie"]
                assert direct["decode_count"] == one["decode_count"] == 1
                assert direct["output_tokens"] == 0 and one["output_tokens"] == 1
                assert generated["output_tokens"] == len(generated["generated_token_ids"]) == generated["decode_count"]
                parsed = json.loads(generated["generated_text"])
                assert set(parsed) == {"answer"}
                assert str(parsed["answer"]) == generated["answer"]
                assert str(parsed["answer"]) == requests[index * 3 + 2]["candidates"][generated["label_index"]]
                assert generated["candidate_boundary_checked"] is False
                assert all(v >= 0 for v in generated["timing_ms"].values())
            assert "output token limit" in replies[6]["error"] and replies[6]["state_cleared_on_error"]
            assert "error" not in replies[7] and replies[7]["logits"] == replies[0]["logits"]
            receipt = {"passed": True, "requests": 8,
                       "binary_sha256": hashlib.sha256(Path(args.binary).read_bytes()).hexdigest(),
                       "source_sha256": hashlib.sha256((HERE / "llama_matched_helper.cpp").read_bytes()).hexdigest(),
                       "fixture_requests": requests, "responses": replies,
                       "note": "Synthetic API/algorithm fixtures; not a performance benchmark. Six normal requests plus one expected generation-limit error and one recovery request."}
            (output / "SMOKE.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
            print(json.dumps({"passed": True, "requests": 8, "total_decode_count": replies[-1]["total_decode_count"]}), flush=True)
        finally:
            selector.close()
            proc.stdin.close()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


if __name__ == "__main__":
    main()
