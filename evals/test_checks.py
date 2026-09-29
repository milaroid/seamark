"""Regression tests for evidence handling, outcomes, and comparison validity."""

import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from checks import InvalidRun, Trace, commands, denial_blocks_contract, evaluate, file_hashes, grade_trial, phase_order, runs_command, verdict
from run import EVALS, ROOT, aggregate, compare, rejudge_run, copy_plugin, digest, preflight, preserve, regrade, rejudge_trial, save, semantic_evidence, suite_config
from selection import case_model, noise_floor, pinned_model, split_cases


def events(cwd, calls=(), final="PASSED"):
    result = [{"type": "system", "subtype": "init", "cwd": str(cwd), "slash_commands": ["seamark:implement"]}]
    for index, (name, args, failed) in enumerate(calls):
        ident = f"tool-{index}"
        result.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": ident, "name": name, "input": args}]}})
        result.append({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": ident, "is_error": failed, "content": "exit 1" if failed else "ok"}]}})
    result.append({"type": "result", "subtype": "success", "is_error": False, "result": final})
    return result


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.trace_path = self.root / "trace.jsonl"
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()

    def trace(self, calls=(), final="PASSED"):
        return Trace(events(self.workspace, calls, final))

    def test_command_mentions_are_not_invocations(self):
        trace = self.trace(final="I invoked seamark:implement and ran go test ./...")
        check = {"kind": "skill", "name": "seamark:implement"}
        self.assertFalse(evaluate(check, trace, self.workspace, {}, self.root)[0])
        self.assertEqual(trace.calls, [])

    def test_failed_skill_does_not_count(self):
        trace = self.trace([("Skill", {"skill": "seamark:implement"}, True)])
        self.assertFalse(evaluate({"kind": "skill", "name": "seamark:implement"}, trace, self.workspace, {}, self.root)[0])

    def test_truncated_and_nonterminal_traces_are_invalid(self):
        for content in ("[…64 messages elided…]\n", '{"type":"system","subtype":"init","cwd":"/tmp"}\n', '[]\n'):
            with self.subTest(content=content):
                self.trace_path.write_text(content)
                with self.assertRaises(InvalidRun):
                    Trace.read(self.trace_path)

    def test_missing_tool_result_is_invalid(self):
        data = events(self.workspace, [("Bash", {"command": "go test ./..."}, False)])
        del data[2]
        with self.assertRaises(InvalidRun):
            Trace(data)

    def test_unknown_command_is_invalid_not_a_safe_pass(self):
        with self.assertRaises(InvalidRun):
            self.trace(final="Unknown command: /seamark:verify")

    def test_shell_execution_requires_a_successful_tool_result(self):
        scenarios = [
            ("go test ./...", False, True),
            ("cd src && go test ./...", False, True),
            ("echo 'go test ./...'", False, False),
            ("printf '%s' 'go test ./...'", False, False),
            ("go test ./...", True, False),
        ]
        for command, failed, wanted in scenarios:
            with self.subTest(command=command, failed=failed):
                call = self.trace([("Bash", {"command": command}, failed)]).calls[0]
                self.assertEqual(runs_command(call, ["go", "test"], require_success=True), wanted)

    def test_failing_checks_still_count_as_executed(self):
        trace = self.trace([("Bash", {"command": "python3 check.py"}, True)], final="BLOCKED")
        self.assertTrue(runs_command(trace.calls[0], ["python3", "check.py"]))
        self.assertFalse(runs_command(trace.calls[0], ["python3", "check.py"], require_success=True))

    def test_repeated_fixture_checks_in_one_tool_call_use_execution_history(self):
        for name in ("check.py", "verification.json"):
            (self.workspace / name).write_text("fixture")
        initial = file_hashes(self.workspace)
        history = self.workspace / ".checks/runs.jsonl"
        history.parent.mkdir()
        history.write_text('{"run":1,"exit_code":1}\n{"run":2,"exit_code":0}\n')
        check = {"kind": "command", "argv": ["python3", "check.py"], "min": 2}
        trace = self.trace([("Bash", {"command": "for i in 1 2; do out=$(python3 check.py); done"}, False)])
        self.assertTrue(evaluate(check, trace, self.workspace, initial, self.root)[0])
        self.assertFalse(evaluate(check, self.trace(), self.workspace, initial, self.root)[0])
        (self.workspace / "check.py").write_text("modified")
        self.assertFalse(evaluate(check, trace, self.workspace, initial, self.root)[0])

    def test_complete_evidence_judge_keeps_middle_tool_results_and_three_votes(self):
        self.trace_path.write_text("\n".join(json.dumps(e) for e in events(self.workspace, [("Bash", {"command": "python3 check.py"}, False)] * 40)))
        evidence = semantic_evidence(self.trace_path)
        self.assertEqual(len(evidence["messages"]), 80)
        self.assertEqual(evidence["messages"][39]["content"][0]["type"], "tool_result")
        raw = {"graders": [{"name": "criteria", "passed": False}]}
        response = SimpleNamespace(returncode=0, stderr="", stdout=json.dumps({"result": json.dumps({"passed": True, "reason": "Observed verification result"}), "total_cost_usd": 0.1}))
        with patch("run.subprocess.run", return_value=response) as call:
            updated, cost = rejudge_trial(raw, "verify--happy", self.trace_path, "test-judge", 3)
        self.assertEqual(call.call_count, 3)
        self.assertEqual(updated["graders"][0]["judgeVotes"], [True, True, True])
        self.assertAlmostEqual(cost, 0.3)
        self.assertEqual(len(json.loads(call.call_args.kwargs["input"])["observed_evidence"]["messages"]), 80)
        response.stdout = json.dumps({"structured_output": {"passed": "true", "reason": "invalid boolean"}})
        with patch("run.subprocess.run", return_value=response), self.assertRaises(InvalidRun):
            rejudge_trial(raw, "verify--happy", self.trace_path, "test-judge", 3)

    def test_optional_out_of_scope_search_denial_is_a_diagnostic(self):
        data = events(self.workspace, [("Grep", {"path": str(self.root), "pattern": "develop"}, True)])
        data[2]["message"]["content"][0]["content"] = "Permission to use Grep has been denied"
        trace = Trace(data)
        self.assertEqual(len(trace.permission_denials), 1)
        self.assertFalse(denial_blocks_contract(trace.calls[0], trace, {"required_files": ["email.go"]}))

    def test_required_verification_denial_is_invalid(self):
        data = events(self.workspace, [("Bash", {"command": "python3 check.py"}, True)])
        data[2]["message"]["content"][0]["content"] = "Permission to use Bash has been denied"
        trace = Trace(data)
        self.assertTrue(denial_blocks_contract(trace.calls[0], trace, {"checks": [{"kind": "command", "argv": ["python3", "check.py"]}]}))

    def test_verdict_requires_an_explicit_outcome(self):
        for text, expected in [
            ("Never emit PASSED while checks fail.", None),
            ("### Pipeline Stages Run\n`refine → plan → implement → review → verify (1 loop, PASSED)`\n### Scope\nLocal", "PASSED"),
            ("### Pipeline Stages Run\n`verify (1 loop, PASSED)`\n### Checks Run\nReview verdict `APPROVED`", "PASSED"),
            ("### Pipeline Stages Run\n`verify (1 loop, PASSED)`\n### Verdict\nBLOCKED", "BLOCKED"),
            ("Example: verify (1 loop, PASSED)", None),
            ("### Verdict\n\n**BLOCKED**", "BLOCKED"),
            ("### Verdict\n`BLOCKED`", "BLOCKED"),
            ("**Verdict: PASSED**", "PASSED"),
            ("The working tree is empty. **Verdict: BLOCKED** until the files are supplied.", "BLOCKED"),
            ("```\nPASSED\n```\nBLOCKED", "BLOCKED"),
            ("### Verdict\nN/A", "N/A"),
            ("APPROVED WITH WARNINGS", "APPROVED WITH WARNINGS"),
        ]:
            with self.subTest(text=text):
                self.assertEqual(verdict(text), expected)

    def test_completed_markers_do_not_replace_phase_calls(self):
        marker = self.workspace / ".seamark/phase-plan-done"
        marker.parent.mkdir()
        marker.touch()
        self.assertFalse(phase_order(self.trace(), ["plan", "implement"]))

    def test_phase_transition_needs_observed_completion(self):
        good = [
            ("Skill", {"skill": "seamark:plan"}, False),
            ("Bash", {"command": "touch .seamark/phase-plan-done"}, False),
            ("Skill", {"skill": "seamark:implement"}, False),
        ]
        self.assertTrue(phase_order(self.trace(good), ["plan", "implement"]))
        self.assertFalse(phase_order(self.trace([good[0], good[2]]), ["plan", "implement"]))
        self.assertFalse(phase_order(self.trace([good[2], good[1], good[0]]), ["plan", "implement"]))
        self.assertFalse(phase_order(self.trace([good[1], good[0], good[2]]), ["plan", "implement"]))
        self.assertFalse(phase_order(self.trace([good[2], *good]), ["plan", "implement"]))

    def test_initial_file_hashes_detect_deleted_tests(self):
        source = self.workspace / "email_test.go"
        source.write_text("original test")
        initial = file_hashes(self.workspace)
        source.unlink()
        self.assertFalse(evaluate({"kind": "unchanged", "paths": ["*_test.go"]}, self.trace(), self.workspace, initial, self.root)[0])

    def test_escaping_artifact_is_invalid(self):
        target = self.root / "outside"
        target.write_text("PASSED")
        (self.workspace / "result").symlink_to(target)
        with self.assertRaises(InvalidRun):
            evaluate({"kind": "contains", "path": "result", "text": "PASSED"}, self.trace(), self.workspace, {}, self.root)

    def test_missing_paid_grade_is_invalid(self):
        self.trace_path.write_text("\n".join(json.dumps(e) for e in events(self.workspace)))
        result = grade_trial({"graders": [], "skippedPaidGraders": True}, {"graders": ["criteria"]}, self.trace_path, self.workspace, {}, self.root)
        self.assertEqual(result["status"], "INVALID")

    def test_fabricated_completion_fails_despite_semantic_pass(self):
        self.trace_path.write_text("\n".join(json.dumps(e) for e in events(self.workspace)))
        case = {"graders": ["criteria"], "checks": [{"id": "executed", "kind": "command", "argv": ["go", "test"]}]}
        raw = {"graders": [{"name": "criteria", "passed": True}]}
        result = grade_trial(raw, case, self.trace_path, self.workspace, {}, self.root)
        self.assertEqual(result["status"], "FAIL")

    def test_valid_completion_passes(self):
        calls = [("Bash", {"command": "go test ./..."}, False)]
        self.trace_path.write_text("\n".join(json.dumps(e) for e in events(self.workspace, calls)))
        case = {"graders": ["criteria"], "checks": [{"id": "executed", "kind": "command", "argv": ["go", "test"]}]}
        result = grade_trial({"graders": [{"name": "criteria", "passed": True}]}, case, self.trace_path, self.workspace, {}, self.root)
        self.assertEqual(result["status"], "PASS")

    @unittest.skipUnless(shutil.which("go"), "Go is needed for the oracle integration test")
    def test_oracle_rejects_stub_and_accepts_working_implementation(self):
        (self.workspace / "go.mod").write_text("module fixture\n\ngo 1.22\n")
        source = self.workspace / "email.go"
        source.write_text("package email\nfunc NormalizeEmail(s string) string { return s }\n")
        check = {"kind": "oracle", "file": "normalize_test.go"}
        oracle_root = Path(__file__).parent / "oracles"
        self.assertFalse(evaluate(check, self.trace(), self.workspace, {}, oracle_root)[0])
        source.write_text('package email\nimport "strings"\nfunc NormalizeEmail(s string) string { return strings.ToLower(strings.TrimSpace(s)) }\n')
        self.assertTrue(evaluate(check, self.trace(), self.workspace, {}, oracle_root)[0])

    @unittest.skipUnless(shutil.which("go"), "Go is needed for the oracle integration test")
    def test_oracle_rejects_testmain_that_skips_tests(self):
        (self.workspace / "go.mod").write_text("module fixture\n\ngo 1.22\n")
        (self.workspace / "email.go").write_text("package email\nfunc NormalizeEmail(s string) string { return s }\n")
        (self.workspace / "email_test.go").write_text('package email\nimport("os"; "testing")\nfunc TestMain(m *testing.M) { os.Exit(0) }\n')
        check = {"kind": "oracle", "file": "normalize_test.go"}
        passed, evidence = evaluate(check, self.trace(), self.workspace, {}, Path(__file__).parent / "oracles")
        self.assertFalse(passed)
        self.assertIn("Oracle tests did not pass", evidence)


class RunnerTests(unittest.TestCase):
    def test_invalid_trials_never_make_a_suite_green(self):
        result = aggregate([{"status": "PASS"}, {"status": "INVALID"}])
        self.assertEqual(result["status"], "INVALID")
        self.assertEqual(result["pass_rate"], 1)
        self.assertEqual(result["INVALID"], 1)
        self.assertEqual(aggregate([])["status"], "INVALID")

    def test_suite_discovery_and_scaffold_contracts(self):
        suite = suite_config()
        self.assertGreaterEqual(len(suite["cases"]), 30)
        self.assertTrue(all(case["checks"] for case in suite["cases"].values() if case["category"] == "execution"))

    def test_calibration_samples_reference_real_rubrics(self):
        root = Path(__file__).parent
        data = json.loads((root / "calibration/examples.json").read_text())
        for sample in data["examples"]:
            self.assertIn(sample["expected"], {"PASS", "FAIL"})
            self.assertTrue(sample["evidence"])
            self.assertTrue((root / sample["case"] / "graders/criteria.md").exists())

    def test_scaffold_errors_stop_preflight(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            (root / "broken").mkdir()
            (root / "broken/fixture.sh").write_text("exit 9\n")
            with self.assertRaisesRegex(InvalidRun, "scaffold failed"):
                preflight("broken", {}, root)

    def test_comparison_rejects_changed_graders_and_invalid_runs(self):
        with tempfile.TemporaryDirectory() as scratch:
            left, right = Path(scratch) / "left.json", Path(scratch) / "right.json"
            data = {"metadata": {"suite_hash": "a"}, "complete": True, "summary": {"INVALID": 0}}
            left.write_text(json.dumps(data))
            data["metadata"]["suite_hash"] = "b"
            right.write_text(json.dumps(data))
            with self.assertRaisesRegex(InvalidRun, "suite_hash"):
                compare(left, right)
            data["metadata"]["suite_hash"] = "a"
            data["complete"] = False
            right.write_text(json.dumps(data))
            with self.assertRaisesRegex(InvalidRun, "incomplete"):
                compare(left, right)

    def test_preserves_native_sealed_workspace_and_raw_evidence(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            native = root / "e-synthetic"
            out = native / "out"
            out.mkdir(parents=True)
            workspace = native / "sealed/home/cwd"
            workspace.mkdir(parents=True)
            (workspace / "result.go").write_text("package fixture\n")
            trace = out / "trace.jsonl"
            trace.write_text("\n".join(json.dumps(e) for e in events(native / "home/cwd")))
            (native / "sealed").chmod(0)
            kept_trace, kept_workspace = preserve({"tracePath": str(trace)}, root / "artifacts")
            self.assertEqual(kept_trace.read_text(), trace.read_text())
            self.assertEqual((kept_workspace / "result.go").read_text(), "package fixture\n")
            self.assertTrue((root / "artifacts/native-evidence/trace.jsonl").exists())

    def test_does_not_copy_a_workspace_outside_the_native_run(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            out = root / "native/out"
            out.mkdir(parents=True)
            trace = out / "trace.jsonl"
            trace.write_text("\n".join(json.dumps(e) for e in events(root / "unrelated")))
            with self.assertRaisesRegex(InvalidRun, "outside"):
                preserve({"tracePath": str(trace)}, root / "artifacts")

    def test_comparison_reports_arms_separately(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            data = {"metadata": {"cases": ["example"]}, "complete": True, "summary": {"INVALID": 0}, "trials": [
                {"candidate": "candidate", "arm": "with", "case": "example", "status": "PASS"},
                {"candidate": "candidate", "arm": "without", "case": "example", "status": "FAIL"},
            ]}
            left, right = root / "left.json", root / "right.json"
            left.write_text(json.dumps(data))
            data["trials"][0]["status"] = "FAIL"
            right.write_text(json.dumps(data))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                compare(left, right)
            rates = json.loads(output.getvalue())
            self.assertEqual(rates["candidate/with/example"]["delta"], -1)
            self.assertEqual(rates["overall"]["delta"], -0.5)
            self.assertEqual(rates["overall"]["noise_floor"], 0.707)
            self.assertFalse(rates["overall"]["exceeds_noise"])
            self.assertEqual(rates["candidate/without/example"]["delta"], 0)

    def test_regrade_uses_retained_evidence_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            source, output = root / "original", root / "regraded"
            snapshot = root / "snapshot"
            copy_plugin(ROOT, snapshot)
            name = "unrelated-request-ignores-plugin"
            artifact = Path("candidate") / name / "with/0"
            workspace = source / artifact / "workspace"
            workspace.mkdir(parents=True)
            (source / artifact / "trace.jsonl").write_text("\n".join(json.dumps(e) for e in events(workspace, final="Paris.")))
            shutil.copytree(EVALS / "oracles", source / "oracles")
            raw = {"graders": [{"name": "answers-paris", "passed": True}], "costUsd": 0.25}
            save(source / "candidate" / name / "native/aggregate-result.json", {"cases": [{"name": name, "arms": {"with": [raw]}}]})
            report = {
                "complete": True, "native_cost_usd": 0.25,
                "metadata": {"cases": [name], "suite_hash": digest(file_hashes(snapshot / "evals")),
                             "oracle_hash": digest(file_hashes(EVALS / "oracles")), "fixture_hashes": {name: digest({})}},
                "trials": [{"candidate": "candidate", "case": name, "arm": "with", "index": 0,
                            "status": "FAIL", "artifacts": str(artifact)}],
            }
            save(source / "result.json", report)
            original_bytes = (source / "result.json").read_bytes()
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(regrade(source / "result.json", output), 0)
            updated = json.loads((output / "result.json").read_text())
            self.assertEqual(updated["summary"]["PASS"], 1)
            self.assertEqual(updated["additional_cost_usd"], 0)
            self.assertEqual(updated["native_cost_usd"], 0.25)
            self.assertEqual((source / "result.json").read_bytes(), original_bytes)
            self.assertTrue((output / "checker.py").exists())
            second = Path("candidate") / name / "with/1"
            shutil.copytree(source / artifact, source / second)
            report["trials"].append({**report["trials"][0], "index": 1, "artifacts": str(second)})
            report["metadata"]["judge_model"] = "test-judge"
            save(source / "candidate" / name / "native/aggregate-result.json", {"cases": [{"name": name, "arms": {"with": [raw, raw]}}]})
            save(source / "result.json", report)
            with patch("run.rejudge_trial", return_value=(raw, 0.2)) as judge, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(regrade(source / "result.json", root / "parallel", 3, 2), 0)
            self.assertEqual([call.args[4] for call in judge.call_args_list], [1.5, 1.5])
            parallel = json.loads((root / "parallel/result.json").read_text())
            self.assertEqual(parallel["summary"]["PASS"], 2)
            self.assertAlmostEqual(parallel["additional_cost_usd"], 0.4)
            report["metadata"]["suite_hash"] = "changed"
            save(source / "result.json", report)
            with self.assertRaisesRegex(InvalidRun, "suite inputs changed"):
                regrade(source / "result.json", root / "rejected")


class ModelAndSplitTests(unittest.TestCase):
    def test_pinned_model(self):
        with tempfile.TemporaryDirectory() as temp:
            plugin = Path(temp)
            (plugin / "commands").mkdir()
            (plugin / "commands/verify.md").write_text("---\ndescription: x\nmodel: claude-sonnet-5-5\neffort: medium\n---\nbody model: other\n")
            (plugin / "commands/help.md").write_text("---\ndescription: no pin\n---\n")
            (plugin / "commands/plain.md").write_text("no frontmatter\n")
            tests = [
                ("stage pin", "verify--happy", "claude-sonnet-5-5"),
                ("no model key", "help--x", "fallback"),
                ("no frontmatter", "plain--x", "fallback"),
                ("no command", "unrelated-request-ignores-plugin", "fallback"),
            ]
            for name, case, want in tests:
                with self.subTest(name):
                    self.assertEqual(pinned_model(plugin, case, "fallback"), want)

    def test_case_model_modes(self):
        plugin = ROOT
        pinned = SimpleNamespace(model="pinned", fallback_model="fallback")
        fixed = SimpleNamespace(model="claude-opus-5-5", fallback_model="fallback")
        self.assertEqual(case_model(plugin, "unrelated-request-ignores-plugin", pinned), "fallback")
        self.assertEqual(case_model(plugin, "verify--happy", fixed), "claude-opus-5-5")

    def test_split_covers_suite_and_holds_out_every_stage(self):
        suite = json.loads((EVALS / "suite.json").read_text())
        train, test = split_cases("train"), split_cases("test")
        self.assertFalse(train & test)
        self.assertEqual(train | test, set(suite["cases"]))
        stages = {name.split("--")[0] for name in suite["cases"] if name.count("--")}
        for stage in stages:
            with self.subTest(stage):
                self.assertTrue(any(name.startswith(stage + "--") for name in test))
                self.assertTrue(any(name.startswith(stage + "--") for name in train))

    def test_split_file_hidden_from_agent(self):
        with tempfile.TemporaryDirectory() as temp:
            copy_plugin(ROOT, Path(temp) / "plugin")
            self.assertFalse((Path(temp) / "plugin/evals/split.json").exists())

    def test_noise_floor(self):
        tests = [("no trials", 0, None), ("37 cases one run", 37, 0.164), ("37 cases three runs", 111, 0.095)]
        for name, trials, want in tests:
            with self.subTest(name):
                self.assertEqual(noise_floor(trials), want)


class CommandParserTests(unittest.TestCase):
    def test_commands_strip_keywords_and_assignments(self):
        tests = [
            ("plain", "python3 check.py; echo ok", [["python3", "check.py"], ["echo", "ok"]]),
            ("loop body", "for i in 1 2; do python3 check.py; done", [["for", "i", "in", "1", "2"], ["python3", "check.py"], ["done"]]),
            ("env prefix", 'GOCACHE="$TMPDIR/g" CGO=0 python3 check.py', [["python3", "check.py"]]),
            ("if branch", "if true; then python3 check.py; else touch x; fi", [["if", "true"], ["python3", "check.py"], ["touch", "x"], ["fi"]]),
            ("negation", "! python3 check.py", [["python3", "check.py"]]),
            ("assignment only", "X=1; python3 check.py", [["python3", "check.py"]]),
            ("argument kept", "echo A=1", [["echo", "A=1"]]),
        ]
        for name, command, want in tests:
            with self.subTest(name):
                self.assertEqual(commands(command), want)


class HardCaseTests(unittest.TestCase):
    def test_preflight_accepts_declared_red_start(self):
        suite = suite_config()
        name = "verify--fix-in-scope"
        self.assertTrue(preflight(name, suite["cases"][name]))

    def test_preflight_rejects_undeclared_red_start(self):
        suite = suite_config()
        case = {k: v for k, v in suite["cases"]["verify--fix-in-scope"].items() if k != "initial_tests_fail"}
        with self.assertRaisesRegex(InvalidRun, "baseline Go tests exit"):
            preflight("verify--fix-in-scope", case)


class RejudgeDefaultTests(unittest.TestCase):
    def test_rejudge_default(self):
        tests = [
            ("complete run rejudges with remaining budget", True, 4, False, 0, 6),
            ("opt out keeps native verdict", True, 4, True, 1, None),
            ("incomplete run is not rejudged", False, 4, False, 1, None),
            ("exhausted budget is not rejudged", True, 10, False, 1, None),
        ]
        for name, complete, spent, opt_out, want_code, want_budget in tests:
            with self.subTest(name), tempfile.TemporaryDirectory() as scratch:
                output = Path(scratch) / "run"
                save(output / "result.json", {"complete": complete, "native_cost_usd": spent})
                args = SimpleNamespace(native_judge_only=opt_out, max_cost_usd=10, concurrency=4)
                with patch("run.regrade", return_value=0) as regrade_mock, contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(rejudge_run(output, args, 1), want_code)
                if want_budget is None:
                    regrade_mock.assert_not_called()
                else:
                    source, target, budget, concurrency = regrade_mock.call_args.args
                    self.assertEqual((target.name, budget, concurrency), ("run-rejudged", want_budget, 2))

    def test_budget_exhaustion_is_named(self):
        with tempfile.TemporaryDirectory() as scratch:
            trace = Path(scratch) / "trace.jsonl"
            trace.write_text("\n".join(json.dumps(e) for e in events(Path(scratch))))
            raw = {"graders": [{"name": "criteria", "passed": False}]}
            envelope = json.dumps({"subtype": "error_max_budget_usd", "is_error": True, "total_cost_usd": 0.07})
            completed = subprocess.CompletedProcess([], 1, stdout=envelope, stderr="")
            with patch("run.subprocess.run", return_value=completed):
                with self.assertRaisesRegex(InvalidRun, "rejudge budget exhausted"):
                    rejudge_trial(raw, "verify--happy", trace, "claude-sonnet-5", 1.0)

if __name__ == "__main__":
    unittest.main()
