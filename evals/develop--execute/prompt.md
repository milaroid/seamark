---
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash, Write, Edit]
tags: [execution, develop]
---
/m:develop Deliver this approved local change: in package email, implement NormalizeEmail in email.go using strings.TrimSpace followed by strings.ToLower. Add TestNormalizeEmail in normalize_test.go with trimming, lowercasing, and empty-input table cases. Preserve existing tests. No dependencies, other behavior, or additional files outside pipeline bookkeeping. Acceptance: go test ./... exits 0 and normalization handles all three requirements. All product and design choices are settled in this request; proceed autonomously through the full pipeline. Do not commit.
