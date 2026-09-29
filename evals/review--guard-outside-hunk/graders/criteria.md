---
type: llm
focus: trace
---
PASS only when the evidence meets this requirement:

Does not report a nil pointer dereference of a.Owner in greeting.go as a finding, because LoadAccount in store.go returns ErrNotFound when Owner is nil and Greeting returns that error first. If the review mentions the dereference, it cites the LoadAccount guard as the reason it is safe. The verdict is not BLOCKED.

FAIL if it is contradicted, omitted, or merely claimed without the evidence needed for this task. Judge the requested behavior; do not require particular wording.

Source: review_precision signals, findings_survived below half on single-pass reviews (42 of 95 records); ADAPTATIONS.md 2026-09-15 notes findings disproved by guard lines outside the diff hunks.
