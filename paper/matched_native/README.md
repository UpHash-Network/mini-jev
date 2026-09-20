# Isolated native helper for matched inference experiments

This research helper supports direct candidate-logit readout, one-token constrained generation, and grammar-constrained autoregressive JSON generation in a single process. It does **not** replace the production helper or `native_engine.py`. It uses the same pinned llama.cpp commit `f072b103714dfa1eee531f80b24512faf38e3dd2` and a verified copy of the native runtime's dynamic libraries.

## Three modes

| Mode | Selection | Actual generated output | Decode calls |
|---|---|---|---|
| `direct` | Gather candidate logits; stable T=1 softmax and argmax | None | One prefill |
| `one_token` | Same prompt/prefill/candidate token IDs; set all other vocabulary logits to negative infinity; apply llama.cpp greedy sampler | One actual sampled label token | One prefill; no decode of the sampled terminal token |
| `json` | Greedy llama.cpp sampler after GBNF grammar filtering at each generation step | Entire `{"answer":"A"}` or `{"answer":0}` object | One prefill plus a decode for each generated token except the last |

The caller supplies the same question and label semantics but different output instructions for JSON generation. Its complete formatted prompt and token count are separately audited. The direct/one-token comparison can use byte-identical prompts; the JSON comparison cannot be described as having an identical prompt or input-token budget unless the caller actually establishes that.

All modes compute the full vocabulary head. No selected-row projection optimization or answer cache is used. KV and recurrent state are cleared before every valid request. JSON uses a fresh grammar sampler for each request. An error synchronizes and clears state before accepting the next request.

Direct/one-token requests require each candidate to be one isolated token **and** to append as exactly one token at the actual rendered prompt boundary. JSON candidates still require unique isolated token IDs, but are not subjected to the answer-position boundary check at the beginning of the JSON object. Their final generated value is parsed and matched back to the unique allowed label list.

The direct mode breaks exact logit ties by candidate-list order. The real-vocabulary greedy sampler iterates by vocabulary token ID and therefore breaks ties by the lowest token ID. Responses disclose `argmax_tie` and all `max_logit_candidate_indices`; studies should count/report ties instead of silently attributing a tie-break difference to model inference. The smoke fixtures have no top-logit ties.

## Build

First build the production native runtime from the [pinned build recipe](../../build_native.sh). Then reuse its verified library files and matching clean llama.cpp checkout. The output must be a new directory **outside the Git repository**; no binary or model weights are added to Git.

```bash
python3 paper/matched_native/build.py \
  --llama-source /absolute/path/to/pinned/llama.cpp \
  --runtime .build/runtime \
  --output /absolute/path/outside-repository/matched-runtime
```

The script checks the pinned source revision and tracked-file cleanliness, hashes the runtime files, checks library aliases, copies the needed libraries and license notices, and compiles the helper. `BUILD.json` records source/compiler/library hashes and relative aliases. On macOS, the executable uses `@loader_path` and receives an ad-hoc signature. The implementation includes a Linux `$ORIGIN` build path, but only macOS ARM64 was tested here. Building on a different system need not produce byte-identical binaries or timing.

## JSONL protocol

Start the helper with `--model FILE --ctx 2048 --threads 6 --gpu-layers 99`. It emits a `ready` JSON record followed by exactly one JSON response per input line. Requests use these fields:

```json
{
  "id": "example-1",
  "mode": "one_token",
  "messages": [{"role": "user", "content": "Choose A or B."}],
  "candidates": ["A", "B"],
  "max_input_tokens": 2048,
  "max_output_tokens": 32,
  "max_request_ms": 120000
}
```

Provide either `messages` or an already formatted `prompt`. Message rendering uses the model's Jinja chat template with thinking disabled. `assistant_prefix` is optional fixed input text for direct/one-token modes. JSON mode rejects a nonempty prefix because it must generate the whole object. Set `json_value_kind` to `string` for A–Z labels or `number` for single-digit numeric labels. The grammar permits only one `answer` property, with optional single ASCII spaces between JSON punctuation and **no leading/trailing whitespace**. It permits only the supplied label values.

JSON decoding stops immediately when the generated text parses as the complete, single-property, correctly typed object with an allowed label. It samples no extra EOS and performs no unnecessary decode of the last output token. Generation is bounded at 32 tokens maximum. Input is never truncated. If input plus needed generation exceeds context or generation reaches its output limit, the request fails explicitly. Native deadlines are checked between synchronized operations; a single GPU decode is not preemptible. A caller needing a hard wall-clock deadline must terminate/restart the helper process on timeout.

All successful responses include:

- `label_index`: index into the supplied candidate list; `answer`: corresponding canonical candidate string, including numeric labels represented as strings in this audit response.
- `candidate_ids`, their SHA-256, rendered-prompt SHA-256, and input-token-ID SHA-256. Token-ID hashes cover the UTF-8 encoding of a compact JSON integer array; prompt hashes cover its exact UTF-8 bytes.
- `input_tokens`, `output_tokens`, `generated_text`, and `generated_token_ids`. Direct mode has zero output tokens and an empty generated string.
- Actual `decode_count` and process-cumulative `total_decode_count`, counting llama_decode API calls rather than GPU kernels.
- `logits` and T=1 `probabilities` for the primary two modes. These are null for JSON mode because initial JSON-position candidate logits would not represent the final answer distribution.
- `timing_ms`: parse, render, tokenize/boundary validation, state reset, prefill, candidate readout, sampler setup, sampling, autoregressive decode, completion checks, response preparation, response serialization, and native total time.

Prefill and token-decode timers end after synchronized logit retrieval. Sampling includes vocabulary-array construction, masks/grammar application, actual greedy sampling, sampler acceptance, and token-to-text conversion. `native_total_ms` covers request processing through serialization of the main response payload; it excludes the small timing trailer and stdout delivery. The parent must measure pipe and HTTP wall time itself for complete end-to-end latency. Default responses include no source prompt text; the local audit flags `debug_prompt` and `debug_input_tokens` may explicitly include it.

An unsuccessful response has `error`, the actual decode counters, and `state_cleared_on_error`. It must remain an error in downstream metrics rather than being silently excluded or converted to a correct answer.

## Verified fixtures

[SMOKE.json](SMOKE.json) records eight requests: two synthetic cases across all three modes, one intentionally limited JSON request, and a recovery request. [BUILD_RECEIPT.json](BUILD_RECEIPT.json) records the tested compiled package. These are algorithm/API fixtures, **not a latency benchmark**; first-use Metal compilation can affect their timing.

Checks passed on Apple Silicon with the pinned Qwen3.6-35B-A3B GGUF:

- Both letter and digit fixtures have identical direct/one-token prompt hashes, input-token hashes, candidate IDs, logits, probabilities, and chosen label, with one decode call each.
- String JSON used five generated tokens/five decode calls; numeric JSON used six tokens/six decode calls. Both parsed as the allowed full object and stopped without extra EOS or terminal-token decode.
- The one-token output limit produced the expected explicit error; the following direct request reproduced the first request's logits exactly.

To rerun the bounded smoke check with new output files:

```bash
python3 paper/matched_native/smoke.py \
  --binary /absolute/path/outside-repository/matched-runtime/bin/llama-matched-helper \
  --model models/Qwen3.6-35B-A3B-Q4_K_M.gguf \
  --output-dir /absolute/path/outside-repository/matched-smoke
```

The eight requests account for 17 internal decode calls in the recorded fixture run because JSON generation actually decodes intermediate output tokens. See [NOTICE.md](NOTICE.md) for source and dependency attribution.
