#!/usr/bin/env python3
"""Check an evidence record, without testing a product or performing an upload.

Exit codes: 0 = record-level release conditions satisfied; 2 = a valid record is
incomplete, failed, pending, or a demonstration; 1 = invalid input. An ``observed``
label is supplied by the author: this program cannot authenticate that label.

Required root fields are artifact, claims, evidence, upload_state, and
experience_state. Optional mode is "observed" (default) or "demo". Each claim has
a scenario and a nonempty checks list of exact kind/environment pairs. Evidence
uses the same pair, the current artifact's version/digest, a unique id, result,
timezone-aware observed_at, and origin. See the module constants for enum values.

Successful upload/experience states additionally require version, digest,
observed_at, and origin. A verified experience also requires evidence_id pointing
to a passed, observed platform-version record. Unknown or pending states may
contain just status. Observations are compared by time, never by list order.
There is no implicit maximum age: add expiry policy separately if one is needed.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys


KINDS = frozenset({
    "unit", "browser", "native-ui", "device-ui", "message-receipt",
    "platform-version",
})
RESULTS = frozenset({"passed", "failed", "pending", "not-tested"})
ORIGINS = frozenset({"observed", "synthetic"})
UPLOAD_STATUSES = frozenset({"unknown", "not-started", "pending", "failed", "succeeded"})
EXPERIENCE_STATUSES = frozenset({"unknown", "not-tested", "pending", "failed", "verified"})
SCOPE_DISCLAIMER = (
    "This checks record structure and internal consistency only. It does not "
    "authenticate observations, prove that real tests occurred, or perform any "
    "upload, retry, platform operation, or network request."
)
TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$"
)


class RecordError(ValueError):
    """An input does not conform to the evidence record's structure."""


def _object(value, location):
    if not isinstance(value, dict):
        raise RecordError(f"{location} must be an object")
    return value


def _fields(value, required, optional, location):
    _object(value, location)
    if not required.issubset(value):
        raise RecordError(f"{location} is missing required fields")
    if set(value) - required - optional:
        raise RecordError(f"{location} contains unsupported fields")


def _text(value, location):
    if not isinstance(value, str) or not value or value != value.strip():
        raise RecordError(f"{location} must be a nonempty string without edge whitespace")
    return value


def _enum(value, allowed, location):
    if not isinstance(value, str) or value not in allowed:
        raise RecordError(f"{location} has an unsupported value")
    return value


def _time(value, location):
    if not isinstance(value, str) or not TIMESTAMP.fullmatch(value):
        raise RecordError(f"{location} must be an RFC3339 timestamp with a timezone")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, OverflowError) as error:
        raise RecordError(f"{location} is not a valid timestamp") from error


def _state(value, name, statuses, success):
    _fields(value, {"status"}, {
        "version", "digest", "observed_at", "origin", "evidence_id", "notes",
    }, name)
    _enum(value["status"], statuses, f"{name}.status")
    for key in ("version", "digest", "evidence_id"):
        if key in value:
            _text(value[key], f"{name}.{key}")
    if "observed_at" in value:
        _time(value["observed_at"], f"{name}.observed_at")
    if "origin" in value:
        _enum(value["origin"], ORIGINS, f"{name}.origin")
    if "notes" in value and not isinstance(value["notes"], str):
        raise RecordError(f"{name}.notes must be a string")
    if value["status"] == success:
        required = {"version", "digest", "observed_at", "origin"}
        if name == "experience_state":
            required.add("evidence_id")
        if not required.issubset(value):
            raise RecordError(f"{name} success requires artifact and observation fields")


def validate(record):
    """Validate structure; a valid record can still be unready for release."""
    _fields(record, {
        "artifact", "claims", "evidence", "upload_state", "experience_state",
    }, {"schema_version", "mode", "notes"}, "record")
    if "schema_version" in record and (
        type(record["schema_version"]) is not int or record["schema_version"] != 1
    ):
        raise RecordError("record.schema_version must be 1")
    _enum(record.get("mode", "observed"), {"observed", "demo"}, "record.mode")
    if "notes" in record and not isinstance(record["notes"], str):
        raise RecordError("record.notes must be a string")
    _fields(record["artifact"], {"version", "digest"}, set(), "artifact")
    for key in ("version", "digest"):
        _text(record["artifact"][key], f"artifact.{key}")

    claims = record["claims"]
    if not isinstance(claims, list) or not claims:
        raise RecordError("claims must be a nonempty list")
    seen_scenarios = set()
    for index, claim in enumerate(claims):
        location = f"claims[{index}]"
        _fields(claim, {"scenario", "checks"}, set(), location)
        scenario = _text(claim["scenario"], f"{location}.scenario")
        if scenario in seen_scenarios:
            raise RecordError("claims contains a duplicate scenario")
        seen_scenarios.add(scenario)
        if not isinstance(claim["checks"], list) or not claim["checks"]:
            raise RecordError(f"{location}.checks must be a nonempty list")
        seen_checks = set()
        for check in claim["checks"]:
            _fields(check, {"kind", "environment"}, set(), f"{location}.checks item")
            _enum(check["kind"], KINDS, f"{location}.checks.kind")
            _text(check["environment"], f"{location}.checks.environment")
            pair = (check["kind"], check["environment"])
            if pair in seen_checks:
                raise RecordError(f"{location}.checks contains a duplicate pair")
            seen_checks.add(pair)

    evidence = record["evidence"]
    if not isinstance(evidence, list):
        raise RecordError("evidence must be a list")
    ids = set()
    for index, observation in enumerate(evidence):
        location = f"evidence[{index}]"
        _fields(observation, {
            "id", "scenario", "kind", "environment", "version", "digest",
            "result", "observed_at", "origin",
        }, {"notes"}, location)
        for key in ("id", "scenario", "environment", "version", "digest"):
            _text(observation[key], f"{location}.{key}")
        if observation["id"] in ids:
            raise RecordError("evidence contains a duplicate id")
        ids.add(observation["id"])
        _enum(observation["kind"], KINDS, f"{location}.kind")
        _enum(observation["result"], RESULTS, f"{location}.result")
        _enum(observation["origin"], ORIGINS, f"{location}.origin")
        _time(observation["observed_at"], f"{location}.observed_at")
        if "notes" in observation and not isinstance(observation["notes"], str):
            raise RecordError(f"{location}.notes must be a string")
    _state(record["upload_state"], "upload_state", UPLOAD_STATUSES, "succeeded")
    _state(record["experience_state"], "experience_state", EXPERIENCE_STATUSES, "verified")


