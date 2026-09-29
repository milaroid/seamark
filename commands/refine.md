---
description: Turn a raw request into an execution-ready PRD via active grilling. Use when user says "ask questions", "examine", "challenge this", "what am I missing", "stress test", "let's align", or wants a refined spec before planning or implementation.
argument-hint: [request]
model: claude-opus-5-5
effort: high
---
# /m:refine - Request Refinement (Grill Stage)

Turn a raw request into an implementation-ready specification by **actively grilling** the request — not defensively checking it. This is the highest-leverage stage in the pipeline: a weak refine silently collapses plans to the lowest-common-denominator solution, and a strong one makes every downstream stage cheaper.

Surface ambiguity proactively, resolve facts with tools, and ask for decisions that remain outside the supplied requirements or delegation. Preserve settled choices across stages instead of reopening them as confirmation questions.

## Input

Raw request: `$ARGUMENTS`

## Jira Context (run before workflow phases)

If `$ARGUMENTS` contains a Jira reference, resolve and fetch it per `${CLAUDE_PLUGIN_ROOT}/references/jira-context.md` **before any workflow phase, including the Phase 0 reframe** — detection, fetch via the `atlassian` MCP, unauthenticated behavior, the **Jira Context** block, and conflict surfacing are all defined there.

## Context Sources

Read these first when available:

- `.m/jira.yml` (per-project Jira mapping)
- `.m/INDEX.md`
- `.m/GAPS.md`
- `.m/RESEARCH.md`
- `PROJECT_INDEX.md`
- repo-local guidance such as `AGENTS.md` and `CLAUDE.md`
- `~/.claude/m-learning/ADAPTATIONS.md` (if present) — apply the HIGH and MEDIUM `refine` adaptations and code-style preferences recorded there; proceed normally if it does not exist. Current-session instructions always override a learned adaptation.

## Workflow

### Phase Marker Protocol

This skill participates in the `/m:develop` phase gate. Follow this
protocol on every invocation, including standalone runs:

If the user explicitly requests no file writes or chat-only output, skip marker and PRD writes, deliver in chat, and do not claim a persisted phase completion.

1. On entry, immediately after reading context sources: run
   `mkdir -p .m && touch .m/phase-refine-started` via Bash.
2. On successful completion (spec ready, no unresolved user-intent decision): run
   `touch .m/phase-refine-done`.
3. A provisional specification is useful output, but it is not phase completion.
   On abort, hard-block, or unresolved user-intent gap: leave `-started` in place
   and do NOT write `-done`. The pipeline will refuse to advance.

If `.m/DEVELOP_ACTIVE` is present and its `current_phase:` line does not
read `refine`, stop and tell the user — the pipeline is out of sync.

### Phase 0: Optimal-Version Reframe (grill opener)

When the desired end state is missing or ambiguous, ask the requester:

> *"If time and labor were not a consideration, what would the optimal version of this look like? Don't plan — just describe the end state."*

Their answer (or the absence of one) is the anchor for the rest of the refine. The goal is to surface the *real* target before assumptions collapse it. Per community research: default AI planning assumes a solo dev with two jobs and no scaffolds, so the first plan is always smaller than it should be. The optimal-version reframe forces a truer anchor.

When the requester already supplied an explicit end state, use it as the anchor without asking them to restate it. Still inspect the requirements and affected code; skipping a redundant question does not skip analysis.

### Phase 1: Analysis

Classify the request (bug/feature/refactor/review/research/analysis/infrastructure), then analyze:

1. **Hidden requirements** — edge cases, implicit assumptions, things the requester likely forgot
2. **Affected surfaces** — files, modules, APIs, data flows touched by this change
3. **Reuse opportunities** — existing patterns, utilities, shared code that should be leveraged
4. **Security and data impact** — attack surface changes, PII handling, auth implications
5. **Acceptance criteria** — concrete, testable criteria for done
6. **Risks** — what could go wrong or waste implementation time

Reuse known repo context from `.m/INDEX.md` and `.m/GAPS.md`.

### Phase 2: Grill — Bounded-Menu Clarifying Questions

**Self-Serve Gate (run BEFORE drafting any question).** Apply `${CLAUDE_PLUGIN_ROOT}/rules/self-serve.md` to every candidate question:

- `[FACTUAL]` questions (struct fields, table names, file paths, signatures, framework defaults, Jira content, test results, config values, current state) MUST be resolved via Read, Grep, Glob, Bash, or MCP. Move the resolved answer into Technical Context. Do NOT ask the user.
- `[USER-INTENT]` questions (scope tradeoffs, business rules, preferences between equally valid options, deadlines, stakeholder context) become bounded-menu questions below.
- `[MIXED]` questions are split. Tool-resolve the factual half. Ask only the intent residue.

Every question that reaches the user MUST be prefixed `[USER-INTENT]` in the menu. If a question cannot wear the prefix cleanly, it is factual — go resolve it via tools instead.

**Inspect ambiguity on every request.** Ask only the unresolved `[USER-INTENT]` questions that affect the outcome, in batches of at most three. There is no question-count floor. Resolve factual issues with tools and routine implementation details within the authorized scope.

