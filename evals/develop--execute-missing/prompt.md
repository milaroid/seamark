---
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash, Write, Edit]
tags: [execution, develop]
---
/seamark:develop Resume delivery of this approved local change: implement NormalizeEmail in email.go using strings.TrimSpace followed by strings.ToLower and add table-driven TestNormalizeEmail in normalize_test.go for trimming, lowercasing, and empty input. Preserve existing tests. All decisions are settled. The previous run stopped with a missing plan completion marker. Follow the full pipeline for this invocation and verify go test ./.... Do not commit.
