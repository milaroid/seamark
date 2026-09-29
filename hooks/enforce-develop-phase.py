#!/usr/bin/env python3
"""
PreToolUse hook for Edit, Write, MultiEdit, and Bash.

Purpose: enforce the /seamark:develop phase protocol. When /seamark:develop is active
(marker file `.seamark/DEVELOP_ACTIVE` present in the project root), this hook
blocks file mutation outside `.seamark/` unless the current required phase has
been entered via its corresponding /seamark:* skill (marker file
`.seamark/phase-<name>-started` present).

Scope: Edit, Write, and MultiEdit are gated on their `file_path`. Bash is
gated on the command text through `bash_write_targets.py`, which finds
output redirections, `tee`, in-place `sed` and `perl`, file-management
commands such as `cp`, `mv`, `rm`, `touch`, and `mkdir`, `git` subcommands
that mutate the working tree, and inline interpreter scripts that call a
write API. The hook denies when any target resolves outside `.seamark/` or cannot
be attributed to a path. Read-only Bash commands pass untouched. Auto mode
steers Claude toward `sed` and heredoc edits instead of the file tools, so
a file-tool-only gate would see none of the edits it exists to gate.
NotebookEdit (which carries `notebook_path`, not `file_path`) is not gated.

The Bash check is a heuristic over shell syntax; its limits are listed in
`bash_write_targets.py`. The gate remains a cooperative guardrail for the
pipeline's own tools, not a sandbox against arbitrary mutation.

Marker protocol
---------------

`.seamark/DEVELOP_ACTIVE` is written by `/seamark:develop` on pipeline entry and
deleted on pipeline exit. It is a single-line YAML-ish file:

    current_phase: <refine|plan|implement|review|verify|readiness>

Each `/seamark:*` phase skill is required to:

- On entry: touch `.seamark/phase-<name>-started`
- On successful completion: touch `.seamark/phase-<name>-done`

`/seamark:develop` updates `current_phase` in `.seamark/DEVELOP_ACTIVE` at every stage
transition, and verifies the prior phase's `-done` marker before moving on.

Allow list
----------

Writes to the following paths always pass, because the protocol itself
must be able to write them:

- Anything under `.seamark/` (PLAN.md, REFINE.md, PROGRESS.md, phase markers,
  handoff dirs, etc.), whether written by a file tool or by a Bash command
  such as `mkdir -p .seamark && touch .seamark/phase-plan-started`
- The `DEVELOP_ACTIVE` marker itself

Relative paths resolve against the `cwd` the payload carries, which is the
directory the tool call runs in.

Everything else under the project root is blocked until the active phase
is entered via its skill. During readiness it remains blocked even after
entry: the assessment never edits the application. Bookkeeping under .seamark/
and read-only commands remain allowed.

Denial signals
--------------

Every denial appends one JSON record to
`~/.claude/seamark-learning/signals/gate-denials.jsonl`, which `/seamark:learn` reads
alongside the other signal files. A denial is the only record of pipeline
discipline that the agent being gated does not author, so it is kept even
though the hook is otherwise stateless. The `path` field names the blocked
target; it is null for a Bash write the hook cannot attribute to a path.

The decision is always emitted and flushed before any signal work begins,
so neither a raising nor a blocking signal write can suppress or delay it —
see `emit_deny` and `record_denial`.
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bash_write_targets import OPAQUE_TARGET, bash_write_targets


FILE_TOOLS = {"Edit", "Write", "MultiEdit"}
GATED_TOOLS = FILE_TOOLS | {"Bash"}

KNOWN_PHASES = {"refine", "plan", "implement", "review", "verify", "readiness"}

SIGNAL_FILE = "gate-denials.jsonl"
MAX_RECORD_BYTES = 4096
MAX_PATH_CHARS = 200

def find_project_root(start_dir: str):
    """Walk up from start_dir looking for `.seamark/DEVELOP_ACTIVE`.

    Returns the directory that contains `.seamark/DEVELOP_ACTIVE`, or None if no
    such directory is found before reaching the filesystem root. The walk
    terminates at the root (parent == current); there is no fixed depth cap,
    so a deeply nested cwd cannot silently slip past the gate.
    """
    current = os.path.abspath(start_dir)
    while True:
        candidate = os.path.join(current, ".seamark", "DEVELOP_ACTIVE")
        if os.path.isfile(candidate):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def parse_current_phase(active_path: str):
    """Parse `current_phase:` out of the DEVELOP_ACTIVE marker."""
    try:
        with open(active_path, "r", encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if line.startswith("current_phase:"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        return None
    return None


def resolve_target(target: str, cwd: str) -> str:
    """Absolute form of a write target, resolving relative paths against cwd."""
    if not target:
        return ""
    expanded = os.path.expanduser(target)
    return expanded if os.path.isabs(expanded) else os.path.join(cwd, expanded)


def is_allowlisted(target_path: str, project_root: str) -> bool:
    """True when the write target is within the pipeline bookkeeping area.

    Uses realpath (not abspath) so a symlink planted inside `.seamark/` cannot
    point outside the bookkeeping area and smuggle a write past the gate.
    """
    if not target_path:
        return True
    abs_target = os.path.realpath(target_path)
    seamark_dir = os.path.realpath(os.path.join(project_root, ".seamark"))
    return abs_target == seamark_dir or abs_target.startswith(seamark_dir + os.sep)


def bash_gate_target(command: str, project_root: str, cwd: str):
    """First Bash write target outside `.seamark/`, OPAQUE_TARGET, or None to allow.

    The returned target is the resolved absolute path, so the denial message
    and the signal record name the same file the command would write.
    """
    for target in bash_write_targets(command):
        if target == OPAQUE_TARGET:
            return OPAQUE_TARGET
        resolved = resolve_target(target, cwd)
        if not is_allowlisted(resolved, project_root):
            return resolved
    return None


def gated_target(payload, project_root: str, cwd: str):
    """The path a tool call would mutate outside `.seamark/`, or None to allow."""
    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}
    if tool_name == "Bash":
        command = tool_input.get("command", "") or ""
        return bash_gate_target(command, project_root, cwd)
    target = resolve_target(tool_input.get("file_path", "") or "", cwd)
    return None if is_allowlisted(target, project_root) else target


def relative_target(target_path: str, project_root: str):
    """Repository-relative form of a write target, capped at MAX_PATH_CHARS.

    Returns None for an empty target, and falls back to the bare basename
    when the target resolves outside the project root. An absolute path is
    never returned, because the signal log is global and spans every
    repository the user works in.
    """
    if not target_path:
        return None
    try:
        relative = os.path.relpath(
            os.path.realpath(target_path), os.path.realpath(project_root)
        )
    except ValueError:
        return os.path.basename(target_path)[:MAX_PATH_CHARS]
    if relative.startswith(".."):
        return os.path.basename(target_path)[:MAX_PATH_CHARS]
    return relative[:MAX_PATH_CHARS]


def recorded_phase(phase):
    """The phase name safe to write into the global signal log.

    Returns None when no phase was parsed, the phase itself when it names a
    known pipeline phase, and the literal `unrecognized` otherwise. The
    marker file this value comes from is writable by the agent the gate
    denies, and the log is read back into `/seamark:learn`, so arbitrary marker
    text must never reach it.
    """
    if phase is None:
        return None
    return phase if phase in KNOWN_PHASES else "unrecognized"


def record_denial(project_root, phase, tool_name, target_path, reason) -> None:
    """Append one gate-denial record to the global learning-signal log.

    `reason` is `missing_phase_marker` when the active phase was never
    entered through its skill, or `unreadable_marker` when DEVELOP_ACTIVE
    is present but carries no parseable `current_phase:` line, in which
    case `phase` is None. `read_only_phase` records an attempted mutation
    outside bookkeeping during readiness.

    Must only be called after `emit_deny` has already flushed the decision.
    Nothing here can suppress a denial, but it can still fail or stall, so
    ordering is the guarantee rather than the exception handling: a failure
    returns after one stderr line, and the log is opened non-blocking so a
    FIFO or similar planted at the signal path fails fast instead of hanging
    the hook.

    `phase` is recorded only when it names a known pipeline phase. Anything
    else becomes the literal `unrecognized`, because the marker file is
    writable by the very agent this gate denies and the log is read back
    into `/seamark:learn`.

    The record is built in full and written with a single append so
    concurrent sessions cannot interleave partial lines; a record that would
    exceed MAX_RECORD_BYTES is dropped rather than split.
    """
    try:
        home = os.path.expanduser("~")
        if home == "~" or not os.path.isdir(home):
            return
        signals_dir = os.path.join(home, ".claude", "seamark-learning", "signals")
        os.makedirs(signals_dir, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "type": "gate_denial",
            "reason": reason,
            "project": os.path.basename(project_root),
            "phase": recorded_phase(phase),
            "tool": tool_name,
            "path": relative_target(target_path, project_root),
        }
        line = json.dumps(record, separators=(",", ":")) + "\n"
        if len(line.encode("utf-8")) > MAX_RECORD_BYTES:
            return
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NONBLOCK", 0)
        handle = os.open(os.path.join(signals_dir, SIGNAL_FILE), flags, 0o600)
        try:
            os.write(handle, line.encode("utf-8"))
        finally:
            os.close(handle)
    except Exception as exc:
        try:
            print(
                f"[enforce-develop-phase] denial signal not recorded: "
                f"{type(exc).__name__}",
                file=sys.stderr,
            )
        except Exception:
            pass
        return


def emit_deny(reason: str) -> None:
    """Print the deny decision on stdout and flush it.

    Deliberately does not exit. Callers emit the decision first, then record
    the signal, then exit — so no signal-path failure or stall can suppress
    or delay a denial that has already been delivered.
    """
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.stdout.flush()


def describe_target(target: str) -> str:
    """Human-readable form of a blocked target for the denial message."""
    if target == OPAQUE_TARGET:
        return (
            "a write the hook cannot attribute to a path (git working-tree "
            "mutation, patch, or an inline interpreter script)"
        )
    return repr(target)


def enforce_phase(project_root: str, tool_name: str, target: str) -> None:
    """Deny the call unless the active phase has been entered via its skill.

    Emits the decision first and records the denial signal second, so the
    signal path can never suppress the decision. Returns without output when
    a writable phase's `-started` marker exists. Readiness never permits
    mutation outside bookkeeping, even after entry.
    """
    active_path = os.path.join(project_root, ".seamark", "DEVELOP_ACTIVE")
    current_phase = parse_current_phase(active_path)
    signal_target = "" if target == OPAQUE_TARGET else target
    if not current_phase:
        emit_deny(
            "`.seamark/DEVELOP_ACTIVE` is present but `current_phase:` is missing "
            "or unreadable. Either fix the marker or delete it if /seamark:develop "
            "is not actually running."
        )
        record_denial(
            project_root, None, tool_name, signal_target, "unreadable_marker"
        )
        return

    if current_phase == "readiness":
        emit_deny(
            "/seamark:readiness is a read-only release assessment. Writes outside "
            "`.seamark/` are blocked even after the phase has started. Return fixes "
            "through /seamark:plan or /seamark:implement, then review and verify before "
            f"reassessing readiness. Blocked target: {describe_target(target)}."
        )
        record_denial(
            project_root, current_phase, tool_name, signal_target,
            "read_only_phase",
        )
        return

    started_marker = os.path.join(
        project_root, ".seamark", f"phase-{current_phase}-started"
    )
    if os.path.isfile(started_marker):
        return

    emit_deny(
        "/seamark:develop pipeline is active and the current phase "
        f"({current_phase!r}) has not been entered via its skill.\n\n"
        f"Before any Edit/Write/MultiEdit, or any Bash command that writes, "
        f"outside `.seamark/`, you must invoke the corresponding skill (for "
        f"example: Skill(skill=\"seamark:{current_phase}\")). The skill is required "
        f"to touch `.seamark/phase-{current_phase}-started` on entry. That marker "
        f"is missing, so this tool call is blocked.\n\n"
        f"Blocked target: {describe_target(target)}.\n\n"
        f"If /seamark:develop is not actually running, remove "
        f"`.seamark/DEVELOP_ACTIVE` to disable this gate."
    )
    record_denial(
        project_root, current_phase, tool_name, signal_target,
        "missing_phase_marker",
    )


def main() -> None:
    """Gate one Edit/Write/MultiEdit/Bash call against the active phase marker.

    Malformed or empty stdin fails open by design: the hook exits 0 (allow)
    rather than denying, because a parser hiccup would otherwise brick every
    edit in the session. Do not harden that path to fail closed.
    """
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = payload.get("tool_name", "")
    if tool_name not in GATED_TOOLS:
        sys.exit(0)

    cwd = payload.get("cwd") or os.getcwd()
    project_root = find_project_root(cwd)
    if not project_root:
        sys.exit(0)

    target = gated_target(payload, project_root, cwd)
    if target is None:
        sys.exit(0)

    enforce_phase(project_root, tool_name, target)
    sys.exit(0)


if __name__ == "__main__":
    main()
