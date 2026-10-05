#!/usr/bin/env python3
"""Verify a saved aggregation replay without changing any frozen analysis files."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ARTIFACTS = frozenset(("RESULTS.json", "records.jsonl", "REPORT.md"))
TOLERANCE = 1e-12
EXPECTED_RECORDS = 960


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON key: " + key)
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError("Nonfinite JSON constant: " + value)


def parse_json(raw):
    return json.loads(raw, object_pairs_hook=unique_object, parse_constant=invalid_constant)


def validate_finite(value, path):
    if type(value) is float:
        require(math.isfinite(value), "Nonfinite number at " + path)
    elif type(value) is dict:
        for key, child in value.items():
            validate_finite(child, path + "/" + key)
    elif type(value) is list:
        for index, child in enumerate(value):
            validate_finite(child, path + "/" + str(index))
    else:
        require(type(value) in (str, int, bool, type(None)), "Unsupported JSON type at " + path)


def compare(actual, expected, path, ignore_top_created_at=False):
    """Strict shapes/types, absolute tolerance for floats, exact other scalar values."""
    require(type(actual) is type(expected), "Type differs at " + path)
    if type(expected) is dict:
        require(actual.keys() == expected.keys(), "Keys differ at " + path)
        maximum = 0.0
        for key, reference in expected.items():
            if ignore_top_created_at and key == "created_at":
                require(type(actual[key]) is str and type(reference) is str,
                        "Creation timestamp must remain a string at " + path)
                continue
            maximum = max(maximum, compare(actual[key], reference, path + "/" + key))
        return maximum
    if type(expected) is list:
        require(len(actual) == len(expected), "List length differs at " + path)
        return max((compare(x, y, path + "/" + str(i))
                    for i, (x, y) in enumerate(zip(actual, expected))), default=0.0)
    if type(expected) is float:
        require(math.isfinite(actual) and math.isfinite(expected), "Nonfinite number at " + path)
        difference = abs(actual - expected)
        require(difference <= TOLERANCE, "Number differs beyond tolerance at " + path)
        return difference
    require(actual == expected, "Value differs at " + path)
    return 0.0


def verified_artifacts(folder, label):
    require(folder.is_dir(), label + " result directory missing")
    manifest = parse_json((folder / "MANIFEST.json").read_text(encoding="utf-8"))
    require(type(manifest) is dict and set(manifest) == {"files_sha256"}, label + " manifest shape differs")
    hashes = manifest["files_sha256"]
    require(type(hashes) is dict and set(hashes) == ARTIFACTS, label + " manifest artifact keys differ")
    blobs = {}
    for name, digest in hashes.items():
        require(type(digest) is str and re.fullmatch(r"[0-9a-f]{64}", digest) is not None,
                label + " manifest digest malformed for " + name)
        path = folder / name
        require(path.is_file() and not path.is_symlink(), label + " artifact missing or symbolic: " + name)
        raw = path.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == digest, label + " manifest hash differs for " + name)
        blobs[name] = raw
    results = parse_json(blobs["RESULTS.json"])
    require(type(results) is dict and "created_at" in results, label + " results shape differs")
    validate_finite(results, label + "/RESULTS.json")
    records = [parse_json(line) for line in blobs["records.jsonl"].decode("utf-8").splitlines()]
    require(len(records) == EXPECTED_RECORDS, label + " must contain exactly 960 item records")
    require(all(type(record) is dict for record in records), label + " record must be a JSON object")
    validate_finite(records, label + "/records.jsonl")
    return results, records, blobs["REPORT.md"]


def verify(actual, expected=HERE / "results"):
    expected_results, expected_records, expected_report = verified_artifacts(Path(expected), "expected")
    actual_results, actual_records, actual_report = verified_artifacts(Path(actual), "actual")
    maximum_results = compare(actual_results, expected_results, "RESULTS.json", ignore_top_created_at=True)
    maximum_records = compare(actual_records, expected_records, "records.jsonl")
    require(actual_report == expected_report, "REPORT.md differs byte-for-byte")
    return {"status": "passed", "verified_manifests": 2, "records_compared": EXPECTED_RECORDS,
            "absolute_numeric_tolerance": TOLERANCE, "strict_json_types": True,
            "ignored_value_paths": ["RESULTS.json/created_at"], "report_byte_identical": True,
            "maximum_results_absolute_difference": maximum_results,
            "maximum_records_absolute_difference": maximum_records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actual", type=Path, required=True)
    parser.add_argument("--expected", type=Path, default=HERE / "results")
    args = parser.parse_args()
    try:
        result = verify(args.actual, args.expected)
    except (OSError, ValueError, TypeError, UnicodeError) as error:
        parser.exit(1, "Replay verification failed: " + str(error) + "\n")
    print(json.dumps(result, allow_nan=False, sort_keys=True))


if __name__ == "__main__":
    main()
