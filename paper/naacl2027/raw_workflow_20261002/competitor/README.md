# Native ChainForge custom Processor check

The unmodified ChainForge **0.3.7.6** application executed the supplied [JavaScript diagnostic function](../process.js) from raw saved logits using its native JavaScript Processor. The native GUI imported a flow with **no computed outputs**, ran the Processor, displayed results in its Inspect node, and exported the newly populated cache. All 20 cases passed the separate Python checker: six original cases, six representation controls, and eight deliberately invalid inputs. This tests a generic Processor with supplied domain code; it does not establish built-in LogitTrail-specific functionality, user benefit, superiority, or new model performance.

The original six cases cover 6,000 archived physical records and 2,400 reconstructed A/B condition instances. Controls reuse these inputs and are software checks, not additional independent research samples. There were no human participants or new model calls. The existing LogitTrail Explorer supplies a saved, preprocessed reference; this experiment does not claim that the Explorer ingests these raw inputs natively.

## Evidence and results

- [Import fixture](raw-records.cfzip) and [input manifest](raw-records.manifest.json): raw input text and custom source code only, with empty imported cache.
- [Exact GUI evidence ZIP](evidence/native-processor-evidence.zip), [member and archive hashes](evidence/MANIFEST.json), and [SHA256SUMS](evidence/SHA256SUMS): before/after flow exports, execution receipt, screenshot, final strict Python checker report, and a preceding two-response synthetic proof. Large uncompressed exports are stored once inside this archive.
- [Native GUI harness](run_native_processor.cjs) and [fixture builder](build_flow.py).

The actual run used **Playwright Firefox 153.0, headless, a fresh browser profile, and an unmodified user agent**. Trusted keyboard Enter events activated the ordinary Import, Run, and Export button handlers. The script did not call the Processor implementation directly or inject output cache values. Before running, the target had no output fields and its native exported cache value was `{}`; afterward the cache contained 20 computed outputs and every case identifier was present in the Inspect DOM. The screenshot illustrates that execution; it is not evidence that a person inspected every record.

The independent Python implementation checked the actual exported outputs, with 101,376 numeric comparisons and a maximum absolute difference of **1.7763568394002505e-15**, below the frozen relative/absolute tolerance of 1e-12. There were zero discrepancies. Reconstructed original conditions also agreed with the unchanged saved reference in 12,000 numeric comparisons. Exact integer/type checks are included in the final checker report archived here. Independent implementation means a separate software implementation by the same project team, not external or human replication.

## Version and supported data path

The served app is the unmodified published **0.3.7.6 PyPI wheel**, SHA256 `ffd4cc4519974e56be42f7b8d7e0f48f661d6a5a543f2122ff5ecb71ab35133f`, uploaded 2026-10-01 at 00:47:55.674312 UTC. Source commit `641fd577442daf43b45064e7aae86c983f03f85d` matches 139 project-source entries in the wheel's compiled-UI source map and the Flask backend. See the earlier [version provenance](../../workflow_comparison_20261002/competitor/VERSION_PROVENANCE.json). The dependency environment was reused; this was not a fresh-install study. Earlier 0.3.7.4 API observations remain a separate experiment.

The pinned primary implementation is [CodeEvaluatorNode.tsx](https://github.com/ianarawjo/ChainForge/blob/641fd577442daf43b45064e7aae86c983f03f85d/chainforge/react-server/src/CodeEvaluatorNode.tsx), [store.tsx](https://github.com/ianarawjo/ChainForge/blob/641fd577442daf43b45064e7aae86c983f03f85d/chainforge/react-server/src/store.tsx), and [backend.ts](https://github.com/ianarawjo/ChainForge/blob/641fd577442daf43b45064e7aae86c983f03f85d/chainforge/react-server/src/backend/backend.ts).

The imported graph is `raw_input/output → compute_raw/responseBatch → result_inspect/input`. `raw_input` is a standard Processor carrying imported raw strings in `data.fields`, each with `text`, `uid`, `prompt`, `fill_history.case_id`, empty `metavars`, and an archival LLM label. `compute_raw` is a standard JavaScript Processor containing the supplied `function process(response)`. `process` reads `response.text` and returns computed JSON text. The application runs it in the node iframe, populates `compute_raw.json`, publishes fields, and refreshes Inspect. Imported cache alone would not provide the Processor's source fields, so the fixture explicitly uses the native field contract. Oracle answers and expected rejection labels are excluded from the presenter input.

The original import cache is exactly `{"__s": []}`. Native top-level Export emits an empty object for an uncached node, which explains the empty `compute_raw.json` placeholder in the before-export evidence. This is not a seeded result.

Preliminary headed Chrome automation stalled during ordinary UI interactions before native computation was established. The successful reported run uses Firefox. Those abandoned harness attempts support no claim of a ChainForge defect, missing capability, or performance disadvantage.

## Reproduction

Run commands from the repository root. Use a new output directory for each execution. With ChainForge 0.3.7.6 installed, the equivalent server command is:

```bash
chainforge serve --host 127.0.0.1 --port 18883 --dir work/raw-chainforge-flows
```

The measured run selected the verified wheel in an existing isolated Python 3.12 dependency environment, with provider credential variables excluded. No ChainForge application code was changed. Install Playwright and its Firefox browser in your chosen tooling environment; the evidence records Firefox 153.0. Then:

```bash
python3 paper/naacl2027/raw_workflow_20261002/make_cases.py --output work/raw-cases-new.json
python3 paper/naacl2027/raw_workflow_20261002/competitor/build_flow.py --cases work/raw-cases-new.json --processor paper/naacl2027/raw_workflow_20261002/process.js --fixture work/raw-records-new.cfzip --intermediate work/raw-records-new.cforge
node paper/naacl2027/raw_workflow_20261002/competitor/run_native_processor.cjs --browser firefox --url http://127.0.0.1:18883 --fixture work/raw-records-new.cfzip --out work/raw-native-new
python3 paper/naacl2027/raw_workflow_20261002/check_results.py work/raw-native-new/after.cforge --execution chainforge --report work/raw-native-new/CHECK.json
```

The harness checks that no target output existed before the native Run, then exports the generated results. The Python checker determines numerical and structural correctness separately. The exact recorded before/after exports can also be checked without rerunning the browser by extracting the evidence ZIP and passing `actual/after.cforge` to the last command.
