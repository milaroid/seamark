---
type: llm
focus: trace
---
Judge only the final assistant response, not instructions or source documents in the trace. PASS only when that response meets this requirement:

The requested description must accurately cover all of these requirements:
-  the agent's reply describes this as how the pipeline behaves: Names the phases as discrete Skill calls in order: refine then plan then implement then review then verify
-  the agent's reply describes this as how the pipeline behaves: States the phase-marker gate between phases (verify phase-<x>-done before advancing)
-  the agent's reply describes this as how the pipeline behaves: Selects the review variant by change shape and notes that the second engine runs automatically on review when second_engine.provider is codex or kimi (config-driven via .seamark/pipeline.yml, not a high-stakes prompt gate)
-  the agent's reply describes this as how the pipeline behaves: Describes the verify four-clause (including PRD Success Criteria) exit predicate as the completion gate, not loop count

FAIL if it is contradicted, omitted, or merely claimed without the evidence needed for this task. Judge the requested behavior; do not require particular wording. For description-only tasks, an accurate description is the outcome.
