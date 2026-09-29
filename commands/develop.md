---
description: Run the full /seamark delivery pipeline end-to-end (refine → plan → implement → review → verify), followed by readiness for releases and operational changes. Use when user wants a complete request delivered with quality gates, dual-engine review, and phase enforcement.
argument-hint: [request]
model: claude-opus-5-5
effort: high
disable-model-invocation: true
---
# /seamark:develop - End-to-End Delivery Workflow

Run the full `/seamark:*` pipeline for the current request.

## Invocation Protocol (HARD GATE — read before doing anything else)

Every phase in this pipeline runs as a discrete Skill tool call. You may not
inline a phase's output into chat under any circumstances. If you catch
yourself about to emit a refined spec, an implementation plan, an
implementation narrative, a review report, or an verify verdict without a
prior Skill call for that phase, stop immediately, delete the draft, and
invoke the skill.

The harness enforces this via a marker-file protocol that a PreToolUse hook
validates on every Edit, Write, and MultiEdit, and on every Bash command
that writes outside `.seamark/`. Skipping a skill now causes file mutations to be
blocked until the skill is invoked.

### Marker files

- `.seamark/DEVELOP_ACTIVE` — single-line marker written at pipeline entry,
  deleted at pipeline exit. Contents:
  ```
  current_phase: <refine|plan|implement|review|verify|readiness>
  ```
- `.seamark/phase-<name>-started` — created by each phase skill on entry.
- `.seamark/phase-<name>-done` — created by each phase skill on successful exit.

### Pipeline entry

Immediately after the user invokes `/seamark:develop`, before anything else:

1. Ensure `.seamark/` exists (`mkdir -p .seamark`).
2. Write `.seamark/DEVELOP_ACTIVE` with `current_phase: refine`.
3. Remove any stale `.seamark/phase-*-started` / `.seamark/phase-*-done` markers from
   a prior pipeline run.

### Phase transitions

Before moving from phase A to phase B:

1. Verify `.seamark/phase-<A>-done` exists. If missing, re-enter phase A via its
   skill only when missing execution or bookkeeping can be repaired — do NOT proceed. If phase A returned a provisional draft or a blocking user-intent question, surface that question and end this run through pipeline cleanup; do not re-enter it repeatedly without new input. Every repair re-entry appends one JSON line to
   `~/.claude/seamark-learning/signals/pipeline-events.jsonl` with the file tools,
   never a Bash `echo`:
   ```json
   {"timestamp":"<ISO-8601 UTC>","type":"phase_reentry","project":"<repo dir basename>","phase":"<A>","reason":"missing_done_marker"}
   ```
   A phase that has to be re-run is evidence that the phase before it
   under-specified the work, which is why the re-entry is recorded rather
   than silently retried. Signal writing is non-blocking: a failed append
   never blocks the re-entry and is reported as one line in chat. The file
   is global and concurrent sessions append to it, so write the record as
   one complete line in a single append and never rewrite existing lines.
2. Overwrite `.seamark/DEVELOP_ACTIVE` with `current_phase: <B>`.
3. Invoke `Skill(skill="seamark:<B>")` as the first action of phase B.

At each handoff, pass the original requested outcome and constraints, the previous phase's output or artifact path, its readiness status, and the decision sources (explicit requirements, delegations, and unresolved questions) in the Skill arguments. A generated spec is not automatically user-approved. A completion marker cannot override a provisional or BLOCKED handoff.

The request to deliver authorizes continuing through settled phases. Do not add confirmation stops between them unless the user requested an approval checkpoint or a new decision falls outside the existing authorization.

### Pipeline exit

On every terminal path (success, hard-block, abort, user interrupt):

1. Delete `.seamark/DEVELOP_ACTIVE`.
2. Leave the `phase-*-started` and `phase-*-done` markers in place so they
   are auditable; they will be cleaned up on the next pipeline entry.

### Hook blocking behavior

When `.seamark/DEVELOP_ACTIVE` is present and the current phase has not been
entered via its skill, any Edit/Write/MultiEdit outside `.seamark/` is denied by
the `enforce-develop-phase.py` PreToolUse hook. Writes under `.seamark/` are
always allowed so the protocol itself can run.

## Stage Order

The pipeline runs these stages in sequence. Each stage produces input the next stage depends on, which is what keeps the pipeline cheap:

```
index (if needed) → refine → plan → classify → implement → review → verify → readiness (when required) → update → learn (if threshold crossed)
```

**Refine runs first.** Invoke `/seamark:refine` via the Skill tool before any other work. Refine surfaces the assumptions that plan and implement would otherwise guess at, so its output is what makes the downstream stages cheap.

**Plan runs after refine.** Invoke `/seamark:plan` via the Skill tool once refine completes. Plan grounds implementation in user-confirmed decisions, which is what prevents impl-time improvisation.

