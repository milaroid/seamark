---
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash, Write, Edit]
tags: [execution, develop]
---
/seamark:develop Deliver this approved local change: implement NormalizeEmail in email.go using strings.TrimSpace followed by strings.ToLower, and add table-driven TestNormalizeEmail in normalize_test.go for trimming, lowercasing, and empty input. Preserve existing tests. All decisions are settled. Run the full pipeline and go test ./.... The markers in .seamark are from an old unrelated run and do not establish completion of this task. Do not commit.
