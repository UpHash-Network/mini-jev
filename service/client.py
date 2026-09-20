"""Dependency-free, strictly validated SDK for the local MiniJev service."""
from __future__ import annotations

import ipaddress
import json
import math
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Mapping

from .schema import Limits, ValidationError, decode_json, validate_request, validate_response


@dataclass(frozen=True)
class Choice:
    instructions: str
    criteria: Mapping[str, str]

    def to_dict(self):
        return {"type": "choice", "instructions": self.instructions, "criteria": dict(self.criteria)}


@dataclass(frozen=True)
class Noul:
    instructions: str
    criteria: Mapping[str, str] | None = None

    def to_dict(self):
        result = {"type": "noul", "instructions": self.instructions}
        if self.criteria is not None:
            result["criteria"] = dict(self.criteria)
        return result


@dataclass(frozen=True)
class Score:
    instructions: str
    criteria: list[str] | tuple[str, ...]

    def to_dict(self):
        return {"type": "score", "instructions": self.instructions, "criteria": list(self.criteria)}


@dataclass(frozen=True, kw_only=True)
class Answer:
    type: str
    label: str
    probabilities: dict[str, float]
    calibrated: bool
    probability_semantics: str
    confidence: float | None = None
    confidence_definition: str | None = None
    temperature_calibration_applied: bool | None = None
    calibration_generalization_validated: bool | None = None


@dataclass(frozen=True)
class ChoiceAnswer(Answer):
    choice: str


@dataclass(frozen=True)
class NoulAnswer(Answer):
    noul: float


@dataclass(frozen=True)
class ScoreAnswer(Answer):
    score: float
    legend: dict[str, str]


@dataclass(frozen=True)
class SystemOneResponse:
    model: str
    answers: dict[str, ChoiceAnswer | NoulAnswer | ScoreAnswer]
    usage: dict[str, int]
    latency_ms: float
    request_id: str

    @property
    def choices(self) -> dict[str, ChoiceAnswer]:
        return {key: value for key, value in self.answers.items() if isinstance(value, ChoiceAnswer)}

    @property
    def nouls(self) -> dict[str, NoulAnswer]:
        return {key: value for key, value in self.answers.items() if isinstance(value, NoulAnswer)}

    @property
    def scores(self) -> dict[str, ScoreAnswer]:
        return {key: value for key, value in self.answers.items() if isinstance(value, ScoreAnswer)}


class APIError(RuntimeError):
    def __init__(self, status: int, code: str, message: str, request_id: str | None = None):
        self.status, self.code, self.request_id = status, code, request_id
        super().__init__(f"HTTP {status} {code}: {message}")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, base_url="http://127.0.0.1:8765", *, timeout=35.0,
                 limits=Limits(), max_response_bytes=262144):
        parsed = urllib.parse.urlsplit(base_url)
        host = parsed.hostname
        try:
            port = parsed.port
        except ValueError:
            raise ValueError("base_url must specify a valid port") from None
        try:
            loopback = host == "localhost" or ipaddress.ip_address(host).is_loopback
        except (ValueError, TypeError):
            loopback = False
        if (parsed.scheme != "http" or not loopback or parsed.username or parsed.password
                or parsed.query or parsed.fragment or parsed.path not in ("", "/")
                or port == 0):
            raise ValueError("base_url must be an HTTP loopback origin without a path or credentials")
        if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        if type(max_response_bytes) is not int or max_response_bytes < 1:
            raise ValueError("max_response_bytes must be a positive integer")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.limits = limits
        self.max_response_bytes = max_response_bytes
        self._closed = False
        # Local prompts must not pass through a proxy configured in the shell.
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())

    def __enter__(self):
        if self._closed:
            raise RuntimeError("client is closed")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        """Stop accepting requests; each HTTP connection is already scoped to its call."""
        self._closed = True

    def _request(self, path, payload=None):
        if self._closed:
            raise RuntimeError("client is closed")
        data = None if payload is None else json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        request = urllib.request.Request(self.base_url + path, data=data,
                                         headers={"Content-Type": "application/json", "Accept": "application/json"})
        try:
            response = self._opener.open(request, timeout=self.timeout)
        except urllib.error.HTTPError as exc:
            with exc:
                raw = exc.read(self.max_response_bytes + 1)
                if len(raw) > self.max_response_bytes:
                    raise APIError(exc.code, "invalid_error", "error response exceeds size limit") from None
                try:
                    body = decode_json(raw)
                    error = body["error"]
                    if not isinstance(error["code"], str) or not isinstance(error["message"], str):
                        raise ValueError()
                    raise APIError(exc.code, error["code"], error["message"], body.get("request_id")) from None
                except (ValidationError, KeyError, TypeError, ValueError):
                    raise APIError(exc.code, "invalid_error", "server returned an invalid error response") from None
        with response:
            if response.headers.get_content_type() != "application/json":
                raise ValidationError("server response is not JSON")
            raw = response.read(self.max_response_bytes + 1)
            if len(raw) > self.max_response_bytes:
                raise ValidationError("server response exceeds size limit")
            return decode_json(raw)

    def health(self):
        result = self._request("/health")
        if (not isinstance(result, dict) or type(result.get("ready")) is not bool
                or not isinstance(result.get("model"), str)):
            raise ValidationError("invalid health response")
        return result

    def system_one(self, state: str | dict | list,
                   questions: Mapping[str, Choice | Noul | Score | dict], *, model=None):
        if not isinstance(questions, Mapping):
            raise ValidationError("questions must be a mapping")
        raw_questions = {key: value.to_dict() if isinstance(value, (Choice, Noul, Score)) else value
                         for key, value in questions.items()}
        payload = {"state": state, "questions": raw_questions}
        if model is not None:
            payload["model"] = model
        identifiers, cases = validate_request(payload, self.limits)
        body = validate_response(self._request("/v1/systemone", payload), identifiers, cases, model)
        answer_classes = {"choice": ChoiceAnswer, "noul": NoulAnswer, "score": ScoreAnswer}
        answers = {key: answer_classes[value["type"]](**value) for key, value in body["answers"].items()}
        return SystemOneResponse(model=body["model"], answers=answers, usage=body["usage"],
                                 latency_ms=body["latency_ms"], request_id=body["request_id"])
