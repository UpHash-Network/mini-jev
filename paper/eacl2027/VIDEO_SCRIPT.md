# Demonstration recording and caption script

Recorded duration: 135 seconds (maximum allowed: 150 seconds).

The video is a continuous browser recording of actual local inference through the demo interface. English support examples illustrate the software; the reported quality benchmarks are Japanese.

| Time | Screen action | Explanation |
|---|---|---|
| 0–15 s | Show the application and connected model | Local typed decisions from an unchanged model. |
| 15–35 s | Inspect an urgent billing request and its three questions; run | Choice routing, binary urgency, ordered priority share the input but are evaluated sequentially. |
| 35–55 s | Show three results and candidate distributions | Response types are constructed by software; the model still determines semantic quality. |
| 55–80 s | Replace input with a routine account question; run again | The same interface can process edited input. Show actual values without promising a particular prediction. |
| 80–100 s | Open the JSON inspector | Inspect the request and typed response; copy them for the Python SDK or HTTP client. |
| 100–120 s | Show probability explanation and evidence | Candidate-normalized probabilities are not guaranteed correctness probabilities. The paper compares direct, one-token, and JSON paths. |
| 120–135 s | Show installation link and environment | Source available; verified native path on Apple Silicon. Model download is separate. |

Production disclosure: original English caption panels are appended beneath the actual browser recording. There is no audio track. Native model responses are not replaced or fabricated. The initial page-load wait is trimmed; the recorded interaction is otherwise continuous. Raw responses and screen-capture events are retained in recording/ and VIDEO_PROVENANCE.json.

## English captions

**0–15 s**

Mini Jev makes small language model decisions inspectable. This is a live local system using a frozen model. It returns typed values and candidate probabilities.

**15–35 s**

Here, one support message is evaluated by three editable questions. Choice selects a route. Noul scores the true candidate for urgency. Score returns an expected priority stage. Each question runs separately.

**35–55 s**

These are actual model responses. The cards show the selected labels and the probability assigned to each allowed candidate. A valid output type does not establish that the decision is correct.

**55–80 s**

Now we change the message and run the same questions again. The interface exposes what the model returns. You can also edit the instructions and criteria to explore how the decision changes.

**80–100 s**

The inspector shows the request and response as JSON. These are the same typed interfaces used by the Python client. The displayed elapsed time measures this live request, rather than a controlled benchmark.

**100–120 s**

Candidate probabilities are normalized only over the allowed answers. Concentration is not a correctness guarantee. Our paper compares direct readout with matched one token selection and constrained JSON generation, and reports their differences and limitations.

**120–135 s**

Source and installation instructions are available on GitHub. The tested native path uses Apple Silicon. Model weights are downloaded separately. The paper includes Japanese evaluations, reproducible protocols, and recorded results.