def _current(observation, artifact):
    return all(observation.get(key) == artifact[key] for key in ("version", "digest"))


def _latest(record, scenario, kind, environment):
    candidates = [item for item in record["evidence"] if (
        _current(item, record["artifact"])
        and (item["scenario"], item["kind"], item["environment"])
        == (scenario, kind, environment)
    )]
    if not candidates:
        return []
    newest = max(_time(item["observed_at"], "observed_at") for item in candidates)
    return sorted(
        (item for item in candidates if _time(item["observed_at"], "observed_at") == newest),
        key=lambda item: item["id"],
    )


def _check(record, scenario, kind, environment):
    latest = _latest(record, scenario, kind, environment)
    result = {
        "scenario": scenario, "kind": kind, "environment": environment,
        "evidence_ids": [item["id"] for item in latest],
    }
    if not latest:
        result["status"] = "missing"
    elif len({(item["result"], item["origin"]) for item in latest}) > 1:
        result["status"] = "ambiguous"
    elif latest[0]["origin"] != "observed":
        result["status"] = "synthetic"
    elif latest[0]["result"] != "passed":
        result["status"] = latest[0]["result"]
    else:
        result["status"] = "passed"
    return result


def evaluate(record):
    """Return a deterministic report. Raises RecordError for invalid input."""
    validate(record)
    checks = [
        _check(record, claim["scenario"], check["kind"], check["environment"])
        for claim in record["claims"] for check in claim["checks"]
    ]
    issues = []
    if any(check["status"] != "passed" for check in checks):
        issues.append("claim_checks_not_satisfied")
    if record.get("mode", "observed") == "demo":
        issues.append("demonstration_record")
    states = (record["upload_state"], record["experience_state"])
    if any(item.get("origin") == "synthetic" for item in record["evidence"] + list(states)):
        issues.append("synthetic_records_present")

    upload, experience = states
    if upload["status"] != "succeeded":
        issues.append("upload_not_succeeded")
    elif not _current(upload, record["artifact"]):
        issues.append("upload_artifact_mismatch")
    if experience["status"] != "verified":
        issues.append("experience_not_verified")
    elif not _current(experience, record["artifact"]):
        issues.append("experience_artifact_mismatch")
    else:
        reference = next((item for item in record["evidence"]
                          if item["id"] == experience["evidence_id"]), None)
        if reference is None:
            issues.append("experience_platform_evidence_missing")
        elif (reference["kind"] != "platform-version"
              or reference["result"] != "passed"
              or reference["origin"] != "observed"
              or not _current(reference, record["artifact"])):
            issues.append("experience_platform_evidence_not_satisfied")
        else:
            latest = _latest(record, reference["scenario"], reference["kind"], reference["environment"])
            latest_check = _check(record, reference["scenario"], reference["kind"], reference["environment"])
            if reference["id"] not in {item["id"] for item in latest} or latest_check["status"] != "passed":
                issues.append("experience_platform_evidence_superseded")
            reference_time = _time(reference["observed_at"], "observed_at")
            experience_time = _time(experience["observed_at"], "observed_at")
            if experience_time < reference_time:
                issues.append("experience_state_precedes_its_evidence")
            if upload["status"] == "succeeded":
                upload_time = _time(upload["observed_at"], "observed_at")
                if reference_time < upload_time or experience_time < upload_time:
                    issues.append("platform_verification_precedes_upload")

    ready = not issues
    return {
        "valid": True,
        "release_ready": ready,
        "status": "record_conditions_satisfied" if ready else "needs_verification",
        "exit_code": 0 if ready else 2,
        "checks": checks,
        "release_issues": issues,
        "scope_disclaimer": SCOPE_DISCLAIMER,
    }


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RecordError("JSON contains a duplicate object key")
        result[key] = value
    return result


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise RecordError("Expected exactly one local JSON record path")


def main(argv=None):
    parser = _ArgumentParser(description=__doc__)
    parser.add_argument("record", help="A local JSON evidence record (read only)")
    try:
        args = parser.parse_args(argv)
        with Path(args.record).open("r", encoding="utf-8-sig") as stream:
            record = json.load(stream, object_pairs_hook=_unique_object)
        report = evaluate(record)
    except (OSError, UnicodeError, json.JSONDecodeError, RecordError) as error:
        message = str(error) if isinstance(error, RecordError) else "Cannot read a valid UTF-8 JSON record"
        report = {
            "valid": False, "release_ready": False, "status": "invalid_input",
            "exit_code": 1, "errors": [message], "scope_disclaimer": SCOPE_DISCLAIMER,
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
