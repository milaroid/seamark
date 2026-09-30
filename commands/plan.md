---
description: Create an actionable implementation plan grounded in repo patterns and user-confirmed decisions. Uses second-engine (Codex or Kimi, config-driven) sanity passes and a grill loop until zero gaps. Use after /seamark:refine or when starting a non-trivial change.
argument-hint: [refined-request]
model: claude-sonnet-5-5
effort: high
allowed-tools: Read, Grep, Glob, Agent, Bash(git:*), Bash(codex exec:*), Bash(codex --version), Bash(kimi -p:*), Bash(kimi --version), Bash(mkdir:*), Bash(rm -f .seamark/handoff/:*), Bash(rm -rf .seamark/handoff/:*)
---
# /seamark:plan - Master Planner

Create a detailed, actionable implementation plan through rigorous gap analysis and user-confirmed decisions. The plan stage is the primary value producer in the pipeline.

## Core Constraint: Trace Every Plan Element to Its Authority

**Every plan element must stay within the user's requested outcome and carry an honest decision source.** Explicit user choices and settled requirements are authoritative. A generated PRD is a handoff, not evidence that the user approved every sentence in it.

- Read the input's status and unresolved questions before planning. A `PROVISIONAL` spec or an unanswered product choice stays unresolved even if its draft contains a concrete assumed value. Do not relabel it `[CONFIRMED-BY-SPEC]`.
- Resolve facts and routine implementation details from inspected code within the requested scope. These are `[DERIVED]` choices, not new product requirements.
- When the user explicitly delegates a choice ("choose the approach", "use your judgment"), decide within that delegation and label it `[DELEGATED]`. Record the user's delegation, the selected option, its reason, and its limits. Silence, unavailable input, and an assistant-authored assumption are not delegation.
- When no intended outcome is supplied but scope selection is explicitly delegated, choose a bounded outcome from the evidence and state it. Broad delegation does not authorize unrelated product changes, destructive operations, or external actions.
- A material product, security, data-retention, or scope decision outside the request and delegation → BLOCK and ask a bounded question. Keep it out of executable tasks until settled.

When an unresolved decision blocks the requested outcome, name it and BLOCK. Continue independent analysis, but do not invent confirmation to clear the gate.

## Input

Refined prompt or task description: `$ARGUMENTS`

## Jira Context (run before Phase 1)

If `$ARGUMENTS` contains a Jira reference, resolve and fetch it per `${CLAUDE_PLUGIN_ROOT}/references/jira-context.md` **before** codebase analysis. Ground acceptance criteria in the Jira acceptance criteria; if the story is thin, call that out under **Risks or Open Items**.

## Context Sources

Read these first when available:

- `.seamark/jira.yml` (per-project Jira mapping)
- `.seamark/INDEX.md`
- `.seamark/GAPS.md`
- `.seamark/RESEARCH.md`
- `PROJECT_INDEX.md`
- repo-local guidance such as `AGENTS.md` and `CLAUDE.md`
- `~/.claude/seamark-learning/ADAPTATIONS.md` (if present) — apply the HIGH and MEDIUM `plan` adaptations, pipeline defaults, and the `plan_depth` preference recorded there; proceed normally if it does not exist. Current-session instructions always override a learned adaptation.

Prefer inspected repo patterns for routine details within the approved scope. Ask only when applying a pattern would decide an unresolved user-intent question or contradict the request.

## Workflow

### Phase Marker Protocol

This skill participates in the `/seamark:develop` phase gate. Follow this
protocol on every invocation, including standalone runs:

1. On entry, before any codebase analysis or second-engine pre-flight: run
   `mkdir -p .seamark && touch .seamark/phase-plan-started` via Bash.
2. On successful completion (plan emitted, exit gate passed): run
   `touch .seamark/phase-plan-done`.
3. On BLOCK (for gaps, research spawn, or hard-block disagreement): leave
   `-started` in place and do NOT write `-done` until the plan is
   eventually emitted.

If `.seamark/DEVELOP_ACTIVE` is present and its `current_phase:` line does not
read `plan`, stop and tell the user — the pipeline is out of sync.

### Phase 1: Codebase Analysis

#### Pre-flight: Second-Engine Check

Before any observation work, resolve `second_engine` from `.seamark/pipeline.yml` (schema, provider defaults, and legacy `codex:` fallback in `${CLAUDE_PLUGIN_ROOT}/references/pipeline-context.md`) and run the pre-flight check in the active provider's protocol Section 2 — `${CLAUDE_PLUGIN_ROOT}/references/codex-protocol.md` for `codex`, `${CLAUDE_PLUGIN_ROOT}/references/kimi-protocol.md` for `kimi`. When a provider is selected, Pass-1 and Pass-2 are **mandatory** — there is no per-pass permission prompt. The passes are skipped (the plan proceeds Claude-only) only when the provider is `none`, the CLI is unavailable, or the per-run token budget is reached.

