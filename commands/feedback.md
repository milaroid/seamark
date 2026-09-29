---
description: Store explicit /seamark:* workflow preferences (approve, reject, prefer, style). Use only when the user explicitly wants persistent learning for /seamark:* behavior.
argument-hint: [approve|reject|prefer|style|show|stats|reset] ...
model: claude-haiku-4-5
effort: low
allowed-tools: Read, Edit, Write
disable-model-invocation: true
---
# /seamark:feedback - Adaptive Learning Feedback

Use this command only when the user explicitly wants persistent Claude-side learning for the `/seamark:*` workflow.

## Input

Subcommand and arguments: `$ARGUMENTS`

Store signal files under `~/.claude/seamark-learning/signals/` — this is the directory `/seamark:learn` reads. `ADAPTATIONS.md` lives one level up at `~/.claude/seamark-learning/ADAPTATIONS.md`.

## Subcommands

### `approve <skill> <detail>`

Write an approval signal to `signals/feedback.jsonl`.

### `reject <skill> <detail>`

Write a rejection signal to `signals/feedback.jsonl`.

### `prefer <category> <value>`

Supported categories:

- `plan_depth`
- `question_count`
- `iteration_tolerance`
- `research_depth`
- `review_strictness`
- `agent_count`
- `commit_style`
- `test_approach`

Write a preference signal to `signals/feedback.jsonl`.

### `style <language> <detail>`

Write a language-specific style preference signal to `signals/feedback.jsonl`.

### `show`

Read and display `~/.claude/seamark-learning/ADAPTATIONS.md`, or say it does not exist yet.

### `stats`

Show signal counts by file and whether `ADAPTATIONS.md` exists.

### `reset`

Ask for confirmation first. Only clear learning data if the user confirms. Clear by overwriting each signal file under `~/.claude/seamark-learning/signals/` to empty with the Write tool — do **not** delete the files (`Write` is the only mutation tool granted here, and an emptied file is an equivalent reset). Report which files were cleared.

### No arguments

Show:

```text
/seamark:feedback <subcommand>
  approve <skill> <detail>
  reject <skill> <detail>
  prefer <category> <value>
  style <language> <detail>
  show
  stats
  reset
```

## Valid Skills

- `index`
- `status`
- `refine`
- `research`
- `plan`
- `implement`
- `review`
- `verify`
- `develop`
- `analyze`
- `cr`

## Rules

- Apply `${CLAUDE_PLUGIN_ROOT}/rules/rigor.md`. No shortcuts: write each signal exactly once, with the actual subcommand, skill, and timestamp; never silently skip persistence because the signal "feels minor". Use the file-system tools to read and append, not Bash echo. Do not compress reasoning or signal content — full context is what makes `/seamark:learn` useful.
- Store signals as timestamped JSONL entries
- Keep this layer opt-in; do not suggest it unless the user wants persistence
