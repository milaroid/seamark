---
type: llm
focus: trace
---
Judge only the final assistant response, not instructions or source documents in the trace. PASS only when that response meets this requirement:

The requested description must accurately cover all of these requirements:
-  the agent's reply describes this as how the pipeline behaves: Spawns multiple lens subagents in parallel, at least security and architecture
-  the agent's reply describes this as how the pipeline behaves: Keeps each lens blind to the others' output
-  the agent's reply describes this as how the pipeline behaves: Runs a judge pass that deduplicates and re-verifies critical and high findings against cited files
-  the agent's reply describes this as how the pipeline behaves: Produces one reconciled verdict, not per-lens verdicts

FAIL if it is contradicted, omitted, or merely claimed without the evidence needed for this task. Judge the requested behavior; do not require particular wording. For description-only tasks, an accurate description is the outcome.