The Metered Invocation (Section 6), Operating-Rules Preamble (Section 4), Secret Redaction Rule (Section 5), and Token Metering (Section 7) of the active provider's protocol apply to every Pass-1 and Pass-2 handoff. Do not duplicate those rules here — read the reference and apply them verbatim.

#### Observation Gathering

Explore the codebase — read the request, map relevant code paths, classify repo health, identify existing patterns. When the codebase map would span more than three searches, spawn `Explore` subagent(s) (`model: haiku`) for the breadth sweep; keep the synthesis, grilling, and the worktree `/seamark:research` spawn on the orchestrator's own model.

Present all findings as `[OBSERVATION]`:

```
[OBSERVATION] Repository uses repository pattern for DB access (see pkg/repository/)
[OBSERVATION] Auth middleware at pkg/middleware/auth.go uses JWT with tenant isolation
[OBSERVATION] No existing test helpers for integration tests
```

Observations are input for planning. They become tasks only through an explicit requirement, a bounded delegation, or a derived implementation detail within that authority.

#### Pass-1: Second-Engine Architecture Sanity (blocking)

Runs after observation gathering completes, before Phase 2 begins. Phase 2 must not start until Pass-1 completes or is skipped. Follow the active provider's protocol Section 8 for the full protocol — payload build, redaction, metered invocation, merge of `[OBSERVATION — codex]` / `[OBSERVATION — kimi]` entries.

### Phase 2: Grill-Based Plan Construction

Build the plan iteratively through user-confirmed decisions. This phase loops until all gaps are resolved.

**For each plan area** (architecture, file changes, data model, security, testing, error handling, implementation order):

1. Identify explicit requirements, delegated choices, derived details, and unresolved user-intent decisions.
2. Resolve facts with tools and make choices within explicit delegation. Batch only the remaining blocking decisions as gaps.
3. If gaps remain, present them as bounded-menu questions:

```
BLOCKED — {N} gaps require your input

An unconfirmed item cannot become a plan element. Each gap below stays out
of the plan until you settle it; nothing here is decided by assumption.

Q1. {short question about gap}
  A) {concrete option with its tradeoff}
  B) {concrete option with its tradeoff}
  C) {concrete option with its tradeoff}
  D) Other — describe

Q2. {next gap}
  ...
```

State the principle in the BLOCK, not only in your reasoning. The requester
has to see that the gap list is the plan's boundary, not a formality.

4. Wait for user answers
5. If answers create new gaps → new grill round. Loop until zero gaps. **Soft round cap:** there is no hard limit, but if the grill reaches round 4 and answers are still spawning fresh gaps, pause and surface a convergence check — show the user the still-open gaps and ask whether to keep grilling or to move the remainder to DEFERRED (under Risks) and proceed. This guards against a gap-spawns-gap loop without forcing premature closure; the user, not a counter, decides when to stop.

**Complete-input fast path.** When explicit requirements, bounded delegation, and derived implementation details settle the plan, emit it directly. Do not ask for another confirmation round merely because the requester is available. A provisional draft with unresolved user intent does not qualify; either resolve those choices within an actual delegation or BLOCK.
6. When user confirms a section:
   - Mark items as `[CONFIRMED]`
   - Record a draft task in the plan document's `### Tasks` section: high-level title + checklist sub-items. The task tools are not the record: Claude Code offers `TaskCreate` only on Claude 3.x, Opus 4.0 to 4.7, Sonnet 4.0 to 4.6, and Haiku 4.5 unless `CLAUDE_CODE_ENABLE_TODO_TOOLS=1` is set, so on this command's model the tool is absent
   - Each task entry must carry its acceptance criteria

**Labeling protocol:**
- `[OBSERVATION]` — codebase finding, not a decision
- `[PROPOSED]` — Claude's suggestion, needs user confirmation before becoming plan
- `[CONFIRMED]` — user confirmed, now a plan element. Include which grill round confirmed it.
- `[CONFIRMED-BY-SPEC]` — settled by an explicit requirement in the user's request or approved spec. Cite that requirement; never use this label for an assistant's provisional assumption.
- `[DELEGATED]` — chosen within the user's explicit delegation. Cite the delegation and explain the choice and scope boundary.
- `[DERIVED]` — a routine implementation detail needed to satisfy an authorized requirement. Cite the requirement and inspected code or constraint that determines the detail. This label cannot create new scope or settle an unresolved product decision.

**Anti-assumption enforcement:**
- When presenting a `[PROPOSED]` item, always include your reasoning AND the strongest counter-argument
- If a plan element has none of these decision sources, keep it `[PROPOSED]` and ask before making it an implementation task.
- "The codebase already does X" is evidence for a derived detail, not proof the user requested X as new scope.

