# Execution and automation-development notes

The protocol and six selected cases were fixed before case-level GUI execution.
Previous study results were known. These notes distinguish harness development
from application behavior; failed automation is not counted as failed diagnosis
or an absent competitor feature.

- The first LogitTrail/JSON browser attempt read `innerText` from a collapsed
  details section, obtaining an empty string. Opening the section before reading
  corrected the harness. The completed run is `logittrail-run02`.
- A preliminary headless Chromium session reached ChainForge's unsupported-browser
  message. The final check uses an ordinary installed Google Chrome, headed, with
  a fresh profile. No user-agent patch or modified application was used. Browser
  versions differ between presenters, precluding a browser-performance comparison.
- The first primary ChainForge harness matched both a hidden and a visible search
  input. Restricting the locator to the visible input resolved that ambiguity.
  The completed `chainforge-run02` established filtering and exports.
- An exploratory processor-modal probe timed out after using an unqualified dialog
  selection. Hidden mounted dialogs make that result inconclusive. It establishes
  no product defect, missing feature or performance bound. A proposed alternative
  fixture was set aside; the original v1 import fixture remained unchanged.
- `chainforge-run03` adds direct opening of all twelve response lightboxes, scoped
  to the visible dialog, and is the final published GUI evidence. It also repeats
  the native spreadsheet and complete-flow downloads needed for this final run.
- The spreadsheet checker initially treated the canonical probability list as a
  dictionary. The corrected checker pairs it with `canonical_keys`; all 52 actual
  numeric cells and twelve compact condition/source JSON records agree. A separate
  standard-library ZIP/XML reader confirms the result.
- A later public-route navigation check initially omitted the URL hash delimiter
  in its input URL. Fixing the test URL preserved selections in both directions at
  desktop and mobile widths. This was not a product data defect.

No case was replaced because of an outcome, no probability tolerance was relaxed,
and no failed harness attempt became a human observation. Local exploratory logs
are retained; final reproducible scripts, reports, screenshots and compact native
spreadsheet are published. The full exported flow is retained locally with its
SHA-256 receipt because the same six large payloads are already in `tasks.json`
and the reproducible import fixture.

Preparation involved installing/selecting the pinned package, inspecting its
native import schema, constructing two cache-holder and two Inspector nodes, and
mapping existing canonical fields into native variables and named numeric scores.
The supplied adapter code documents that customization. No clean-install time,
human setup effort, task time or superiority is claimed.
