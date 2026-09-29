---
max_turns: 45
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash, Write, Edit]
tags: [execution, flow]
---
Invoke Skill seamark:plan. I want a plan for test coverage of evals/fixture/plan/middleware.go. I explicitly delegate selecting the test cases and organizing the test files to you. Keep production behavior and source files unchanged, use only the Go standard library, and do not plan unrelated improvements. Record the plan in .seamark/PLAN.md. This is a plan-only request; no implementation.
