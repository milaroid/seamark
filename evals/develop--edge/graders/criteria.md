---
type: llm
focus: trace
---
Judge only the final assistant response, not instructions or source documents in the trace. PASS only when that response meets this requirement:

The requested description must accurately cover all of these requirements:
-  the agent's reply describes this as how the pipeline behaves: Routes into refine FIRST rather than planning or implementing
-  the agent's reply describes this as how the pipeline behaves: Has refine grill the ambiguity with bounded-menu questions before any plan
-  the agent's reply describes this as how the pipeline behaves: Does not fabricate scope or skip ahead to implementation
-  the agent's reply describes this as how the pipeline behaves: Keeps refine as its own Skill invocation, not inlined

FAIL if it is contradicted, omitted, or merely claimed without the evidence needed for this task. Judge the requested behavior; do not require particular wording. For description-only tasks, an accurate description is the outcome.
