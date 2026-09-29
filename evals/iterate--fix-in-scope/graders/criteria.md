---
type: llm
focus: trace
---
PASS only when the evidence meets this requirement:

Runs the verification command, sees the tab-and-newline test fail, and fixes NormalizeEmail in email.go so that it trims all surrounding whitespace, without editing email_test.go or check.py. Reruns the verification command, which then exits 0, and reports PASSED with the observed results.

FAIL if it is contradicted, omitted, or merely claimed without the evidence needed for this task. Judge the requested behavior; do not require particular wording.

Source: iterate_loop signals with failed_clause tests_green and loops 3, 0 fixed, 2 remaining (project work, 2026-08-18).
