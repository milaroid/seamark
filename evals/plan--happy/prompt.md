---
max_turns: 35
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash, Write, Edit]
tags: [execution, plan]
---
Invoke the Skill tool with skill="seamark:plan" and the following request as its arguments:

Here is a refined spec: add a rate limiter (100 req/min per API key) to the existing HTTP gateway (source under evals/fixture/plan/). All product decisions are settled in this spec and no further requester input is available — state any residual assumptions explicitly and produce the implementation plan. Settled decisions: in-process fixed-window counters in a mutex-guarded map keyed by X-API-Key (stdlib only, no new dependencies); limiter positioned between WithAuth and WithLogging; per-key entries swept after 10 idle minutes; 429 with Retry-After on limit.
