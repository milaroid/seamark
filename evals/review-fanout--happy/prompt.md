---
max_turns: 40
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Agent]
tags: [develop-set, review-fanout, descriptive]
---
Read reference/review-fanout.md and related files under reference/ as needed. Answer the documentation question below; do not execute the pipeline.

A change touches a handler, service, repository, and a SQL migration across 6 files in a Go backend. Without performing the review, describe how /m:review-fanout structures it.
