#!/usr/bin/env python3
"""
Regression tests for hooks/enforce-develop-phase.py.

Run with `python3 hooks/test_enforce_develop_phase.py`. The Bash-analysis
cases exercise `bash_write_targets` in-process. The gate cases run the hook
as a subprocess with a synthetic PreToolUse payload against a temporary
project that carries `.m/DEVELOP_ACTIVE`, with HOME pointed at a scratch
directory so denial signals never reach the real signal log.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "enforce-develop-phase.py"
)


def load_hook_module():
    """Import the hyphenated hook file as a module."""
    spec = importlib.util.spec_from_file_location("enforce_develop_phase", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hook = load_hook_module()
OPAQUE = hook.OPAQUE_TARGET

WRITE_TARGET_CASES = [
    ("read-only listing", "ls -la src", []),
    ("null redirects are not writes", "grep -rn foo src > /dev/null 2>&1", []),
    ("quoted angle bracket is not a redirect", "echo 'a > b'", []),
    ("git read-only", "git status && git diff --stat", []),
    ("inline python without writes", "python3 -c 'print(1)'", []),
    ("heredoc body is not shell syntax",
     "python3 - <<'EOF'\nx = 1 > 0\nprint(x)\nEOF", []),
    ("marker touch under .m",
     "mkdir -p .m && touch .m/phase-refine-started",
     [".m", ".m/phase-refine-started"]),
    ("newline separates commands", "mkdir -p .m\ntouch .m/x", [".m", ".m/x"]),
    ("heredoc redirect", "cat > out.txt <<'EOF'\nif a > b:\n    pass\nEOF",
     ["out.txt"]),
    ("append redirect", "echo hi >> log.txt", ["log.txt"]),
    ("sed in place", "sed -i 's/a/b/' src/main.go", ["src/main.go"]),
    ("sed in place with expression flag",
     "sed -i -e 's/a/b/' a.txt b.txt", ["a.txt", "b.txt"]),
    ("perl in place", "perl -pi -e 's/a/b/' lib/x.pl", ["lib/x.pl"]),
    ("tee append", "printf 'x' | tee -a notes.md", ["notes.md"]),
    ("copy names both paths", "cp a.txt b.txt", ["a.txt", "b.txt"]),
    ("rm under .m", "rm -rf .m/handoff/kimi-scratch", [".m/handoff/kimi-scratch"]),
    ("xargs with stdin targets is opaque", "cat list | xargs -0 rm -f", [OPAQUE]),
    ("wrappers and assignments skipped", "FOO=1 env BAR=2 tee out", ["out"]),
    ("git apply is opaque", "git apply fix.patch", [OPAQUE]),
    ("git checkout is opaque", "git checkout -- src/", [OPAQUE]),
    ("python heredoc write is opaque",
     "python3 - <<'EOF'\nopen('x.txt', 'w').write('hi')\nEOF", [OPAQUE]),
    ("node inline write is opaque",
     "node -e \"require('fs').writeFileSync('a.js','x')\"", [OPAQUE]),
    ("patch is opaque", "patch -p1 < fix.diff", [OPAQUE]),
    ("input redirect is not a target", "sort < names.txt", []),
]

GATE_CASES = [
    ("edit outside .m denied", "Edit", {"file_path": "src/app.go"}, False, True),
    ("write inside .m allowed", "Write", {"file_path": ".m/PLAN.md"}, False, False),
    ("edit allowed once phase entered", "Edit", {"file_path": "src/app.go"},
     True, False),
    ("bash marker touch allowed", "Bash",
     {"command": "mkdir -p .m && touch .m/phase-implement-started"},
     False, False),
    ("bash sed outside .m denied", "Bash",
     {"command": "sed -i 's/a/b/' src/app.go"}, False, True),
    ("bash sed allowed once phase entered", "Bash",
     {"command": "sed -i 's/a/b/' src/app.go"}, True, False),
    ("bash read-only allowed", "Bash",
     {"command": "git diff --stat && grep -rn TODO src"}, False, False),
    ("bash heredoc write denied", "Bash",
     {"command": "cat > src/new.go <<'EOF'\npackage main\nEOF"}, False, True),
    ("bash git apply denied", "Bash", {"command": "git apply fix.patch"},
     False, True),
    ("bash write into .m allowed", "Bash",
     {"command": "echo 0 > .m/handoff/codex-meter.txt"}, False, False),
    ("notebook edit not gated", "NotebookEdit",
     {"notebook_path": "a.ipynb"}, False, False),
]


def make_project(root, phase="implement", started=False):
    """Create a project root with the pipeline markers under `.m/`."""
    m_dir = os.path.join(root, ".m")
    os.makedirs(os.path.join(root, "src"), exist_ok=True)
    os.makedirs(m_dir, exist_ok=True)
    with open(os.path.join(m_dir, "DEVELOP_ACTIVE"), "w", encoding="utf-8") as f:
        f.write(f"current_phase: {phase}\n")
    if started:
        open(os.path.join(m_dir, f"phase-{phase}-started"), "w").close()


def run_hook(payload, home):
    """Run the hook once with `payload` on stdin; return (exit code, stdout)."""
    env = dict(os.environ, HOME=home)
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    result = subprocess.run(
        [sys.executable, HOOK], input=stdin, capture_output=True, text=True,
        env=env,
    )
    return result.returncode, result.stdout


def denied(stdout: str) -> bool:
    """True when stdout carries a PreToolUse deny decision."""
    if not stdout.strip():
        return False
    decision = json.loads(stdout)["hookSpecificOutput"]
    return decision["permissionDecision"] == "deny"


class BashWriteTargets(unittest.TestCase):
    """Shell analysis returns the paths a command writes."""

    def test_write_targets(self):
        for name, command, expected in WRITE_TARGET_CASES:
            with self.subTest(name):
                self.assertEqual(hook.bash_write_targets(command), expected)


class PhaseGate(unittest.TestCase):
    """The hook allows or denies according to the phase markers."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        os.makedirs(self.home)
        self.project = os.path.join(self.tmp.name, "project")

    def tearDown(self):
        self.tmp.cleanup()

    def payload(self, tool, tool_input, cwd=None):
        return {
            "tool_name": tool,
            "tool_input": tool_input,
            "cwd": cwd or self.project,
        }

    def test_gate_cases(self):
        for name, tool, tool_input, started, expect_deny in GATE_CASES:
            with self.subTest(name):
                make_project(self.project, started=started)
                code, out = run_hook(self.payload(tool, tool_input), self.home)
                self.assertEqual(code, 0)
                self.assertEqual(denied(out), expect_deny)
                marker = os.path.join(self.project, ".m", "phase-implement-started")
                if os.path.exists(marker):
                    os.remove(marker)

    def test_relative_paths_resolve_against_payload_cwd(self):
        make_project(self.project)
        nested = os.path.join(self.project, "src")
        code, out = run_hook(
            self.payload("Edit", {"file_path": "app.go"}, cwd=nested), self.home
        )
        self.assertEqual(code, 0)
        self.assertTrue(denied(out))
        code, out = run_hook(
            self.payload("Write", {"file_path": "../.m/notes.md"}, cwd=nested),
            self.home,
        )
        self.assertEqual(code, 0)
        self.assertFalse(denied(out))

    def test_no_active_marker_allows_everything(self):
        os.makedirs(os.path.join(self.project, "src"))
        code, out = run_hook(
            self.payload("Bash", {"command": "sed -i 's/a/b/' src/app.go"}),
            self.home,
        )
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_malformed_stdin_fails_open(self):
        make_project(self.project)
        code, out = run_hook("not json", self.home)
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_unreadable_marker_denies(self):
        make_project(self.project)
        with open(os.path.join(self.project, ".m", "DEVELOP_ACTIVE"), "w") as f:
            f.write("garbage\n")
        code, out = run_hook(
            self.payload("Bash", {"command": "tee src/x.txt"}), self.home
        )
        self.assertEqual(code, 0)
        self.assertTrue(denied(out))

    def test_denial_signal_records_bash_target(self):
        make_project(self.project)
        run_hook(
            self.payload("Bash", {"command": "sed -i 's/a/b/' src/app.go"}),
            self.home,
        )
        run_hook(self.payload("Bash", {"command": "git apply fix.patch"}), self.home)
        signal = os.path.join(
            self.home, ".claude", "m-learning", "signals", "gate-denials.jsonl"
        )
        with open(signal, encoding="utf-8") as f:
            records = [json.loads(line) for line in f]
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["tool"], "Bash")
        self.assertEqual(records[0]["path"], "src/app.go")
        self.assertEqual(records[0]["phase"], "implement")
        self.assertEqual(records[0]["reason"], "missing_phase_marker")
        self.assertIsNone(records[1]["path"])
        self.assertNotIn("/", str(records[0]["project"]))


if __name__ == "__main__":
    unittest.main(verbosity=1)
