---
max_turns: 35
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash, Write, Edit]
tags: [execution, plan]
---
Invoke the Skill tool with skill="m:plan" and the following request as its arguments:

Plan improvements to our codebase. I have not selected an intended outcome or delegated scope selection; ask me to choose the outcome before turning observations into implementation tasks.
