# ChainForge and Ollama scope, 2 October 2026

The appropriate claim for LogitTrail is a specific frozen-evidence inspection
workflow with explicit provenance and shared-call accounting. Local typed
decisions, candidate probabilities, judge comparison and probability-based
diagnostics already overlap with other tools.

**Executed evidence remains the September 25 custom-provider diagnostic:**
ChainForge 0.3.7.4 registration/dispatch with four synthetic request pairs,
eight typed answers and three rejected invalid requests. The complete typed
payload was returned by the adapter. That establishes backend interoperability
and information availability, with zero probability difference in those pairs.
The ChainForge GUI was not tested. See the unchanged
[earlier diagnostic](../chainforge_integration/README.md).

**New inspection is source/documentation only.** The pinned ChainForge commit
is `641fd577442daf43b45064e7aae86c983f03f85d`. Fetched-file hashes and URLs are
recorded in [competitor_sources.json](competitor_sources.json); no model or
ChainForge GUI was run, and source version 0.3.7.6 is not treated as proof of a
published package version.

1. ChainForge added a standard Ollama decision provider, using `/v1/systemone`
   and the shared typed-question route. The source handles binary, categorical
   and ordinal rubric questions. A following change expands rubric variables
   per response. These are more substantial overlaps than a generic chat-tool
   comparison would suggest. [Provider commit](https://github.com/ianarawjo/ChainForge/commit/94faf02cc403c3e54cf4d1c658d02f9a73b8f066),
   [rubric commit](https://github.com/ianarawjo/ChainForge/commit/641fd577442daf43b45064e7aae86c983f03f85d).
2. Its scorer source contains judge-agreement and disagreement computations and
   reliability summaries, with corresponding calls in the scorer component.
   The inspected response-conversion helper represents Choice by its selected
   label and selected-label probability; it converts Score expectation from
   zero-based to one-based and rounds to three decimal places. That helper's
   behavior does **not** prove raw candidate vectors are unavailable elsewhere
   in caches, exports or the GUI. [Pinned scorer source](https://github.com/ianarawjo/ChainForge/blob/641fd577442daf43b45064e7aae86c983f03f85d/chainforge/react-server/src/backend/scorerFormat.ts),
   [conversion helper](https://github.com/ianarawjo/ChainForge/blob/641fd577442daf43b45064e7aae86c983f03f85d/chainforge/react-server/src/backend/utils.ts#L1165-L1195),
   [scorer component](https://github.com/ianarawjo/ChainForge/blob/641fd577442daf43b45064e7aae86c983f03f85d/chainforge/react-server/src/LLMEvalNode.tsx#L753-L785).
3. Official Ollama documentation independently describes local System One
   decisions using version 0.35.0 or later and Nimble, with no API key for local
   calls. Its example Choice response includes the whole candidate distribution;
   yes/no and ordinal tasks are also documented. These are documented features,
   not a newly measured runtime result here. [Official decision documentation](https://docs.ollama.com/capabilities/decision).

The full-vector semantic-order comparison, shared physical-call union, and
frozen-ZIP line tracing in this audit are directly verified for LogitTrail and
its complete JSON baseline. Comparable ChainForge configurations have not been
run on these same frozen records; mark that scope **unverified**, not absent.
The published adapter makes complete information available and could support
such a study. Different Nimble/Tev models must not be substituted and then
described as a same-model comparison with the frozen Qwen records.

This evidence supports neither a speed/accuracy superiority claim nor a claim
that LogitTrail is the first local typed-decision interface. Source inspection
and an exact-record functional audit are distinct from an end-to-end competing
GUI study; the latter remains optional future work.
