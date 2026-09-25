---
max_turns: 45
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash, Write, Edit]
tags: [execution, flow]
---
Invoke Skill m:refine. Produce a specification for CSV export of the current filtered report on reports.html using Report in reports.go. The desired end state is: a logged-in user clicks an Export CSV button beside the existing filter and downloads exactly the currently displayed rows, in their current order. Settled choices: GET /reports/export.csv; reuse existing authorization; no new roles or data access; UTF-8 CSV with a header, comma separator, CRLF rows, RFC-style doubled quotes and quoted cells when needed; prefix cells starting with =, +, -, or @ with an apostrophe; Content-Disposition filename report.csv; header-only export for zero rows; no background jobs, new filters, or layout redesign. Record the spec under .m/. This request is refinement only.
