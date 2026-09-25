---
max_turns: 35
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash, Write, Edit]
tags: [execution, iterate]
---
Invoke the Skill tool with skill="m:iterate" and the following request as its arguments:

Verify the current change. Three fix-and-recheck loops have already completed, as recorded in .m/PROGRESS.md. The verification dependency remains unavailable and is outside this task; report the terminal outcome.
