# Mini Jev: local decision workbench

A browser interface for the existing Mini Jev HTTP API. Enter one support message, edit three questions, and inspect a **Choice**, **Noul**, and **Score** from the live resident model. There are no stored answers, mock mode, or replay path in the application. Fake engines exist only in the CPU tests.

The interface and bridge use static HTML/CSS/JavaScript and Python 3.10+ standard-library code. No package manager, remote font, analytics, CDN, or frontend build is needed.

## Start the demo

Run these commands from the repository root. The UI and model API are separate processes.

1. Prepare the native model service using the [root installation instructions](../README.md#run-the-native-service). The tested native runtime requires an Apple Silicon Mac, macOS 26.4+, Xcode command-line tools, CMake, Git, and a 20.4 GB GGUF download. The measured hardware has 64 GB memory; lower-memory machines are not validated. Model weights and native binaries are not included in the source package.
2. In one terminal, start the model API:

   ```sh
   ./run.sh --without-calibration
   ```

3. In another terminal, start this interface:

   ```sh
   python3 -m demo.server
   ```

4. Open **http://127.0.0.1:8766/**. Wait for **Model API ready**, then select **Run decisions**. Stop either process with Control+C.

If the model download fails with `CERTIFICATE_VERIFY_FAILED`, certificate setup depends on your Python distribution. Identify the interpreter with `python3 -c "import sys; print(sys.executable)"`. For a **python.org macOS installation**, run its bundled `Install Certificates.command` in that Python version's Applications folder, following the [official Python macOS installation guide](https://docs.python.org/3/using/mac.html#installation-steps). For other distributions or managed networks, follow their certificate/trust-store instructions. Retry with the same interpreter after setup; keep TLS certificate verification enabled.

The UI can start before the model API; it will show an offline message and keep inference disabled until the API is ready. It never downloads or initializes a model. Startup and model download are not included in the displayed inference timing.

For alternative ports:

```sh
./run.sh --without-calibration --port 8875
python3 -m demo.server --port 8876 --api-url http://127.0.0.1:8875
```

The default upstream timeout is 35 seconds (`--api-timeout`, maximum 60 seconds). The browser deadline adds eight seconds. A timeout does not guarantee that model computation has stopped; wait before trying again. This demo submits only one request at a time, containing its three questions.

## Demonstration workflow

1. Start with **Urgent billing request** and run the decisions. Read the semantic queue key, the probability of explicit urgency, and the expected priority stage.
2. Expand any **Questions & candidates** entry. Instructions and descriptions are editable. Choice keys can be edited; candidates or Score stages can be added or removed within the API's 2–26 limit. Noul always has false and true meanings. Score stage indices are ordered and equally spaced.
3. Select **Routine account request**, choose **Load example**, and run again. Changing inputs marks previous results as stale until another live request completes. No expected answers are inserted into the UI.
4. Inspect every candidate probability and **Concentration**. Concentration is one minus normalized entropy, not the probability of correctness. Probabilities are conditional on the allowed candidates; calibration and semantic accuracy are separate questions.
5. Open **Inspect the API exchange**. Copy the current request or last SDK-validated response to use from Python or curl. The last response always belongs to the last completed request; it is not rewritten when inputs change.

These English examples illustrate the interface. Published quality evaluations are Japanese and do not validate these demonstration examples. This UI uses the production direct-readout API, not the paper's separate three-mode timing harness. No generated explanation, shared prefill, or concurrent question processing is claimed.

The displayed **Browser round-trip** uses the browser's monotonic clock around its fetch and JSON parsing. **Bridge → API** includes SDK validation, local API transport, and response validation. The copied response also contains the API's own `latency_ms`; these boundaries differ. Values are actual observations for that request and are not a production SLA. The token total includes all three independently formatted questions; direct readout reports zero generated output tokens.

All controls are reachable by keyboard. Use Tab/Shift+Tab, Enter to activate buttons, and Enter/Space on expandable questions and the JSON inspector. Controls have visible focus, form labels, loading/error announcements, and a mobile layout. Clipboard access may require browser permission; JSON remains selectable if it is denied.

## Presentation view

For a screen recording or live audience, open **http://127.0.0.1:8766/#presentation**. Use the URL fragment, not `?presentation=1`: the server deliberately serves only its explicit routes. Open `/#standard` to return to the usual layout. Switching views changes presentation only; the request, model, candidate scores, and inference path are identical.

At 1280×720 or 1440×720 browser viewport size, the presentation layout places the editable message, Run button, and three result cards in one view for the two included examples. Result values use 34 px text; state, candidate labels/probabilities, concentration, and result status use 18 px or larger. The layout avoids browser zoom or cropping. Arbitrarily long user inputs, additional candidates, or larger accessibility text may need scrolling.

Keep the page at the top for the result scene. The smaller **Bridge → API** timing and temperature metadata remain available in the standard layout and JSON exchange; presentation view emphasizes the measured browser round-trip and actual token counts. Edited inputs visibly mark prior results with an 18 px **INPUTS CHANGED · RUN AGAIN** label and dashed outline. A completed new request clears that marking.

Scroll down for **Questions & candidates**. Open one question at a time to show its full instructions and candidate meanings. In this view, candidate descriptions use wrapping textareas; editing them has exactly the same effect as in the standard form. In particular, the Noul and Score instructions refer to urgency/timing **explicitly expressed by the message**, not an objective assessment of the customer's circumstances.

The JSON inspector uses one column with 18 px text and a 470 px scrollable area for each exchange. Show the current request and last response as separate scenes; each Copy button has its own visible success/failure message directly below that JSON area. Clipboard success is reported only after the browser's write operation succeeds. All results still come from live API calls; presentation view adds no saved-result or replay path.

## Local boundary

The bridge binds only `127.0.0.1`. It serves an explicit static-file allowlist and accepts only the matching loopback Host/port. API routes require a custom header; inference additionally requires the exact same browser Origin. Cross-site requests are rejected, no CORS headers are added, and a restrictive content security policy blocks external scripts, framing, and remote resources.

The Python SDK forwards requests to the separately configured loopback API; browser Origin headers are **not** forwarded. The existing API's browser-Origin rejection and its validation remain unchanged. The bridge rejects duplicate JSON keys, unknown schema fields, invalid types, oversized inputs (64 KiB total; 8,192 characters per text), ambiguous HTTP framing, unsupported encodings, and requests other than the three typed demo questions. The upstream API separately checks the complete tokenized context and its runtime limits.

Body reads have a five-second deadline, connections and in-flight inference are bounded, and no prompt/body logging or browser local-storage persistence is added. Local processes can still access the local services; this is not an authenticated multi-user deployment or a public web host.

## CPU tests

```sh
python3 -m unittest demo.test_demo -v
```

Tests run real local HTTP servers and the existing SDK against a test-only fake engine, using ephemeral ports. They cover three typed responses, unchanged upstream Origin rejection, static routes, readiness, Host/Origin/custom-header restrictions, request framing and size, schema rejection, inference concurrency, connection errors, and timeouts. They do not download a model, call the real service on port 8765, or use a GPU.

Browser interaction and live model behavior should be checked separately on the installed runtime before recording a demonstration.
