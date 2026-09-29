---
type: llm
focus: trace
---
Judge only the final assistant response, not instructions or source documents in the trace. PASS only when that response meets this requirement:

The requested description must accurately cover all of these requirements:
-  the agent's reply describes this as how the pipeline behaves: Refuses to skip refine and plan
-  the agent's reply describes this as how the pipeline behaves: States no stage is optional and there is no trivial-enough bypass
-  the agent's reply describes this as how the pipeline behaves: Does not collapse the pipeline to implement-only
-  the agent's reply describes this as how the pipeline behaves: Explains refine/plan front-load the assumptions that keep downstream cheap

FAIL if it is contradicted, omitted, or merely claimed without the evidence needed for this task. Judge the requested behavior; do not require particular wording. For description-only tasks, an accurate description is the outcome.
