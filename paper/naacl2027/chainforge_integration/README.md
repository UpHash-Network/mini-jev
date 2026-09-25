# ChainForge custom-provider integration check

This is a small engineering diagnostic, **not a human study, browser-interface
comparison, speed benchmark, or independent task-quality evaluation**. It uses
unmodified ChainForge 0.3.7.4 registration and dispatch routes through Flask's
in-process HTTP test client, and real HTTP calls to Mini Jev's native model API.
The only custom ChainForge component is the documented provider adapter.

## Result, 25 September 2026

- Four synthetic request pairs cover eight typed-answer pairs: Choice, Noul and
  Score, a changed state, Japanese keys/text, and an explicitly ordered rubric.
- Both routes return the same labels, model, usage and semantic metadata.
  Maximum absolute candidate-probability difference: **0.0** (frozen tolerance
  `1e-4`). These are separately executed requests, not a replayed answer.
- All eight returned SDK/provider objects pass the existing strict response
  validator after removing optional null fields introduced by dataclass export.
- Three invalid inputs are rejected: malformed JSON, an empty question set, and
  chat history that this stateless adapter does not support.
- Eight native HTTP calls execute sixteen individual typed questions. These
  diagnostics are separate from the paper's 26,050 research-harness requests.
- No provider-specific model was trained. No external inference API was used.

`protocol.json` was saved before inference; its SHA-256 is recorded in
`results.json`. The record also identifies the actual installed ChainForge
dispatch source, adapter, runner, model health and every observed response.
`WHEEL.json` identifies the downloaded official wheel; the complete observed
Python environment is in `requirements-observed.txt`.

## Reproduce

From the Mini Jev repository root, create an isolated Python 3.12 environment
and install `chainforge==0.3.7.4` (or use the observed requirements file).
Start the native API as described in the main README; the recorded run used
the rebuilt runtime and cached, verified model from the reproducibility study,
without temperature calibration, at `http://127.0.0.1:8875`.

```sh
env PYTHONPATH=. /path/to/chainforge-venv/bin/python \
  paper/naacl2027/chainforge_integration/run_checks.py \
  --api-url http://127.0.0.1:8875 --output /tmp/chainforge-recheck.json
```

The runner uses a temporary ChainForge flow/cache directory and does not read
the user's saved flows or credentials. It does not change ChainForge's access
controls. Each SDK call is immediately followed by the matching provider call;
this order is fixed, not randomized, and no latency inference is made.

## Adapter contract and inspection use

`provider.py` implements the official
[custom-provider interface](https://chainforge.ai/docs/custom_providers/).
Its input string is one JSON Mini Jev request with `state` and `questions`.
Its output is a JSON string containing both the input request and the complete
typed response. Mini Jev's SDK validates the request and response. All candidate
probabilities, typed values, calibration/concentration metadata, request ID,
model and latency are available to an inspecting client.

The registration endpoint was exercised with the exact provider source, and
the real dispatch endpoint called the registered function. **The visual
ChainForge flow editor was not tested in this diagnostic.** A graph using this
adapter must supply the JSON request as its rendered prompt, without changing
JSON braces through template expansion. This result establishes backend
interoperability and information availability; it establishes no difference
in human task time, task success, or interface usability.

Primary sources: [ChainForge](https://github.com/ianarawjo/ChainForge),
[custom providers](https://chainforge.ai/docs/custom_providers/),
[pinned package](https://pypi.org/project/chainforge/0.3.7.4/).
