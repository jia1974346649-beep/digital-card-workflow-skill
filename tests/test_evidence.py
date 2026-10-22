"""Synthetic labels test the checker, never assert that a real product was tested."""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "card-product-workflow" / "scripts" / "check_evidence.py"
SPEC = importlib.util.spec_from_file_location("check_evidence", SCRIPT)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def observation(identifier, kind, environment, scenario="submit-and-receive", **changes):
    record = {
        "id": identifier, "scenario": scenario, "kind": kind,
        "environment": environment, "version": "demo-v2", "digest": "DEMO_BUILD_A",
        "result": "passed", "observed_at": "2025-01-02T10:05:00Z", "origin": "observed",
    }
    record.update(changes)
    return record


def complete_record():
    """A hypothetical author-labelled record, not actual test evidence."""
    checks = [
        ("unit", "python-stdlib"),
        ("browser", "browser-small"),
        ("native-ui", "simulator-standard"),
        ("device-ui", "device-a-standard"),
        ("message-receipt", "recipient-a"),
        ("platform-version", "experience-channel"),
    ]
    return {
        "schema_version": 1,
        "mode": "observed",
        "artifact": {"version": "demo-v2", "digest": "DEMO_BUILD_A"},
        "claims": [{"scenario": "submit-and-receive", "checks": [
            {"kind": kind, "environment": environment} for kind, environment in checks
        ]}],
        "evidence": [observation(f"check-{index}", kind, environment)
                     for index, (kind, environment) in enumerate(checks)],
        "upload_state": {
            "status": "succeeded", "version": "demo-v2", "digest": "DEMO_BUILD_A",
            "observed_at": "2025-01-02T10:00:00Z", "origin": "observed",
        },
        "experience_state": {
            "status": "verified", "version": "demo-v2", "digest": "DEMO_BUILD_A",
            "observed_at": "2025-01-02T10:06:00Z", "origin": "observed",
            "evidence_id": "check-5",
        },
        "notes": "Hypothetical labels for checker tests only; no real release is asserted.",
    }


