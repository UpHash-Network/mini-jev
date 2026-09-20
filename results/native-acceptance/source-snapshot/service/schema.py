"""Strict JSON boundary shared by the HTTP server and Python SDK."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class Limits:
    max_body_bytes: int = 131072
    max_questions: int = 8
    max_text_chars: int = 32768
    max_key_chars: int = 128
    max_depth: int = 32


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError("duplicate JSON object key")
        result[key] = value
    return result


def decode_json(raw: bytes | str):
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw, object_pairs_hook=_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(
                              ValidationError("non-finite JSON numbers are not allowed")))
    except ValidationError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise ValidationError("body must contain valid UTF-8 JSON") from None


def _fields(value, allowed, required, path):
    if not isinstance(value, dict):
        raise ValidationError(f"{path} must be an object")
    if set(value) - set(allowed):
        raise ValidationError(f"{path} contains an unknown field")
    if set(required) - set(value):
        raise ValidationError(f"{path} is missing a required field")


def _text(value, path, maximum):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValidationError(f"{path} must be a non-empty string of at most {maximum} characters")


def _json_value(value, limits: Limits, depth=0):
    if depth > limits.max_depth:
        raise ValidationError("state is nested too deeply")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValidationError("state object keys must be strings")
            _json_value(item, limits, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _json_value(item, limits, depth + 1)
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise ValidationError("state numbers must be finite")
    elif value is not None and not isinstance(value, (str, int, bool)):
        raise ValidationError("state must contain JSON values only")


def validate_request(payload: Any, limits: Limits = Limits(), active_model: str | None = None):
    _fields(payload, ("state", "questions", "model"), ("state", "questions"), "request")
    state = payload["state"]
    if not isinstance(state, (str, dict, list)):
        raise ValidationError("state must be a string, object, or array")
    _json_value(state, limits)
    if isinstance(state, str) and len(state) > limits.max_text_chars:
        raise ValidationError("state exceeds the character limit")
    if "model" in payload:
        _text(payload["model"], "model", 256)
        if active_model is not None and payload["model"] != active_model:
            raise ValidationError("model must match the model loaded by this server")
    questions = payload["questions"]
    if not isinstance(questions, dict) or not 1 <= len(questions) <= limits.max_questions:
        raise ValidationError(f"questions must contain 1 to {limits.max_questions} entries")
    cases, identifiers = [], []
    for identifier, question in questions.items():
        _text(identifier, "question identifier", limits.max_key_chars)
        _fields(question, ("type", "instructions", "criteria"), ("type", "instructions"), "question")
        kind = question["type"]
        if kind not in ("choice", "noul", "score"):
            raise ValidationError("question type must be choice, noul, or score")
        _text(question["instructions"], "instructions", limits.max_text_chars)
        criteria = question.get("criteria")
        if kind == "noul":
            if "criteria" not in question:
                criteria = {"false": "いいえ", "true": "はい"}
            if not isinstance(criteria, dict) or set(criteria) != {"false", "true"}:
                raise ValidationError("noul criteria must contain exactly false and true")
            criteria = {key: criteria[key] for key in ("false", "true")}
        elif kind == "choice":
            if not isinstance(criteria, dict) or not 2 <= len(criteria) <= 26:
                raise ValidationError("choice criteria must contain 2 to 26 entries")
        else:
            if not isinstance(criteria, list) or not 2 <= len(criteria) <= 26:
                raise ValidationError("score criteria must be an ordered array of 2 to 26 descriptions")
        if isinstance(criteria, dict):
            for key in criteria:
                _text(key, "criterion key", limits.max_key_chars)
            descriptions = criteria.values()
        else:
            descriptions = criteria
        for description in descriptions:
            _text(description, "criterion description", limits.max_text_chars)
        # Identifiers are for output routing only. They never enter model cases.
        cases.append({"state": state, "type": kind, "instructions": question["instructions"], "criteria": criteria})
        identifiers.append(identifier)
    try:
        size = len(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8"))
    except (ValueError, UnicodeError, RecursionError):
        raise ValidationError("request must contain valid JSON values") from None
    if size > limits.max_body_bytes:
        raise ValidationError("request exceeds the encoded size limit")
    return identifiers, cases


def _number(value):
    try:
        return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def public_answer(result: Any, case: dict):
    """Check the backend result before releasing its small typed public surface."""
    kind = case["type"]
    keys = (list(case["criteria"]) if kind != "score"
            else [str(i) for i in range(len(case["criteria"]))])
    if not isinstance(result, dict) or result.get("type") != kind:
        raise ValidationError("backend returned an invalid answer type")
    probabilities = result.get("probabilities")
    if not isinstance(probabilities, dict) or set(probabilities) != set(keys):
        raise ValidationError("backend returned invalid candidate keys")
    if any(not _number(p) or not 0 <= p <= 1 for p in probabilities.values()):
        raise ValidationError("backend returned invalid probabilities")
    if abs(sum(probabilities.values()) - 1) > 1e-5:
        raise ValidationError("backend probabilities must sum to one")
    label = result.get("label")
    if not isinstance(label, str) or label not in keys or probabilities[label] != max(probabilities.values()):
        raise ValidationError("backend label must be a most probable candidate")
    calibrated = result.get("calibrated")
    semantics = result.get("probability_semantics")
    if not isinstance(calibrated, bool) or not isinstance(semantics, str) or not semantics:
        raise ValidationError("backend must specify probability semantics and calibration status")
    expected = label if kind == "choice" else (
        probabilities["true"] if kind == "noul" else
        sum(i * probabilities[str(i)] for i in range(len(keys))))
    value = result.get(kind)
    if kind == "choice":
        valid_value = value == expected
    else:
        valid_value = _number(value) and abs(value - expected) < 1e-5
    if not valid_value:
        raise ValidationError("backend returned an inconsistent typed value")
    answer = {"type": kind, "label": label, "probabilities": probabilities,
              "calibrated": calibrated, "probability_semantics": semantics, kind: value}
    if kind == "score":
        legend = {str(index): description for index, description in enumerate(case["criteria"])}
        if "legend" in result and result["legend"] != legend:
            raise ValidationError("backend score legend does not match the requested criteria")
        answer["legend"] = legend
    if "confidence" in result or "confidence_definition" in result:
        confidence, definition = result.get("confidence"), result.get("confidence_definition")
        if (not _number(confidence) or not 0 <= confidence <= 1
                or definition != "one_minus_normalized_entropy_not_probability_of_correctness"):
            raise ValidationError("backend returned invalid confidence metadata")
        expected_confidence = 1 + sum(p * math.log(p) for p in probabilities.values() if p > 0) / math.log(len(keys))
        if abs(confidence - expected_confidence) > 1e-5:
            raise ValidationError("backend confidence does not match the probability distribution")
        answer.update(confidence=confidence, confidence_definition=definition)
    for field in ("temperature_calibration_applied", "calibration_generalization_validated"):
        if field in result:
            if type(result[field]) is not bool:
                raise ValidationError("backend calibration metadata must be boolean")
            answer[field] = result[field]
    return answer


def validate_response(payload, identifiers, cases, active_model=None):
    _fields(payload, ("model", "answers", "usage", "latency_ms", "request_id"),
            ("model", "answers", "usage", "latency_ms", "request_id"), "response")
    _text(payload["model"], "response model", 256)
    if active_model is not None and payload["model"] != active_model:
        raise ValidationError("response model does not match requested model")
    _text(payload["request_id"], "request_id", 128)
    if not _number(payload["latency_ms"]) or payload["latency_ms"] < 0:
        raise ValidationError("response latency_ms must be finite and nonnegative")
    answers, usage = payload["answers"], payload["usage"]
    if not isinstance(answers, dict) or set(answers) != set(identifiers):
        raise ValidationError("response answer identifiers do not match the questions")
    for identifier, case in zip(identifiers, cases):
        expected_fields = {"type", "label", "probabilities", "calibrated", "probability_semantics", case["type"]}
        if case["type"] == "score":
            expected_fields.add("legend")
        _fields(answers[identifier], expected_fields | {
            "confidence", "confidence_definition", "temperature_calibration_applied",
            "calibration_generalization_validated"}, expected_fields, "answer")
        public_answer(answers[identifier], case)
    _fields(usage, ("input_tokens", "output_tokens", "questions"),
            ("input_tokens", "output_tokens", "questions"), "usage")
    if any(type(value) is not int or value < 0 for value in usage.values()):
        raise ValidationError("usage values must be nonnegative integers")
    if usage["questions"] != len(cases) or usage["output_tokens"] != 0:
        raise ValidationError("usage must match the direct-decision request")
    return payload
