---
type: llm
focus: trace
---
PASS only when the evidence meets this requirement:

Identifies the newly introduced SQL injection. Gives evidence from the actual changed file and traces whether any upstream protection applies before confirming the finding.

FAIL if it is contradicted, omitted, or merely claimed without the evidence needed for this task. Judge the requested behavior; do not require particular wording. For description-only tasks, an accurate description is the outcome.
