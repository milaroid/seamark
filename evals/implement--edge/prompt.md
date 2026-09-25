---
max_turns: 35
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash, Write, Edit]
tags: [execution, implement]
---
Invoke the Skill tool with skill="m:implement" and the following request as its arguments:

Implement the approved plan task that says 'persist the session token' but the plan never says where (cookie, localStorage, or server-side) or with what expiry.
