"""Frozen prompt manipulations for the fixed external 600-item robustness study.

This module formats requests only. It never loads a model or performs inference.
Returned candidate_keys map the candidate-token vector back to baseline meanings.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import string
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from native_engine import NativeEngine, options_for

SEED = 2026092201
MAX_INPUT_TOKENS = 2048
EXPECTED_REQUEST_COUNT = 4000
CONDITIONS = (
    "baseline", "baseline_repeat", "display_reverse", "display_rotate",
    "label_reverse", "opaque_keys", "instruction_reword", "definition_reword",
)
EXPECTED_CONDITION_COUNTS = {
    "baseline": 600, "baseline_repeat": 600, "display_reverse": 600,
    "display_rotate": 400, "label_reverse": 400, "opaque_keys": 400,
    "instruction_reword": 600, "definition_reword": 400,
}
QUESTIONS_SHA256 = "4df650133880c935c885668b46b33d8d49c14fdb82b0703b4bf45e0bc297272b"
SOURCE_PROTOCOL_PATH = ROOT / "paper/external_expanded/PROTOCOL.json"
SOURCE_SELECTION_PATH = ROOT / "paper/external_expanded/SELECTION.json"
SOURCE_PROMPTS = json.loads(SOURCE_PROTOCOL_PATH.read_text(encoding="utf-8"))["prompts"]

# Fixed before any robustness inference; these are AI-authored hypotheses of
# semantic equivalence, not human-validated equivalence annotations.
INSTRUCTION_REWORD = {
    "JCoLA": "この文が日本語として文法的に容認できるかを判定してください。述べられた出来事の現実性ではなく、文の構造と語同士の結び付きに基づいて判断してください。",
    "JSTS": "文Aと文Bが意味の上でどれほど似ているか、0から5で評価してください。各段階の定義に従い、意味や話題に共通する点と、異なる点の重要性を判断してください。",
    "JCommonsenseQA": "一般的な知識と常識を用いて質問に答えてください。提示された選択肢のうち、最も適切な答えを一つ選んでください。",
}
DEFINITION_REWORD = {
    "JCoLA": {
        "false": "いいえ。この文は、日本語の文法上、容認できません。",
        "true": "はい。この文は、日本語の文法上、容認できます。",
    },
    "JSTS": [
        "意味にも、扱っている話題にも共通する点がない。",
        "同じ話題を扱っているが、意味は異なる。",
        "細かな要素の一部は共通しているが、意味は異なる。",
        "意味に重なる部分はあるが、重要な内容は異なる。",
        "意味はほぼ同じで、相違は重要ではない細部だけである。",
        "二つの文の意味は同じである。",
    ],
}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _validate_row(row):
    if not isinstance(row, dict):
        raise ValueError("row must be an object")
    dataset = row.get("dataset")
    if dataset not in SOURCE_PROMPTS:
        raise ValueError("unsupported dataset")
    spec = SOURCE_PROMPTS[dataset]
    for field in ("id", "state", "instructions"):
        if not isinstance(row.get(field), str) or not row[field].strip():
            raise ValueError("invalid row field: " + field)
    if row.get("type") != spec["type"]:
        raise ValueError("dataset/type mismatch")
    if row["instructions"] != spec["instructions"]:
        raise ValueError("unexpected source instructions")
    options = options_for(row)
    expected_keys = {
        "JCoLA": ["false", "true"],
        "JSTS": [str(i) for i in range(6)],
        "JCommonsenseQA": ["option_" + str(i) for i in range(5)],
    }[dataset]
    if [key for key, _ in options] != expected_keys:
        raise ValueError("unexpected option count or semantic keys")
    if dataset in DEFINITION_REWORD and row["criteria"] != spec["criteria"]:
        raise ValueError("unexpected source definitions")
    if dataset == "JSTS":
        gold = row.get("gold_score")
        if type(gold) not in (int, float) or not math.isfinite(gold) or not 0 <= gold <= 5:
            raise ValueError("invalid continuous JSTS gold_score")
        if "label" in row:
            raise ValueError("JSTS must not contain an invented discrete gold label")
    elif row.get("label") not in expected_keys:
        raise ValueError("invalid semantic gold label")
    return options


def verify_source(path, selection_path=SOURCE_SELECTION_PATH):
    """Verify frozen source bytes, ID/order/metadata and per-question hashes.

    The source file contains upstream text and must remain outside this repository.
    Returns its validated rows; callers must not write those rows into public output.
    """
    path = Path(path).resolve()
    if path.is_relative_to(ROOT):
        raise ValueError("source question text must remain outside the repository")
    raw = path.read_bytes()
    selection = json.loads(Path(selection_path).read_text(encoding="utf-8"))
    digest = hashlib.sha256(raw).hexdigest()
    if (digest != QUESTIONS_SHA256 or digest != selection["questions_sha256"]
            or len(raw) != selection["questions_bytes"]):
        raise ValueError("source question file hash/size mismatch")
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    if len(rows) != 600 or selection["count"] != 600 or len(selection["items"]) != 600:
        raise ValueError("expected exactly 600 selected questions")
    if len({row["id"] for row in rows}) != 600:
        raise ValueError("duplicate item IDs")
    for row, reference in zip(rows, selection["items"]):
        _validate_row(row)
        if hashlib.sha256(canonical(row).encode()).hexdigest() != reference["question_sha256"]:
            raise ValueError("question hash mismatch")
        for key in ("id", "dataset", "split", "type", "group"):
            if row.get(key) != reference.get(key):
                raise ValueError("selection metadata mismatch: " + key)
        gold_key = "gold_score" if row["type"] == "score" else "label"
        if row[gold_key] != reference[gold_key]:
            raise ValueError("gold metadata mismatch")
    if Counter(row["dataset"] for row in rows) != {
        "JCoLA": 200, "JSTS": 200, "JCommonsenseQA": 200,
    }:
        raise ValueError("unexpected per-dataset sample counts")
    if Counter((row["dataset"], row["split"]) for row in rows) != {
        ("JCoLA", "in_domain_valid"): 100, ("JCoLA", "out_of_domain_valid"): 100,
        ("JSTS", "valid"): 200, ("JCommonsenseQA", "valid"): 200,
    }:
        raise ValueError("unexpected source split counts")
    return rows


def _formatter():
    engine = object.__new__(NativeEngine)
    engine.prompt_style = "repeat_typed_score"
    return engine


def _request(row, options):
    formatter = _formatter()
    candidates, prefix, _ = formatter._candidate_spec(row, options)
    result = {"messages": formatter._messages(row, options),
              "candidates": candidates, "max_input_tokens": MAX_INPUT_TOKENS}
    if prefix:
        result["assistant_prefix"] = prefix
    return result


def _lines(row, options):
    if row["type"] == "score":
        return [f"{i}: {description}" for i, (_, description) in enumerate(options)]
    return [f"{string.ascii_uppercase[i]}. {key}: {description}"
            for i, (key, description) in enumerate(options)]


def _replace_option_lines(request, old_lines, new_lines):
    """Replace only each repeated prompt's terminal option block, even if the
    state itself includes option-like text. Fail closed if the formatter changes.
    """
    result = deepcopy(request)
    content = result["messages"][1]["content"]
    if len(content) % 2 != 0:
        raise ValueError("unexpected repeated prompt layout")
    half = content[:(len(content) - 2) // 2]
    if content != half + "\n\n" + half:
        raise ValueError("expected exactly two identical prompt copies")
    marker = "\n\n選択肢:\n"
    block = marker + "\n".join(old_lines) + "\n\n"
    start = half.rfind(marker)
    if start < 0 or not half.startswith(block, start):
        raise ValueError("unexpected terminal option block")
    tail = half[start + len(block):]
    if not tail or "\n\n" in tail:
        raise ValueError("unexpected output-format suffix")
    replaced = half[:start] + marker + "\n".join(new_lines) + "\n\n" + tail
    result["messages"][1]["content"] = replaced + "\n\n" + replaced
    return result


def variants(row):
    """Return only eligible conditions, with vectors aligned to original keys.

    Display-order variants preserve token/key/meaning bindings. Label reversal
    instead preserves semantic display order while reversing output letters and
    candidate_keys. Score numeric labels and their 0..5 interpretation never move.
    """
    options = _validate_row(row)
    keys = [key for key, _ in options]
    base = _request(row, options)
    lines = _lines(row, options)
    result = []

    def add(condition, request, candidate_keys=keys):
        if len(request["candidates"]) != len(candidate_keys) or set(candidate_keys) != set(keys):
            raise ValueError("invalid candidate mapping")
        result.append({"condition": condition, "request": deepcopy(request),
                       "candidate_keys": list(candidate_keys)})

    add("baseline", base)
    add("baseline_repeat", base)
    add("display_reverse", _replace_option_lines(base, lines, list(reversed(lines))))
    if len(options) >= 3:
        add("display_rotate", _replace_option_lines(base, lines, lines[1:] + lines[:1]))
    if row["type"] in ("choice", "noul"):
        letters = base["candidates"]
        reverse_labels = [f"{letter}. {key}: {description}"
                          for letter, (key, description) in zip(reversed(letters), options)]
        add("label_reverse", _replace_option_lines(base, lines, reverse_labels), list(reversed(keys)))
        opaque = [f"{letter}. slot_{i}: {description}"
                  for i, (letter, (_, description)) in enumerate(zip(letters, options))]
        add("opaque_keys", _replace_option_lines(base, lines, opaque))
    reworded = deepcopy(row)
    reworded["instructions"] = INSTRUCTION_REWORD[row["dataset"]]
    add("instruction_reword", _request(reworded, options))
    if row["dataset"] in DEFINITION_REWORD:
        reworded = deepcopy(row)
        reworded["criteria"] = deepcopy(DEFINITION_REWORD[row["dataset"]])
        add("definition_reword", _request(reworded, options_for(reworded)))
    return result