**Research trigger:** If you encounter an unknown requiring external research (unfamiliar library, protocol, integration point), BLOCK and spawn isolated research. The trigger fires on the unknown itself, independent of repository state: an unfamiliar third-party library is a research trigger whether the repo is fully populated, empty, or missing the subsystem the change targets. Do not substitute a repo-state BLOCK for the research spawn — report both when both apply:

```
BLOCKED — need research on [topic]. Spawning isolated worktree research.
```

Spawn via `Agent(isolation: "worktree")` with ONLY the research question and relevant file paths. Do NOT include the refined spec, plan-so-far, or any conversation context in the agent prompt. Present research findings to user. User decides what to incorporate — research is advisory, the plan (user's plan) wins.

### Phase 3: Exit Gate

Before emitting the final plan, verify ALL of the following:

1. **Every task has acceptance criteria** — specific, testable, complete
2. **Zero impl-time decisions** — no task requires the implementer to choose an approach, pick a pattern, or decide on error handling. The metric is decision count, not file count. A 3-file change with zero ambiguity passes. A 1-file change with "pick auth strategy" fails.
3. **All gaps resolved** — or user said "enough" (remaining gaps become DEFERRED items under Risks)

If any check fails:
- Identify failing items
- Convert to new grill round questions
- Loop back to Phase 2

If all checks pass, run Pass-2 (below) before emitting the plan document.

**Task splitting rule:** Before finalizing, check every task against the zero-decisions constraint. If a task requires the implementer to make any design decision, split it or escalate the missing decision as a new gap.

#### Pass-2: Second-Engine Final Plan Review (blocking)

Runs after the three exit-gate checks pass, before the plan document is emitted. The plan is not emitted until Pass-2 completes or is skipped. Follow the active provider's protocol Section 9 for the full Pass-2 protocol, Section 10 for the Disagreement Menu, Section 7 for token metering and budget enforcement, and Section 13 for the handoff cleanup that runs on every terminal path.

## Output

Produce a slim context document. All actionable content lives in tasks.

## Implementation Plan

### Summary
One paragraph: what we're building, why, and the key decisions that shape the approach.

### Architecture Decisions
For each major decision:
- **Decision**: what was chosen
- **Decision source**: confirmed requirement, spec section, explicit delegation, or derivation from an authorized requirement and inspected code
- **Rationale**: why this approach
- **Alternatives rejected**: what else was evaluated

### Tasks
One entry per task, in dependency order:
- **Title**: what the task delivers
- **Steps**: checklist sub-items (file changes, implementation steps, test strategy, error handling)
- **Acceptance criteria**: specific, testable, complete
- **Decision sources**: the requirements, delegation, and derivations that settle every decision the task encodes

### Risks or Open Items
- Active risks with mitigation
- DEFERRED items (gaps user chose not to resolve now)
- Verification limits (missing tests, build configs, etc.)

All other plan content (file changes, implementation steps, test strategy, error handling) lives in the `### Tasks` section, one entry per task recorded during the grill.

## Persistence

- If `.seamark/PLAN.md` already exists for the current task, update it surgically
- Otherwise keep the plan in chat unless the user explicitly asks to persist it

## Rules

- Apply `${CLAUDE_PLUGIN_ROOT}/rules/rigor.md` for the entire plan run. Evaluate every plan area; use the complete-input fast path when its decision sources suffice, and ask only for remaining blocking decisions. Do not skip the second-engine Pass-1/Pass-2 checks when a provider is selected (they are mandatory, not gated — see the active provider's protocol), or finalize tasks with unconfirmed `[PROPOSED]` elements. Read every cited file, fetch Jira via the `atlassian` MCP rather than inventing acceptance criteria, and prefer `context7` for library questions. Preserve analysis and verification when removing unnecessary round-trips.
- Apply `${CLAUDE_PLUGIN_ROOT}/rules/self-serve.md` to every question the plan emits to the user. Resolve factual questions via Read, Grep, Glob, Bash, or MCP before asking. Only `[USER-INTENT]` residues (scope tradeoffs, business rules, preferences between equally valid options) reach the user. Prefix every user-facing question with `[USER-INTENT]`.

## Self-Check

Before finishing, verify:

- every acceptance criterion from the refined spec is addressed by at least one task
- the plan follows inspected patterns within the authorized scope and identifies any intentional departure
- shared utilities were considered
- restricted files, migrations, contracts, or generated code are flagged
- the implementation order encoded in tasks is dependency-safe
- every task has honest decision sources; provisional assumptions have not been promoted to confirmed requirements

For a standalone plan-only request, deliver the plan and stop; planning does not itself authorize implementation. When implementation was already requested, including an active `/seamark:develop` run, hand the completed plan back to the orchestrator without asking for permission again. Preserve any explicit user-requested approval checkpoint.
