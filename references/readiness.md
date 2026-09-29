# Release readiness contract

Shared by Claude's `/m:readiness` command and the Codex `m-pipeline` adapter.
Both drivers use this contract for scope, evidence states, and the release verdict.

## When the gate runs

Run after a successful `/m:iterate` when `/m:develop` is delivering a launch,
release, deployment, a major data migration (destructive schema change, live-table
backfill, or data relocation), or a runtime infrastructure change. Also run when
the user explicitly requests readiness or `.m/pipeline.yml` has
`readiness.required: true`. A mention of deployment in documentation or an edit
to the workflow skills themselves is not a runtime infrastructure change.

Ordinary implementation retains the five core phases without this extra gate.
`readiness.required: false` or an absent setting does not suppress the release
triggers above. Explicit user scope takes precedence; if the user excludes the
assessment, report readiness as not assessed and do not claim release approval.

A standalone invocation assesses the supplied release without forcing an
implementation pipeline first. It must not infer a completed review or green CI.

## Scope and permitted work

1. Identify the repository, exact commit or artifact, dirty working-tree changes,
   and target environment. For an uncommitted audit, include a diff fingerprint
   (including relevant untracked files). Never silently switch or clean the tree.
2. Read existing PRD criteria, deployment/IaC configuration, CI results, runbooks,
   incident/recovery records, and `.m/pipeline.yml` when present. Resolve the
   critical user flows, data sensitivity, service objectives, incident owner,
   recovery time objective (RTO), and recovery point objective (RPO) from those
   sources or the user's instructions. The latter is the acceptable data-loss
   window. Do not invent targets to obtain a passing result.
3. State the reviewed environment and exclusions before checking. Use explicit
   invocation arguments over saved defaults. If the deployment's artifact cannot
   be linked to the audited release, mark release identity UNVERIFIED. Evidence
   from staging proves staging behavior; explain the production differences.
4. Inspect files, existing records, CI, and authorized read-only platform APIs.
   Run applicable local checks after inspecting their commands and side effects.
   Honor existing authorization for tests against an isolated test environment.
   An audit request alone does not authorize deployment, production writes,
   restore/failover drills, load against a live service, real payments, or messages
   to other people. Where execution lacks authorization, keep doing independent
   checks and identify the specific evidence or scoped test needed.
5. Do not fix source, configuration, infrastructure, or UI during the audit. Do
   not install packages or upload source to an external audit service as a default
   audit step. Existing authorized tools may be used within their granted scope.

Missing factual evidence produces UNVERIFIED, not a question the user could not
answer better than the available tools. Ask only for unresolved user decisions
that materially affect the required checks. Do not repeat settled permissions.

## Evidence pass

Inventory the release once, then evaluate each applicable area. Reuse prior
review findings and test results only when their release, environment, relevant
configuration, and age make them applicable. A fix, configuration change, or new
artifact invalidates affected results and their downstream checks.

For each check record: requirement, required/advisory, status, evidence kind
(source, configuration, CI, runtime, or recovery exercise), exact location or
command/result, commit/artifact, environment, and observation time. Record the
missing evidence and next verification action for UNVERIFIED checks.

When a control is not found, name the paths/configuration searched, search terms,
and result. Zero matches mean "not found in reviewed scope". They prove neither
absence nor presence of a provider-managed control. Even if some IaC is present,
confirm that it owns that control before judging its absence. A backup setting
does not demonstrate a successful restore; a test file does not prove execution.

## Required checks

Make checks required when they apply to this release's behavior and risk. An
existing launch-blocking defect still blocks release even if it predates the
current change. Separate CURRENT and PRE-EXISTING ownership without lowering the
verdict. Do not invent enterprise controls for a small product.

| Area | Evidence needed when applicable |
| --- | --- |
| Release identity and build | Audited commit/artifact and target match; relevant CI/build/tests ran successfully on that version; production configuration and required environment variables are validated. |
| Critical journeys | Executed success and failure paths for the named user flows; server-side authorization and cross-user/tenant denial; payment/webhook signature, duplicate and out-of-order handling; essential background jobs. |
| Deployment and data | Migration/backfill compatibility with old and new application versions; tested rollout/rollback or recovery route; startup, traffic readiness, and graceful shutdown behavior. |
| Recovery | Backup/PITR coverage and retention where persistent data matters; a successful isolated restore with measured recovery time and recoverable data point assessed against agreed RTO/RPO. |
| Operations | Service objectives and relevant metrics; alert delivery to the responsible responder demonstrated; incident owner and actionable runbooks; sensitive data excluded from logs. |
| Capacity and cost | Representative load against agreed latency/error limits; timeouts, bounded retries, idempotency, queue limits/backpressure, and applicable API/LLM spend controls. |
| Existing blockers | Review/security findings and PRD success criteria reconciled; required fixes rechecked; no unresolved credible critical issue. |

Decompose areas into checkable requirements; one passing subcheck does not clear
an entire area. Missing objectives for an applicable required check leave that
check UNVERIFIED. Mark irrelevant checks N/A with a concrete reason (for example,
payment processing in an application with no payments). Libraries and packaging
reviews use the explicitly requested release surface and explain which service
checks do not apply. An undefined target or an all-N/A assessment cannot be READY.

Use provider-specific official guidance for the actual deployment platform.
Source/configuration checks can PASS on inspected source/configuration; runtime
or recovery requirements need execution evidence of the corresponding behavior.

## Status and verdict

- `PASS`: the requirement is met by appropriate, applicable evidence.
- `FAIL`: evidence demonstrates the requirement is not met.
- `UNVERIFIED`: evidence, environment access, execution, identity, or the target
  criterion is missing or stale. It is neither a proven vulnerability nor a pass.
- `N/A`: the requirement does not apply, with a verified scope reason. Missing
  access, a failed check, or an unwanted result is not a reason for N/A.

Return `READY` only when release identity is established, every required check
is PASS or justified N/A, and no unresolved critical/high release blocker remains.
Any required FAIL or UNVERIFIED produces `BLOCKED`. Advisory gaps do not block;
explain why each advisory item is outside the release's required criteria.

An explicit user waiver records accepted risk, but does not change a check's
status, turn this gate READY, or advance an active `/m:develop` past the gate.
Return BLOCKED to the orchestrator for cleanup, recording the accepted risk,
scope, owner, and any expiry supplied by the user. Any separately authorized
rollout is outside this assessment and must retain the recorded BLOCKED verdict.
Do not reclassify required failures as advisory to clear the gate. A READY
verdict is an assessment of the named release and environment, not authorization
to deploy.

## Output and handoff

Report in chat by default: target release/environment, READY or BLOCKED, the
check table, release blockers, scope/evidence limits, and concrete next actions.
Name repository-only versus runtime evidence explicitly. Do not create dedicated
reports, dashboards, or explanatory files unless the user requests them.

Within `/m:develop`, preserve its permitted phase bookkeeping and record the
verdict and open gaps in existing `.m/PROGRESS.md` and `.m/GAPS.md`. Honor chat-only
or no-write instructions over persistence; do not create completion markers when
the corresponding phase was not completed. A standalone audit creates no `.m/`
state by default.

Hand fixes back to the appropriate `/m:plan` or `/m:implement` stage, followed by
review and iterate, within the user's authorization. Reassess the resulting
release before clearing this gate. Do not start an unbounded fix/audit loop or
declare readiness because an iteration or token limit was reached.