**Complete-input fast path.** When the request is complete and no blocking `[USER-INTENT]` question remains, emit the specification and mark the phase done without a confirmation round. Honor explicit delegation for choices within its bounds and label them as delegated, not user-selected. An unavailable requester is not permission to invent product choices.

1. **Validate file references** against actual repo state.
2. **Emit up to three necessary clarifying questions, each as a bounded menu** of 2–4 selectable options (plus an explicit "none of these / I'll describe it" escape hatch). Format each as:

   ```
   Q{n}. {short question}
     A) {concrete option with its tradeoff}
     B) {concrete option with its tradeoff}
     C) {concrete option with its tradeoff}
     D) Other — describe
   ```

3. **Question only the remaining decision.** Preserve prior answers across stages. Do not ask the requester to approve a restatement of a choice they already made or delegated.
4. **Resolve contradictions.** If a requested choice conflicts with an inspected constraint, explain the consequence. Ask again only if the conflict leaves a material decision unresolved; a clear, feasible user choice takes precedence over a repo preference.

## Rules

- Apply `${CLAUDE_PLUGIN_ROOT}/rules/rigor.md` for the entire refine. Inspect ambiguity, preserve the requested outcome, and verify cited facts. Validate file paths, fetch Jira via the `atlassian` MCP rather than inventing acceptance criteria, and prefer `context7` for library questions. The complete-input fast path removes redundant questions, not analysis or verification.
- Prefer concrete acceptance criteria over generic summaries
- If UI work is involved, preserve the existing design system unless the user explicitly asks for a redesign
- If repo health limits confidence, say so in Assumptions
- Keep the refinement actionable enough to hand directly to `/m:plan` or `/m:implement`

## Output

One observable test decides whether this run emits the specification: **is the
goal determinate?** A goal is determinate when you can write an end state a
reader would recognize as achieved or not achieved. "A logged-in user downloads
the current filtered report as a .csv" is determinate. "The app is faster" is not.
"Fully offline and permanently connected" is not, because no state satisfies both.

**Determinate goal → emit the specification, in the same turn as the grill.**
Every heading below is a REQUIRED slot. Emit each one with content, in this order.
Open questions do not block this. Emit the bounded-menu questions first, then for
each open question record the interpretation you are carrying under
`### Assumptions` with its reason, and write the specification on those
assumptions. Mark it `PROVISIONAL — pending answers to Q1..Qn` in the Goal slot.
Keep the phase incomplete until those user-intent decisions are answered or explicitly delegated. The draft helps the requester answer; it does not authorize planning or implementation against the carried assumptions.
A `[FACTUAL]` slot the repository cannot answer — the file is absent, the stack
is unreadable, the working directory is empty — is likewise an assumption, never a
reason to stop. A provisional specification shows the requester where their
answers lead, which they correct far more cheaply than they recover a
specification that was never written.

**Indeterminate or self-contradictory goal → BLOCK.** Emit the bounded-menu
questions and no specification, not even a provisional one. When the goal itself
has no recognizable end state, or two stated constraints cannot both hold, there
is no coherent thing to write a specification about, and assumptions cannot
manufacture one. Name the conflict or the missing end state, and stop.

The test runs once, on the goal, before you write anything. Open sub-decisions
under a determinate goal are assumptions. An indeterminate goal is a block.

Return:

## Refined Specification

### Goal
### Classification
### Scope
### Out of Scope
### Success Criteria
[Target state expressed as observable conditions, not activities. Read by `/m:iterate` as exit-predicate input, and persisted to `.m/PRD-<slug>.md` under the exact heading `## 8. Success Criteria` (see Persistence) so the iterate gate can verify it. Example: "`go test ./...` exits 0", "user completes checkout without redirect loop", "API returns 401 when token missing". Avoid "improve X" or "make it work".]
### Acceptance Criteria
### Technical Context
### Security or Data Impact
### Test Requirements
### Assumptions
### Recommended Next Command

## Persistence

Persist the refined specification so downstream stages — and `/m:iterate`'s exit predicate — can consume it:

1. Write the full **Refined Specification** to `.m/PRD-<slug>.md`, where `<slug>` is a short kebab-case identifier derived from the goal. Create `.m/` if missing. Use full prose (it is a downstream-consumed artifact); keep the chat output as the human-facing summary.
2. In that file, the success-criteria section MUST use the exact heading `## 8. Success Criteria` (a numbered H2). `/m:iterate` clause 4 scans `.m/PRD-*.md` for that exact heading and gates `PASSED` on every listed condition, so the text must match. Each condition is a target-state predicate (exit code, observable flow, response code, latency bound), not an activity.
3. Persist by default for downstream verification, preserving any `PROVISIONAL` status and unresolved questions. If the user explicitly requests chat-only output or no file writes, honor that request: emit the full spec in chat and do not write PRDs or phase markers. A chat-only request does not satisfy the persisted-artifact gate of an active delivery run; report that constraint instead of silently overriding the user.
