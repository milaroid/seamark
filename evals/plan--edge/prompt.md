---
max_turns: 35
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash, Write, Edit]
tags: [execution, plan]
---
Invoke the Skill tool with skill="seamark:plan" and the following request as its arguments:

Plan the migration of our auth layer to a third-party library none of us has used before; we are unsure of its session model.