class EvidenceTests(unittest.TestCase):
    def assert_unready(self, record, issue=None):
        report = checker.evaluate(record)
        self.assertTrue(report["valid"])
        self.assertFalse(report["release_ready"])
        self.assertEqual(report["exit_code"], 2)
        if issue:
            self.assertIn(issue, report["release_issues"])
        return report

    def test_complete_observed_labels_satisfy_record_logic_only(self):
        report = checker.evaluate(complete_record())
        self.assertTrue(report["release_ready"])
        self.assertEqual(report["exit_code"], 0)
        self.assertIn("does not authenticate", report["scope_disclaimer"])
        self.assertIn("prove that real tests occurred", report["scope_disclaimer"])

    def test_browser_success_does_not_cover_missing_native_ui(self):
        record = complete_record()
        record["evidence"] = [item for item in record["evidence"] if item["kind"] != "native-ui"]
        report = self.assert_unready(record, "claim_checks_not_satisfied")
        native = next(item for item in report["checks"] if item["kind"] == "native-ui")
        self.assertEqual(native["status"], "missing")
        self.assertEqual(native["evidence_ids"], [])

    def test_device_success_does_not_substitute_for_message_receipt(self):
        record = complete_record()
        record["evidence"] = [item for item in record["evidence"] if item["kind"] != "message-receipt"]
        self.assert_unready(record, "claim_checks_not_satisfied")

    def test_environment_matching_is_exact_for_model_and_reading_mode(self):
        for environment in ("device-b-standard", "device-a-large", "Device-a-standard"):
            with self.subTest(environment=environment):
                record = complete_record()
                record["evidence"][3]["environment"] = environment
                self.assert_unready(record, "claim_checks_not_satisfied")

    def test_other_scenario_cannot_cover_this_scenario(self):
        record = complete_record()
        record["evidence"][3]["scenario"] = "edit-profile"
        self.assert_unready(record, "claim_checks_not_satisfied")

    def test_wrong_version_or_digest_cannot_cover_current_artifact(self):
        for field, value in (("version", "demo-v1"), ("digest", "DEMO_BUILD_B")):
            with self.subTest(field=field):
                record = complete_record()
                record["evidence"][2][field] = value
                self.assert_unready(record, "claim_checks_not_satisfied")

    def test_newer_current_pass_replaces_old_failure_even_if_old_arrives_last(self):
        record = complete_record()
        record["evidence"].append(observation(
            "late-arriving-old-failure", "native-ui", "simulator-standard",
            result="failed", observed_at="2025-01-02T09:00:00Z",
        ))
        report = checker.evaluate(record)
        self.assertTrue(report["release_ready"])
        native = next(item for item in report["checks"] if item["kind"] == "native-ui")
        self.assertEqual(native["evidence_ids"], ["check-2"])

    def test_newer_failure_blocks_an_older_pass_regardless_of_list_order(self):
        for insert_at in (0, 6):
            with self.subTest(insert_at=insert_at):
                record = complete_record()
                record["evidence"].insert(insert_at, observation(
                    "latest-failure", "native-ui", "simulator-standard",
                    result="failed", observed_at="2025-01-02T10:10:00Z",
                ))
                report = self.assert_unready(record, "claim_checks_not_satisfied")
                native = next(item for item in report["checks"] if item["kind"] == "native-ui")
                self.assertEqual(native["status"], "failed")

    def test_pending_and_not_tested_do_not_fall_back_to_an_older_pass(self):
        for result in ("pending", "not-tested"):
            with self.subTest(result=result):
                record = complete_record()
                record["evidence"].append(observation(
                    "newer-result", "native-ui", "simulator-standard", result=result,
                    observed_at="2025-01-02T10:10:00Z",
                ))
                self.assert_unready(record, "claim_checks_not_satisfied")

    def test_newer_evidence_for_a_different_artifact_does_not_override_current(self):
        record = complete_record()
        record["evidence"].append(observation(
            "other-build", "native-ui", "simulator-standard", digest="DEMO_BUILD_B",
            observed_at="2025-01-02T11:00:00Z", result="failed",
        ))
        self.assertTrue(checker.evaluate(record)["release_ready"])

    def test_timezone_comparison_uses_instant_not_text_order(self):
        record = complete_record()
        record["evidence"].append(observation(
            "older-offset", "native-ui", "simulator-standard", result="failed",
            observed_at="2025-01-02T11:00:00+02:00",
        ))
        self.assertTrue(checker.evaluate(record)["release_ready"])

    def test_equal_latest_timestamp_with_conflicting_results_is_ambiguous(self):
        record = complete_record()
        record["evidence"].append(observation(
            "conflicting-result", "native-ui", "simulator-standard", result="failed",
        ))
        report = self.assert_unready(record)
        native = next(item for item in report["checks"] if item["kind"] == "native-ui")
        self.assertEqual(native["status"], "ambiguous")

    def test_demo_mode_never_reports_true_release_ready(self):
        record = complete_record()
        record["mode"] = "demo"
        self.assert_unready(record, "demonstration_record")

    def test_any_synthetic_observation_blocks_true_release_ready_even_if_unclaimed(self):
        record = complete_record()
        record["evidence"].append(observation(
            "extra-demo", "browser", "browser-wide", scenario="unclaimed-demo", origin="synthetic",
        ))
        self.assert_unready(record, "synthetic_records_present")

    def test_synthetic_state_blocks_true_release_ready(self):
        for state in ("upload_state", "experience_state"):
            with self.subTest(state=state):
                record = complete_record()
                record[state]["origin"] = "synthetic"
                self.assert_unready(record, "synthetic_records_present")

    def test_unknown_pending_failed_or_not_started_upload_is_not_ready(self):
        for status in ("unknown", "pending", "failed", "not-started"):
            with self.subTest(status=status):
                record = complete_record()
                record["upload_state"] = {"status": status}
                self.assert_unready(record, "upload_not_succeeded")

    def test_experience_state_requires_verified_status(self):
        for status in ("unknown", "not-tested", "pending", "failed"):
            with self.subTest(status=status):
                record = complete_record()
                record["experience_state"] = {"status": status}
                self.assert_unready(record, "experience_not_verified")

    def test_release_states_must_match_current_version_and_digest(self):
        for state, issue in (("upload_state", "upload_artifact_mismatch"),
                             ("experience_state", "experience_artifact_mismatch")):
            for field, value in (("version", "demo-v1"), ("digest", "DEMO_BUILD_B")):
                with self.subTest(state=state, field=field):
                    record = complete_record()
                    record[state][field] = value
                    self.assert_unready(record, issue)

    def test_verified_experience_must_reference_platform_version_evidence(self):
        for evidence_id, issue in (("unknown-check", "experience_platform_evidence_missing"),
                                   ("check-1", "experience_platform_evidence_not_satisfied")):
            with self.subTest(evidence_id=evidence_id):
                record = complete_record()
                record["experience_state"]["evidence_id"] = evidence_id
                self.assert_unready(record, issue)

    def test_newer_platform_failure_invalidates_old_verified_reference(self):
        record = complete_record()
        record["evidence"].append(observation(
            "newer-platform-failure", "platform-version", "experience-channel",
            result="failed", observed_at="2025-01-02T10:08:00Z",
        ))
        self.assert_unready(record, "experience_platform_evidence_superseded")

    def test_platform_verification_before_upload_is_stale(self):
        record = complete_record()
        record["upload_state"]["observed_at"] = "2025-01-02T10:10:00Z"
        self.assert_unready(record, "platform_verification_precedes_upload")

    def test_experience_confirmation_cannot_precede_its_referenced_evidence(self):
        record = complete_record()
        record["experience_state"]["observed_at"] = "2025-01-02T10:04:00Z"
        self.assert_unready(record, "experience_state_precedes_its_evidence")

    def test_valid_incomplete_record_is_exit_two_not_invalid(self):
        record = complete_record()
        record["evidence"] = []
        record["upload_state"] = {"status": "not-started"}
        record["experience_state"] = {"status": "not-tested"}
        self.assert_unready(record)

    def test_malformed_or_timezone_less_timestamps_are_invalid(self):
        for value in ("later", "2025-01-02T10:05:00", "2025-02-30T10:05:00Z",
                      "0001-01-01T00:00:00+23:00"):
            with self.subTest(value=value):
                record = complete_record()
                record["evidence"][0]["observed_at"] = value
                with self.assertRaises(checker.RecordError):
                    checker.evaluate(record)

    def test_incomplete_structure_and_success_without_proof_are_invalid(self):
        variants = []
        for key in ("artifact", "claims", "evidence", "upload_state", "experience_state"):
            record = complete_record()
            del record[key]
            variants.append(record)
        record = complete_record()
        del record["evidence"][0]["origin"]
        variants.append(record)
        for state, success in (("upload_state", "succeeded"), ("experience_state", "verified")):
            record = complete_record()
            record[state] = {"status": success}
            variants.append(record)
        for record in variants:
            with self.subTest(record=record):
                with self.assertRaises(checker.RecordError):
                    checker.evaluate(record)

    def test_unknown_kind_duplicate_id_and_duplicate_checks_are_invalid(self):
        record = complete_record()
        record["evidence"][0]["kind"] = "all-tests"
        with self.assertRaises(checker.RecordError):
            checker.evaluate(record)
        record = complete_record()
        record["evidence"].append(deepcopy(record["evidence"][0]))
        with self.assertRaises(checker.RecordError):
            checker.evaluate(record)
        record = complete_record()
        record["claims"][0]["checks"].append(deepcopy(record["claims"][0]["checks"][0]))
        with self.assertRaises(checker.RecordError):
            checker.evaluate(record)

    def test_cli_exit_codes_and_read_only_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            for mode, expected in (("observed", 0), ("demo", 2)):
                record = complete_record()
                record["mode"] = mode
                original = json.dumps(record).encode("utf-8")
                path.write_bytes(original)
                result = subprocess.run([sys.executable, str(SCRIPT), str(path)],
                                        capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertEqual(json.loads(result.stdout)["exit_code"], expected)
                self.assertEqual(path.read_bytes(), original)
            path.write_text("not JSON", encoding="utf-8")
            result = subprocess.run([sys.executable, str(SCRIPT), str(path)],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(json.loads(result.stdout)["valid"])

    def test_duplicate_json_keys_are_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            path.write_text('{"artifact": {}, "artifact": {}}', encoding="utf-8")
            result = subprocess.run([sys.executable, str(SCRIPT), str(path)],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("duplicate", json.loads(result.stdout)["errors"][0])

    def test_missing_or_unsupported_cli_arguments_are_invalid_input(self):
        for args in ([], ["--unexpected-option"]):
            with self.subTest(args=args):
                result = subprocess.run([sys.executable, str(SCRIPT)] + args,
                                        capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(json.loads(result.stdout)["status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
