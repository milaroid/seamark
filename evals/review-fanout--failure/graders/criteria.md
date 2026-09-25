---
type: llm
focus: trace
---
Judge only the final assistant response, not instructions or source documents in the trace. PASS only when that response meets this requirement:

The requested description must accurately cover all of these requirements:
-  the agent's reply describes this as how the pipeline behaves: The judge reads the cited middleware before deciding rather than averaging the lenses
-  the agent's reply describes this as how the pipeline behaves: Shows the resolution with its evidence rather than silently dropping a side
-  the agent's reply describes this as how the pipeline behaves: Applies stricter-verdict-wins when unresolved (the permissive view does not win by default)
-  the agent's reply describes this as how the pipeline behaves: Does not emit APPROVED while a credible critical is unresolved

FAIL if it is contradicted, omitted, or merely claimed without the evidence needed for this task. Judge the requested behavior; do not require particular wording. For description-only tasks, an accurate description is the outcome.
