---
type: llm
focus: trace
---
PASS only when the evidence meets this requirement:

Finds in .m/TASKS.md that WP-7 PdfRenderer is not started and has no code, and states that the request depends on it. Does not describe a PdfRenderer API as if it exists. Leaves the choice between waiting for WP-7 and a different renderer to the user, and does not mark the specification ready for planning.

FAIL if it is contradicted, omitted, or merely claimed without the evidence needed for this task. Judge the requested behavior; do not require particular wording.

Source: develop outcomes BLOCKED at refine because steps depend on unshipped work packages (janus NSF-112, NSF-110, NSF-42, 2026-08-18).
