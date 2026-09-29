---
max_turns: 45
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash, Write, Edit]
tags: [execution, flow]
---
Invoke Skill seamark:review-fanout. The blind lens passes are already complete in .seamark/lens-reports.md. Perform the judge reconciliation and final verdict now, using the actual source files. Reuse the supplied lens reports rather than spawning new lens passes. No second engine is configured. Do not modify source or the supplied reports, and do not post anywhere.
