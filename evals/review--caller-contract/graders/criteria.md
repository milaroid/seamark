---
type: llm
focus: trace
---
PASS only when the evidence meets this requirement:

Reports that ParseAmount now returns cents while LineTotalCents in invoice.go, which is outside the diff, still multiplies the result by 100, so line totals become 100 times too large. Cites invoice.go and treats the defect as blocking.

FAIL if it is contradicted, omitted, or merely claimed without the evidence needed for this task. Judge the requested behavior; do not require particular wording.

Source: engine_disagreement signals with stricter_applied true: the second engine returned BLOCKED where Claude returned APPROVED WITH WARNINGS (4 records).
