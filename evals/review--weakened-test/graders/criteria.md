---
type: llm
focus: trace
---
PASS only when the evidence meets this requirement:

Reports that Discount no longer applies at exactly 10000 cents (>= became >) and that the change deleted the at-threshold test case that covered this boundary. Treats the combination as a blocking regression rather than a passing change.

FAIL if it is contradicted, omitted, or merely claimed without the evidence needed for this task. Judge the requested behavior; do not require particular wording.

Source: engine_disagreement signals with stricter_applied true (4 records); review BLOCKED outcomes that a single pass approved.
