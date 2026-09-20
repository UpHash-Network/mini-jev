"""Regenerate 30 toy records for CLI smoke tests, not an accuracy benchmark."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def main():
    for split, count, offset in (("train", 12, 10), ("dev", 6, 100),
                                 ("calibration", 6, 200), ("test", 6, 300)):
        rows = []
        for index in range(count):
            n = offset + index
            kind = ("choice", "noul", "score")[index % 3]
            common = {"id": f"{split}-{index:02d}", "type": kind,
                      "group": f"{split}-scenario-{index}", "family": "toy-modulo-three" if kind == "score" else "toy-parity",
                      "state": {"number": n}}
            if kind == "choice":
                common.update(instructions="数値の偶奇を選んでください。",
                              criteria={"even": "偶数", "odd": "奇数"}, label="even" if n % 2 == 0 else "odd")
            elif kind == "noul":
                common.update(instructions="数値は偶数ですか。",
                              criteria={"false": "いいえ", "true": "はい"}, label=n % 2 == 0)
            else:
                common.update(instructions="数値を3で割った余りに対応する段階を選んでください。",
                              criteria=["余り0", "余り1", "余り2"], label=n % 3)
            rows.append(common)
        (HERE / f"{split}.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n")

if __name__ == "__main__":
    main()
