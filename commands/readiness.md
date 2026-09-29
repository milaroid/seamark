---
description: Assess a specific release and environment for production readiness using runtime, deployment, recovery, monitoring, and capacity evidence. Use before launch or after major migration or runtime infrastructure changes; reports findings without fixing the application.
argument-hint: "[release or commit] [target environment]"
model: claude-opus-5-5
effort: high
disable-model-invocation: false
---
# /seamark:readiness - Release Readiness Gate

Target: `$ARGUMENTS`. Resolve omitted values from the current release context;
missing identity or environment is UNVERIFIED, never an assumed production pass.

Read and follow `${CLAUDE_PLUGIN_ROOT}/references/readiness.md`. That shared contract defines
the triggers, permitted work, evidence requirements, check states, verdict, and
handoff for both Claude and Codex. Apply the verification and self-serve rules
from `${CLAUDE_PLUGIN_ROOT}/rules/verification.md` and `${CLAUDE_PLUGIN_ROOT}/rules/self-serve.md`.

## Pipeline integration

When `.seamark/DEVELOP_ACTIVE` exists:

1. Confirm its phase is `readiness` and `.seamark/phase-verify-done` exists. If either
   check fails, report the out-of-order invocation and stop. Do not rewrite the
   active phase to make the invocation fit.
2. Remove a stale `.seamark/phase-readiness-done` from an earlier assessment and create
   `.seamark/phase-readiness-started` before checking. Respect a no-write instruction;
   in that case return the assessment in chat without claiming marker completion.
3. Evaluate the shared contract. On READY, create `.seamark/phase-readiness-done`. On
   BLOCKED or abort, leave it absent. The verdict and evidence must belong to the
   current release; a marker by itself never proves readiness.
4. Return the assessment to `/seamark:develop` for final bookkeeping and cleanup.

Without an active pipeline, run the same assessment in chat and create no phase
markers. This command does not deploy, automatically fix findings, or start a
dashboard.
