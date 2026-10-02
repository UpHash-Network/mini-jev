"""Check an actual compact ChainForge XLSX export; needs openpyxl.

No model calls or human outcome measures. JSON text must round-trip exactly;
numeric-cell differences are reported, not silently rounded into equality.
"""
import argparse
import hashlib
import json
from pathlib import Path

from openpyxl import load_workbook

parser = argparse.ArgumentParser()
parser.add_argument("spreadsheet", type=Path)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
if args.out.exists():
    raise SystemExit("Refusing to overwrite earlier output")
tasks = json.loads(Path(__file__).with_name("tasks.json").read_text())["tasks"]
lookup = {t["id"]: t for t in tasks}
sheet = load_workbook(args.spreadsheet, data_only=True).active
rows = list(sheet.values)
headers = rows[0]
assert len(rows) == 13
checks, deltas, seen = [], [], set()
for values in rows[1:]:
    row = dict(zip(headers, values))
    record = json.loads(row["Response"])
    case, side = record["task_id"], record["side"]
    assert (case, side) not in seen
    seen.add((case, side))
    expected = json.loads(lookup[case]["evidence_json"])["comparison_export"]
    condition = expected["conditions"][side]
    assert record["condition"] == condition
    assert record["sources"] == expected["sources"]
    assert record["candidate_comparison"] == expected["candidate_comparison"]
    assert row["Var: task_id"] == case and row["Var: side"] == side
    # Read labels from the canonical condition, not a rounded displayed score.
    probabilities = condition["probabilities"]
    for key, value in zip(expected["canonical_keys"], probabilities):
        actual = row["Eval result: P(" + key + ")"]
        assert isinstance(actual, (int, float))
        delta = abs(actual - value)
        deltas.append(delta)
        if delta:
            checks.append({"case": case, "side": side, "candidate": key,
                           "canonical": value, "xlsx_numeric": actual,
                           "absolute_difference": delta})
report = {
    "status": "pass" if not checks else "json_exact_numeric_rounding_observed",
    "xlsx_sha256": hashlib.sha256(args.spreadsheet.read_bytes()).hexdigest(),
    "rows": 12, "response_json_conditions_and_sources_exact": 12,
    "candidate_numeric_cells_checked": len(deltas),
    "candidate_numeric_cells_exact": sum(d == 0 for d in deltas),
    "max_numeric_cell_absolute_difference": max(deltas),
    "numeric_cell_differences": checks,
    "interpretation": "Compact Response JSON retains exact recorded values; numeric spreadsheet cells are checked separately. This checks export fidelity, not human task performance. Full multi-megabyte evidence uses the flow export, not XLSX cells.",
}
args.out.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k:v for k,v in report.items() if k != "numeric_cell_differences"}, indent=2))
