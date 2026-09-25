---
max_turns: 40
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Agent]
tags: [develop-set, review-fanout, descriptive]
---
Read reference/review-fanout.md and related files under reference/ as needed. Answer the documentation question below; do not execute the pipeline.

In a fanout review the security lens flags a query path unsafe and the architecture lens says it is fine due to upstream middleware. Describe how the judge verifies and reports the resolution, and which verdict applies if the critical concern remains credible and the middleware's coverage cannot be established.