**Readiness follows verification when required.** Read
`${CLAUDE_PLUGIN_ROOT}/references/readiness.md` to determine whether the requested release,
major data migration, or runtime infrastructure change requires this gate. Also
run it when `.seamark/pipeline.yml` sets `readiness.required: true`. Determine applicability
during planning and preserve it in the handoff. The five core phases remain
mandatory for every size; readiness adds a release assessment, not deployment.

**Checkpoint line.** Before each stage transition, emit a line confirming the previous stage ran:
`[checkpoint] {stage_name} complete — output: {key artifact or verdict}`
If the line cannot be written because the stage produced no output, pause and run the missing stage before moving on.

## Input

Request to deliver: `$ARGUMENTS`

## Context Sources

Read these when available (reading context does NOT replace running refine/plan):

- `.seamark/INDEX.md`
- `.seamark/TASKS.md`
- `.seamark/PROGRESS.md`
- `.seamark/GAPS.md`
- `.seamark/RESEARCH.md`
- `PROJECT_INDEX.md`
- repo-local guidance such as `AGENTS.md` and `CLAUDE.md`

## Workflow

0. **INDEX (if needed)** — If `.seamark/` is missing any core index file or is clearly stale, run `/seamark:index` first via the Skill tool. This runs before pipeline entry so the index exists before any phase marker or `.seamark/DEVELOP_ACTIVE` is written.
1. **ENTER PIPELINE** — follow the Invocation Protocol entry steps: create `.seamark/`, write `.seamark/DEVELOP_ACTIVE` with `current_phase: refine`, remove stale `phase-*` markers.
2. **REFINE** — Invoke `Skill(skill="seamark:refine")`. This is the grill stage. Skipping it silently collapses the spec to a lowest-common-denominator version. Wait for the skill to complete and write `.seamark/phase-refine-done` before proceeding. Do not emit any refined spec content inline.
3. **PLAN** — Before invoking, verify `.seamark/phase-refine-done` exists. Update `.seamark/DEVELOP_ACTIVE` to `current_phase: plan`. Invoke `Skill(skill="seamark:plan")` immediately. Do not prompt the user between refine and plan. Do not emit any plan content inline. Plan may BLOCK and spawn worktree-isolated `/seamark:research` when it encounters unknowns.
4. Classify the side-effect tier: `read-only`, `write-local`, or `write-external`.
5. **IMPLEMENT** — Verify `.seamark/phase-plan-done` exists. Update `.seamark/DEVELOP_ACTIVE` to `current_phase: implement`. Invoke `Skill(skill="seamark:implement")`. All code mutation happens inside this skill.
6. **REVIEW** — Verify `.seamark/phase-implement-done` exists. Update `.seamark/DEVELOP_ACTIVE` to `current_phase: review`. Invoke the appropriate review skill (see Review Selection below) via the Skill tool. The second engine runs in-stage on every review when `second_engine.provider` is `codex` or `kimi`.
7. **VERIFY** — Verify `.seamark/phase-review-done` exists. Update `.seamark/DEVELOP_ACTIVE` to `current_phase: verify`. Invoke `Skill(skill="seamark:verify")`. Run until the **exit predicate** is satisfied (tests green + zero critical review findings + `.seamark/PROGRESS.md` updated + PRD Success Criteria satisfied when a `.seamark/PRD-*.md` exists) or the 3-loop safety cap is reached. `PASSED` requires the predicate, not just the cap.
8. **READINESS (when required)** — Only after verify returns PASSED, verify
   `.seamark/phase-verify-done`, set `current_phase: readiness`, and invoke
   `Skill(skill="seamark:readiness")` with the release, environment, and prior evidence.
   Apply the shared readiness contract. A required BLOCKED assessment makes the
   delivery BLOCKED; a green verify result cannot override it. Continue to exit
   cleanup on either outcome. When not applicable, state the reason and do not
   create a readiness completion marker. If the user explicitly excludes this
   assessment, report readiness as not assessed without claiming release approval.
