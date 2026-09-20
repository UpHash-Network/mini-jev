# Demonstration recording and caption script

Recorded duration: 144.96 seconds (maximum allowed: 150 seconds).

The revised video uses the opt-in presentation view of the actual local demo. It is a continuous screen recording of two live native inference requests. Results are not substituted. English examples illustrate the interface; the paper's quality evaluations are Japanese.

The 1440 × 720 browser capture is resized without cropping to 1920 × 960, with a 120-pixel English caption strip beneath it. The finished video is 1920 × 1080, with no audio track. Primary UI text is 18 px and result values are 34 px before resizing.

Input and all three typed result cards remain visible together in result scenes. Each question's instructions and candidate meanings are shown separately. The JSON request and response are inspected at multiple scroll positions; the full live response is copied with a visible success message and its clipboard contents are verified.

Caption boundaries follow recorded interaction events. The short run explanation remains visible until the result-reading scene. Raw responses and layout checks are in recording/; VIDEO_PROVENANCE.json records source hashes, event times, caption text, and production details.

## English captions

**0.000–7.568 s — MINI JEV / LIVE LOCAL DEMONSTRATION**

Small typed decisions from a frozen language model.
Candidate-token scores become structured values; no answer text is generated.

**7.568–16.626 s — 1 / DEFINE THE ALLOWED ANSWERS**

Choice: define support queues and what each candidate means.
The model selects a key; software constructs the typed response.

**16.626–25.579 s — 2 / DEFINE A BINARY QUESTION**

Noul: ask whether urgency is explicitly requested.
The output is P(true), normalized over the two candidates.

**25.579–34.500 s — 3 / DEFINE ORDERED STAGES**

Score: define ordered, equally spaced priority stages.
The output is their probability-weighted mean, not a class ID.

**34.500–39.000 s — RUN / ACTUAL MODEL INFERENCE**

Run three questions on the live model.
Each question is evaluated separately.

**39.000–51.551 s — INSPECT / URGENT BILLING MESSAGE**

Read the route, urgency probability, and expected priority together.
Each card also shows the distribution over its allowed candidates.

**51.551–57.645 s — CHANGE THE INPUT / RUN AGAIN**

Load a routine account request.
Previous results are marked stale until the next run completes.

**57.645–70.570 s — COMPARE / ROUTINE ACCOUNT MESSAGE**

Compare how the route, urgency probability, and priority change.
These values are live model outputs, not prefilled answers.

**70.570–80.542 s — INSPECT / THE ACTUAL REQUEST**

The request contains the state, instructions, and candidate meanings.
The same interface is available through the Python SDK and HTTP API.

**80.542–99.098 s — INSPECT / THE ACTUAL RESPONSE**

Scroll through the typed answers, probabilities, and calibration metadata.
The full JSON remains available for inspection and export.

**99.098–105.543 s — EXPORT / COPY THE LIVE RESPONSE**

Copy the JSON response for use in your own tools.
The confirmation shows whether the clipboard operation succeeded.

**105.543–118.541 s — INTERPRET / KNOW WHAT THE NUMBERS MEAN**

Probabilities compare allowed candidates only; concentration is not correctness.
A well-typed output can still be semantically wrong.

**118.541–129.572 s — EVIDENCE / WHAT THE PAPER FOUND**

Direct readout and native one-token selection agreed in all 1,350 pairs.
This study did not establish a latency advantage over one-token selection.

**129.572–145.000 s — SOURCE / SETUP AND REPRODUCIBLE ARTIFACTS**

github.com/UpHash-Network/mini-jev  •  branch: research/eacl2027-demo
Follow demo/README.md. Tested on Apple Silicon; model weights are separate.
