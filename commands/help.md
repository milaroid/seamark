---
description: Show the /m:* workflow reference — pipeline order, stage purposes, side-effect tiers, when to use each command. Use when user asks "what does /m do", "list /m commands", "/m help".
model: claude-haiku-4-5
effort: low
allowed-tools: Read
---
# /m:help

Show a concise reference for the `/m:*` workflow.

State these rules first:

- In Claude Code, `/m:*` should live as slash commands under `.claude/commands/m/`. The pipeline commands remain colon-namespaced slash commands (`/m:refine`, `/m:plan`, …).
- The expert modes live as skills under `.claude/skills/m-*/` and split into two invocation styles:
  - **Manual security skills** — `/m:cr` and `/m:security` carry `disable-model-invocation: true`, so they are user-invoked slash skills (you type `/m:cr` / `/m:security`); Claude does not auto-run them.
  - **Path-activated expert skills** — `m:go`, `m:react`, and `m:biz` carry `user-invocable: false` plus a `paths:` glob list, so they auto-load when Claude edits matching files (`**/*.go`, `go.mod`, `go.work`; `**/*.tsx`, `**/*.jsx`, tailwind config; `.business/**`, `**/BUSINESS.md`). They are hidden from the `/` menu and are not typed as slash commands.
- Do not recommend converting the whole `/m:*` pack into Claude skills unless the user explicitly wants a separate reusable plugin artifact.

Then print:

## `/m:*` - Core Workflow

| Command | Purpose | Use when |
|---------|---------|----------|
| `/m:index` | Build or refresh project memory | Starting work in a repo or refreshing stale context |
| `/m:status` | Show state, tasks, gaps, and worktrees | You want a dashboard or to update tracking |
| `/m:refine` | Cross-examine a request into a complete PRD | The request needs deep exploration, edge cases, alignment |
| `/m:research` | Independent deep research with internet sources | The task is unfamiliar, risky, or integration-heavy |
| `/m:plan` | Produce an implementation plan grounded in repo patterns | The change is medium or large |
| `/m:implement` | Execute a plan or direct request | The scope is clear and coding should begin |
| `/m:review` | Review code or a plan with findings first | You want a gate before merge or implementation |
| `/m:review-fanout` | Parallel-lens review (blind specialists + judge) | The diff is 4+ files or crosses stacks/layers |
| `/m:iterate` | Verify, fix, and re-check | After implementation or review fixes |
| `/m:develop` | Run the end-to-end workflow | You want Claude to orchestrate the whole delivery |
| `/m:analyze` | Deep analysis with optional cached outputs | Architecture, security, flows, docs, proposals |
| `/m:feedback` | Store explicit workflow preferences | The user wants persistent Claude-side learning |
| `/m:readiness` | Assess release, deployment, recovery, monitoring, and capacity evidence | Before launch or after major data migration/runtime infrastructure changes |
| `/m:learn` | Generate or inspect learned adaptations | The user wants to analyze stored signals |
| `/m:setup` | Diagnose and configure the second engine (codex, kimi, or none) | Checking or changing the second-engine provider, CLI, auth, model, effort |

### Expert Modes (installed skills)

User-invoked (type the slash command):

- `/m:cr` — manual security review of changed code, evidence-only, read-only
- `/m:security` — manual OWASP/CWE audit and threat modeling

Auto-activated (load when Claude edits matching files; not slash commands):

- `m:go` — `**/*.go`, `go.mod`, `go.work`
- `m:react` — `**/*.tsx`, `**/*.jsx`, tailwind config
- `m:biz` — `.business/**`, `**/BUSINESS.md`

### Security review routing

Four security surfaces exist; pick by scope:

| Want | Use |
|------|-----|
| Security review of a specific diff / PR / commit (evidence-only, read-only) | `/m:cr` |
| Broad standing-codebase audit, threat model, or OWASP/CWE sweep (not diff-scoped) | `/m:security` |
| Release go/no-go with runtime, rollback, restore, alerts, and capacity evidence | `/m:readiness` |
| Go backend security inside a normal code review | `/m:review` (auto-delegates the security pass to the `go-security-reviewer` agent) |
| Compliance (SOC2 / GDPR / EU AI Act) | `/m:review` or `/m:review-fanout` — the compliance pass fires automatically on repos whose `.m/pipeline.yml` sets `compliance.enabled` |

