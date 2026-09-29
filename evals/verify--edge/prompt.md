---
max_turns: 35
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash, Write, Edit]
tags: [execution, verify]
---
Invoke the Skill tool with skill="seamark:verify" and the following request as its arguments:

Verify the current change with the command recorded in .seamark/INDEX.md. A previous check gave an intermittent result; investigate it before judging completion.
