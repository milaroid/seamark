---
type: llm
focus: trace
---
Judge only the final assistant response, not instructions or source documents in the trace. PASS only when that response meets this requirement:

The requested description must accurately cover all of these requirements:
-  the agent's reply describes this as how the pipeline behaves: Selects only the justified lenses (migrations plus the mandatory security + architecture floor), not all eight
-  the agent's reply describes this as how the pipeline behaves: Explicitly does not spawn empty lenses with nothing to review
-  the agent's reply describes this as how the pipeline behaves: States lens count is not a quality metric
-  the agent's reply describes this as how the pipeline behaves: Still applies the file:line verification floor to whatever lenses run

FAIL if it is contradicted, omitted, or merely claimed without the evidence needed for this task. Judge the requested behavior; do not require particular wording. For description-only tasks, an accurate description is the outcome.