### Quick Start
```text
/m:index
/m:status
/m:refine Fix the upload auth regression in manager portal
/m:research OAuth 2.0 PKCE flow for mobile apps
/m:plan
/m:implement
/m:review
/m:iterate
/m:develop Harden claim document authorization
/m:analyze overall architecture and style; grade it
/m:readiness HEAD staging
```

### Memory Sources
- Prefer `.m/INDEX.md`, `.m/TASKS.md`, `.m/PROGRESS.md`, `.m/GAPS.md`, `.m/RESEARCH.md`
- Business logic: `.business/BUSINESS.md` and `.business/` specs (PDF, XLSX, DOCX)
- Fall back to `PROJECT_INDEX.md`, `PROJECT_INDEX.json`, `.planning/`, `AGENTS.md`, and `CLAUDE.md`
- Preserve existing user-authored state; update surgically

### Repo Notes
- Repos that already maintain `PROJECT_INDEX.*`, `.planning/`, `AGENTS.md`, or `CLAUDE.md`: treat those as authoritative inputs when bootstrapping `.m/`
- Repos that already have `.m/` state: prefer it and use `PROJECT_INDEX.*` only as supplementary context

### Pipeline discipline

`/m:develop` runs all five phases in order: **refine → plan → implement → review → iterate**. Every size runs the full pipeline. No stage is optional. No skips. No "trivial enough" bypass. The order is not ceremony: refine and plan front-load the assumptions that implement and review would otherwise guess at, which is what keeps the downstream stages cheap. Skipping them does not save work, it moves the work to where it costs more. Each phase is a discrete Skill invocation, and a `PreToolUse` hook (`enforce-develop-phase.py`) blocks file mutations outside `.m/` until the current phase has been entered via its skill. The hook validates `Edit`, `Write`, `MultiEdit`, and any Bash command that writes outside `.m/`. Marker files `.m/phase-<name>-started` and `-done` gate each transition, and `.m/DEVELOP_ACTIVE` records the current phase. The iterate exit predicate (tests green + zero critical findings + progress recorded + PRD criteria met) is the completion gate, not the loop count. `PASSED` requires the predicate; a loop-count exit is `BLOCKED`.

The review variant is selected by change shape, not by preference: 1 to 3 files goes to `/m:review`, 4 or more files or a change crossing layers goes to `/m:review-fanout`. The second engine (Codex or Kimi) is config-driven, not prompted: it runs automatically on plan, research, and review whenever `.m/pipeline.yml` sets `second_engine.provider` to `codex` or `kimi`. The default is `none`, which runs Claude-only. It is not gated on how high-stakes the change looks.

For releases, major data migrations, runtime infrastructure changes, or
`readiness.required: true`, `/m:develop` runs `/m:readiness` after iterate. Claude
and Codex share `${CLAUDE_PLUGIN_ROOT}/references/readiness.md`. Required FAIL or UNVERIFIED
checks block readiness. Standalone readiness reports in chat without creating
`.m/` state; a READY verdict does not deploy or authorize deployment.

### Defaults
- Apply `${CLAUDE_PLUGIN_ROOT}/rules/rigor.md` to every `/m:*` invocation. No shortcuts (skipped phases, paraphrased requirements, `--no-verify` gates), full tool use (Read every cited file, run tests instead of predicting them, prefer `context7` and `atlassian` MCPs over recall, parallel independent calls), no compression of reasoning or verification work to save tokens. Simplified Technical English is an output filter only.
- Do not auto-create worktrees
- Do not redesign UI unless the user explicitly asks
- Do not create `.m/PLAN.md` unless the repo already uses it or the user explicitly asks to persist a plan
- Keep `~/.claude/m-learning/` opt-in; only use `/m:feedback` and `/m:learn` when the user asks
- If the repo looks like an extracted snapshot, vendor dump, or incomplete source tree, say so explicitly before promising build or test validation
- When analyzing or reviewing, separate first-party code from vendor or generated code before grading style or quality
