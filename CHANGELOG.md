# Changelog

This file lists the changes in each version of the `seamark` plugin. The version is the `version` field in `.claude-plugin/plugin.json`. Claude Code updates an installed plugin only when that field changes.

## 1.2.0 - 2026-09-30

### Changed

- `/seamark:plan` runs on Sonnet 5.5 in place of Opus 5.5. In the eval sweep, Sonnet 5.5 passed 15 of 15 plan trials, the same as Opus 5.5, at 37% lower cost. (#11)
- The `seamark-status` entry in the marketplace installs from `milaroid/seamark-status`. (#8, #10)
- The README links point to the `milaroid` account. (#8, #10)
- The Why loop in the README shows the full Seamark run, and all README loops render at 2x. (#10, #12)

### Fixed

- The phase hook runs when the plugin install path contains a space. The hook command now quotes `${CLAUDE_PLUGIN_ROOT}`. Before this fix, the shell split the path, the command exited 127, and the phase gate did not run.
- `/seamark:learn` refers to the Seamark source checkout, not the old `m-pipeline` name. (#8)

### Added

- A GitHub Actions workflow runs the static eval profile and validates the marketplace and the plugin on each pull request and on each push to `main`. The static profile runs the hook tests, the grader tests, and the fixture preflight.
- An "Update" section in the README, and this changelog.

## 1.1.0 - 2026-09-29

The first release under the Seamark name. The git tag for this release is `v1.0`.

- The five phases: `/seamark:refine`, `/seamark:plan`, `/seamark:implement`, `/seamark:review` or `/seamark:review-fanout`, and `/seamark:verify`. `/seamark:develop` runs all five.
- A `PreToolUse` hook that blocks writes outside `.seamark/` until the active phase has started through its skill.
- 16 commands and 5 expert skills.
- The eval harness in `evals/`.