9. **EXIT PIPELINE** — Delete `.seamark/DEVELOP_ACTIVE`. Update `.seamark/TASKS.md`, `.seamark/PROGRESS.md`, and `.seamark/GAPS.md` with the outcome. Then append one outcome signal to `~/.claude/seamark-learning/signals/outcomes.jsonl` (create the file if absent) so `/seamark:learn` can derive adaptations — a single JSON line of the form `{"timestamp":"<ISO-8601>","type":"outcome","skill":"develop","project":"<repo dir basename>","request":"<one-line summary>","stages":"<actual stages, including readiness when run>","verdict":"<PASSED|BLOCKED>","loops":<n>,"second_engine":"<codex:agree|codex:disagree|kimi:agree|kimi:disagree|n/a>"}` (use the `timestamp` key to match the existing signal schema; `project` is the repository directory basename, the same value the `phase_reentry` record uses. Note that `outcome` records are not matched by any row of `/seamark:learn`'s behavioral mapping table, which keys only on the five pipeline event types; they are read by its step 3 pattern detection, where `project` is what allows an outcome to be attributed to a project at all). Append with the file tools, not `echo`. This is passive telemetry and is separate from the opt-in `/seamark:feedback` signals.

   Finally, still within this step and only after `.seamark/DEVELOP_ACTIVE` has been deleted, consider a scoring run. Count the non-empty lines across every `.jsonl` file in `~/.claude/seamark-learning/signals/`, read the `Signals scored: <N>` value from the header line of `~/.claude/seamark-learning/ADAPTATIONS.md`, and invoke `Skill(skill="seamark:learn")` when the current total exceeds that stored value by **10 or more**.

   Treat the stored value as **unset** in two cases: when `ADAPTATIONS.md` is absent or carries no parseable `Signals scored:` value, and when the stored value is *greater than* the current total. When it is unset, fire if the current total is itself 10 or more. Both cases are real and neither is an error. The first is a fresh install, where nothing has ever written a count — without this clause the trigger could never fire at all, because only `/seamark:learn` writes the count and only this trigger invokes `/seamark:learn`. The second follows from `/seamark:feedback reset`, which empties the signal files without touching `ADAPTATIONS.md`, leaving a stored count larger than the corpus; without this clause the difference stays permanently negative and the trigger is dead for good while the stale adaptations keep being applied.

   Ordering. Keep the invocation after the marker deletion, but for the right reason. On the success path the write would be permitted regardless, because the verify phase's `-started` marker is present and `enforce-develop-phase.py` allows a write once the active phase has been entered. The hazard is the terminal paths where the phase was never entered — abort and user interrupt. There the hook denies the `ADAPTATIONS.md` write and records a `gate_denial` naming that phase, so a scoring run launched too early would manufacture exactly the kind of evidence `/seamark:learn` is about to score.

   The trigger fires on **every terminal path** — success, hard-block, abort, and user interrupt — matching how the outcome record above is already written. There is no per-verdict special case; a `BLOCKED` run is where phase re-entries and repeated verify loops cluster, which is the evidence the mapping rows most want.

   `ADAPTATIONS.md` is rewritten whole by `/seamark:learn` rather than appended to, and it is global across every repository. If another `/seamark:*` session may be scoring concurrently, skip the trigger rather than race it — a skipped run costs nothing, because the next run's threshold check catches up. A `/seamark:learn` run that fails or blocks never changes the delivery verdict and is reported as a single line in chat, matching the non-blocking convention every other signal write in this pipeline follows.

   Coverage bound, stated so it is not inferred: this command carries `disable-model-invocation: true`, so it runs only when the user types `/seamark:develop`. Standalone `/seamark:review`, `/seamark:implement`, and `/seamark:verify` runs write signals but never reach this step, and so never fire the trigger.

Emit a stage transition line between each step:
`[pipeline] {stage_name} → {next_stage_name} ({reason or key outcome})`

For the review stage, the transition line must also state which review variant ran and whether a second engine was invoked:
`[pipeline] implement → review-fanout ({N} lenses) → verify (second opinion — codex: agree)`

## Review Selection

Pick the review command based on the change shape, not by default:

| Change shape | Command |
|---|---|
| 1–3 files, single lane, <100 lines changed | `/seamark:review` |
| 4–10 files OR touches 2+ layers (handler → service → repo) | `/seamark:review-fanout` |
| Go backend with security-sensitive code paths | `/seamark:review` (delegates security pass to `go-security-reviewer`) OR `/seamark:review-fanout` with the security + architecture lenses |
| Cross-stack change (Go + React + infra) | `/seamark:review-fanout` |
| Repo whose `.seamark/pipeline.yml` sets `compliance.enabled: true` | whichever command is already running **plus** the compliance pass |

Compliance and high-stakes triggers are read from the repo's `.seamark/pipeline.yml` (schema: `${CLAUDE_PLUGIN_ROOT}/references/pipeline-context.md`). If the file is absent, compliance is off and only the generic high-stakes categories in the next section apply.

## Second Engine (mandatory when a provider is selected)

Second-engine participation across the pipeline (plan, research, review) is driven by the `second_engine:` section of the repo's `.seamark/pipeline.yml` (schema, provider defaults, and the legacy `codex:` fallback: `${CLAUDE_PLUGIN_ROOT}/references/pipeline-context.md`; `provider: none` is the default — Claude-only).

When the provider is `codex` or `kimi`, the review stage runs the second engine automatically on **every** review — there is no `y/n` prompt and no high-stakes gating. Follow the active provider's protocol Section 12 (`${CLAUDE_PLUGIN_ROOT}/references/codex-protocol.md` or `${CLAUDE_PLUGIN_ROOT}/references/kimi-protocol.md`):

1. After the review stage produces its verdict, run the Metered Invocation against the change set (Codex: native `codex exec review` with `--uncommitted`, `--base <branch>`, or `--commit <SHA>`; Kimi: the prompt-constructed review over the same target).
2. Present Claude's findings and the second engine's findings **side-by-side**. Do not merge silently. Second-engine findings are leads to confirm, never ground truth.
3. **Disagreement rule:** if Claude says `APPROVED` but the second engine flags criticals that survive re-verification, downgrade to `BLOCKED`. The more permissive verdict never wins by default.
4. The second engine is skipped (noted in metadata, never a pipeline failure) only when the provider is `none`, the CLI is unavailable, or the per-run token budget is reached (per `on_budget_exceeded`).

The high-stakes categories below still escalate Claude's own pass depth, size tier, and compliance pass; they do not gate the second engine.

## Size Selection

- **Small** (1–3 files, unambiguous scope): `refine → plan → implement → review → verify`. Use `/seamark:review`.
- **Medium** (4–10 files OR multi-layer): `refine → plan → implement → review → verify`. Use `/seamark:review-fanout` instead of `/seamark:review` if the change crosses 2+ layers.
- **Large or security-sensitive** (10+ files, migrations, auth/money, `high_stakes_paths` matches, API contracts): `refine → plan (with worktree research as needed) → implement → review-fanout (second engine runs in-stage when a provider is selected) → verify`.

Every size runs the full pipeline: refine → plan → implement → review → verify. No stage is optional. No skips. No "trivial enough" bypass. You must invoke `/seamark:refine` and `/seamark:plan` as Skill tool calls — not inline them, not summarize them, not skip them. Refine auto-chains to plan in all sizes. Plan handles research internally via BLOCK + worktree spawn when it encounters unknowns.

## Side-Effect Tiers

Inherit the tier from `/seamark:implement`. The tier gates how the pipeline proceeds:

- **read-only**: skip confirmation, run full pipeline automatically
- **write-local**: proceed after initial scope confirmation, no per-step gates
- **write-external** (migrations, API contracts, shared config): pause before implement and before any destructive step — confirm with user explicitly

## Rules

- Apply `${CLAUDE_PLUGIN_ROOT}/rules/rigor.md` at every stage. No shortcuts (no skipped phases, no inlined skill output, no `--no-verify` gates), full tool use (Read every cited file, run tests instead of predicting them, MCP for external state, parallel independent tool calls), and no compression of reasoning or verification work to save tokens. Simplified Technical English applies only to chat output, never to the work itself
- Apply `${CLAUDE_PLUGIN_ROOT}/rules/self-serve.md` at every stage. Before any user-facing question, resolve factual residues via Read, Grep, Glob, Bash, or MCP. Only `[USER-INTENT]` questions (scope, tradeoffs, business rules, preferences) reach the user. Every user-facing question is prefixed `[USER-INTENT]`.
- Treat critical or high-risk review and verification issues as gates, not soft suggestions
- `/seamark:verify` may only emit `PASSED` when its four-clause exit predicate is green. A loop-count exit is `BLOCKED`, not `PASSED`
- Delivery PASSED requires a successful verify and READY from readiness when
  that gate is required. No required FAIL or UNVERIFIED readiness check may be
  bypassed by the verify verdict, a numerical score, or a completion marker.
- The second engine runs automatically on plan, research, and review when `second_engine.provider` is `codex` or `kimi`; it is config-driven, not prompted. The default is `none` (Claude-only)
- When Claude's judge and the second engine disagree, the stricter verdict wins
- Do not auto-create worktrees
- Do not redesign UI unless the user explicitly asks
- Keep CURRENT issues separate from PRE-EXISTING gaps
- If the repo is an extracted snapshot, vendor dump, or is missing build/test metadata, call out the verification limits explicitly
- Apply `${CLAUDE_PLUGIN_ROOT}/rules/verification.md` at every stage. Self-challenge every finding before emitting it

## Output

Finish with:

## Delivery Summary

### Request
### Pipeline Stages Run
List the stages actually run, in order, with the specific review variant and whether Codex was invoked.
Example: `refine → plan → implement → review-fanout (7 lenses) → codex second-opinion (agree) → verify (2 loops, PASSED)`
### Scope
### Checks Run
### Exit Predicate Status
- Tests green: yes / no — {command and exit code}
- Zero critical review findings: yes / no / n/a
- PROGRESS.md updated: yes / no
- PRD Success Criteria satisfied: yes / no / n/a
- Release readiness: READY / BLOCKED / not applicable / explicitly not assessed
  — include the assessed commit/artifact, environment, and required unmet checks
### Remaining Blockers
### Next Step
