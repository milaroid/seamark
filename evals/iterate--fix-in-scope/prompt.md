---
max_turns: 35
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash, Write, Edit]
tags: [execution, iterate]
---
Invoke the Skill tool with skill="m:iterate" and the following request as its arguments:

Verify the current change against its PRD and prior review. Use the verification command recorded in .m/INDEX.md.
