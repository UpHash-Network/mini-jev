#!/usr/bin/env python3
"""Deterministic synthetic training/dev/calibration data; no model or eval reads.

Each type has eight families, each with six semantic configuration groups.
The first four groups go to train; the remaining groups go to dev/calibration.
Labels are computed from explicit rules. Candidate order is never a split key.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random


SEED = 20260920
SPLITS = ("train", "train", "train", "train", "dev", "calibration")
DOMAINS = (
    ("部品倉庫", "ねじ", "ボルト", "ワッシャー", "ナット", "軸", "歯車"),
    ("図書室", "文庫", "辞典", "雑誌", "図鑑", "地図", "楽譜"),
    ("生花店", "ばら", "ゆり", "菊", "ガーベラ", "すみれ", "蘭"),
    ("料理教室", "小麦粉", "米", "豆", "塩", "砂糖", "ごま"),
    ("観測所", "温度計", "雨量計", "風速計", "気圧計", "湿度計", "日照計"),
    ("舞台設備室", "照明", "マイク", "幕", "演台", "譜面台", "椅子"),
)
CHECKS = (
    ("在庫確認", "寸法検査", "封入", "宛名確認", "重量測定"),
    ("登録照合", "背表紙確認", "蔵書印確認", "修復確認", "棚番号確認"),
    ("水替え", "花弁確認", "茎の検査", "包装確認", "品種照合"),
    ("手洗い", "道具洗浄", "計量", "加熱確認", "片付け"),
    ("水平確認", "時計合わせ", "感度検査", "電源確認", "通信確認"),
    ("接続確認", "音量確認", "固定確認", "明るさ確認", "通路確認"),
)
FAMILIES = {
    "choice": ("numeric_band", "priority_rule", "boolean_pattern", "minimum_cost",
               "latest_event", "stock_decision", "symbol_mapping", "rule_count"),
    "noul": ("all_conditions", "any_condition", "veto_rule", "closed_interval",
             "quantity_comparison", "quota_rule", "state_transition", "exact_count"),
    "score": ("completed_count", "numeric_band", "shortage_level", "weighted_points",
              "completion_ratio", "maximum_risk", "violation_count", "consecutive_checks"),
}


def make_choice(family: str, group: int, example: int, rng: random.Random) -> tuple:
    domain, *items = DOMAINS[group]
    n = 2 + (FAMILIES["choice"].index(family) + group) % 5
    goal = example % n
    base, width = 11 + group * 13, 7 + group * 2
    state = {"業務": domain}
    if family == "numeric_band":
        value = base + goal * width + (example // n) % width
        state.update({"検査値": value, "備考": f"測定対象は{items[example % 6]}"})
        criteria = {f"band_{i}": f"検査値が{base + i * width}以上{base + (i + 1) * width}未満"
                    for i in range(n)}
        instructions = "検査値だけを使い、該当する範囲を一つ選んでください。境界値は『以上』側に含めます。"
        gold = (value - base) // width
    elif family == "priority_rule":
        names = [f"{items[i]}の追加点検" for i in range(n - 1)]
        flags = [False if i < goal else (True if i == goal else bool(rng.randrange(2))) for i in range(n - 1)]
        state.update({"点検対象": dict(zip(names, flags)), "当日の受付件数": 31 + example * 3 + group})
        criteria = {f"action_{i}": f"{name}を行う" for i, name in enumerate(names)}
        criteria[f"action_{n-1}"] = "追加点検をせず通常作業を続ける"
        instructions = "trueの点検対象が複数ある場合は、次の順番で最初のものだけを実施します：" + "、".join(names) + "。すべてfalseなら通常作業です。次の対応を選んでください。"
        gold = next((i for i, flag in enumerate(flags) if flag), n - 1)
    elif family == "boolean_pattern":
        # A binary code uses two or three independently meaningful checks.
        bits = max(1, (n - 1).bit_length())
        names = list(CHECKS[group][:bits])
        code = goal
        state.update({"検査": {name: bool(code & (1 << i)) for i, name in enumerate(names)},
                      "検査対象": items[example % 6], "実測重量": 70 + group * 19 + example})
        patterns = []
        for i in range(n):
            patterns.append("、".join(f"{name}が{'済' if i & (1 << j) else '未実施'}" for j, name in enumerate(names)))
        criteria = {f"pattern_{i}": pattern for i, pattern in enumerate(patterns)}
        instructions = "検査のtrueは済、falseは未実施を表します。現在の検査状態と完全に一致する組み合わせを選んでください。"
        gold = sum(int(state["検査"][name]) << i for i, name in enumerate(names))
    elif family == "minimum_cost":
        quantities = [rng.randint(2, 6) for _ in range(n)]
        prices = [rng.randint(12, 29) for _ in range(n)]
        fees = [rng.randint(2, 8) for _ in range(n)]
        prices[goal], quantities[goal], fees[goal] = 1 + example, 1, 0
        state["調達候補"] = [{"品目": items[i], "単価": prices[i], "個数": quantities[i], "手数料": fees[i]} for i in range(n)]
        criteria = {f"purchase_{i}": f"{items[i]}を選ぶ" for i in range(n)}
        instructions = "支払額は単価×個数＋手数料です。支払額が最も小さい調達候補を選んでください。同額の候補はありません。"
        totals = [prices[i] * quantities[i] + fees[i] for i in range(n)]
        gold = min(range(n), key=totals.__getitem__)
    elif family == "latest_event":
        times = rng.sample(range(30, 110), n)
        times[goal] = 130 + example
        records = [{"対象": items[i], "記録時刻": f"{8 + times[i] // 60:02d}:{times[i] % 60:02d}"} for i in range(n)]
        rng.shuffle(records)
        state.update({"同じ日の作業記録": records})
        criteria = {f"record_{i}": f"{items[i]}の記録" for i in range(n)}
        instructions = "記録一覧は時刻順とは限りません。同じ日の最も遅い時刻の記録を選んでください。"
        gold = max(range(n), key=times.__getitem__)
    elif family == "stock_decision":
        # n distinct, exhaustive intervals of a derived stock balance.
        desired = base + goal * width + (example // n)
        incoming = 4 + example * 2
        outgoing = 16 + group * 2
        current = desired - incoming + outgoing
        state.update({"対象": items[example % 6], "現在数": current, "入荷予定数": incoming, "確定出荷数": outgoing})
        criteria = {f"stock_{i}": f"更新後の数量が{base + i * width}以上{base + (i + 1) * width}未満の棚へ置く" for i in range(n)}
        instructions = "更新後の数量＝現在数＋入荷予定数−確定出荷数です。更新後の数量に合う棚を選んでください。"
        gold = (current + incoming - outgoing - base) // width
    elif family == "symbol_mapping":
        names = [f"{item}用の受付" for item in items[:n]]
        symbols = [f"{chr(75 + group)}{19 + 7 * i + group}" for i in range(n)]
        mapping = list(zip(symbols, names))
        rng.shuffle(mapping)
        state.update({"票の記号": symbols[goal], "個数": 13 + example * 7})
        criteria = {f"desk_{i}": name for i, name in enumerate(names)}
        instructions = "票の記号を次の対応表で受付に振り分けてください。" + "、".join(f"{symbol}なら{name}" for symbol, name in mapping) + "。個数は振り分けに影響しません。"
        gold = symbols.index(state["票の記号"])
    elif family == "rule_count":
        names = [f"{item}の記録" for item in items[:n - 1]]
        values = [True] * goal + [False] * (n - 1 - goal)
        rng.shuffle(values)
        state.update({"確認済み": dict(zip(names, values)), "残り時間（分）": 45 + example * 2})
        criteria = {f"count_{i}": f"確認済みが{i}件の窓口へ回す" for i in range(n)}
        instructions = "確認済みのtrueだけを数えて、該当する窓口を選んでください。falseは数えません。"
        gold = sum(values)
    else:
        raise AssertionError(family)
    assert gold == goal, (family, group, example, gold, goal)
    return state, instructions, criteria, list(criteria)[gold]


def make_noul(family: str, group: int, example: int, rng: random.Random) -> tuple:
    domain, *items = DOMAINS[group]
    names = list(CHECKS[group])
    target = example % 2 == 1
    inverted = example in (2, 3, 6, 7)
    required = not target if inverted else target
    # Pair positive/negative questions on the same item to avoid item-name shortcuts.
    state = {"業務": domain, "対象": items[(example // 2 + group) % 6]}
    if family == "all_conditions":
        n = 3 + group % 3
        values = [True] * n
        if not required:
            values[example % n] = False
        state.update({"確認": dict(zip(names[:n], values)), "受付数量": rng.randint(10, 99)})
        rule = "、".join(names[:n]) + "のすべてがtrueのときだけ処理を開始できます。"
        result = all(values)
    elif family == "any_condition":
        n = 3 + group % 3
        values = [False] * n
        if required:
            values[example % n] = True
        state.update({"確認": dict(zip(names[:n], values)), "対象数量": rng.randint(3, 75)})
        rule = "、".join(names[:n]) + "のうち少なくとも一つがtrueなら処理を開始できます。すべてfalseなら開始できません。"
        result = any(values)
    elif family == "veto_rule":
        # Permission with an overriding prohibition; include failures of each cause.
        ready = required or example % 4 == 0
        blocked = not required and example % 4 == 0
        state.update({names[0]: ready, "停止指示あり": blocked, "予定数": rng.randint(8, 80)})
        rule = f"{names[0]}がtrueで、かつ停止指示がないときだけ処理を開始できます。停止指示があれば他の条件にかかわらず開始できません。"
        result = ready and not blocked
    elif family == "closed_interval":
        low, high = 12 + group * 9, 24 + group * 11
        if required:
            value = (low, high, low + 1, high - 1)[example // 2]
        else:
            value = (low - 1 - example, high + 1 + example)[example % 2]
        state["測定値"] = value
        rule = f"測定値が{low}以上{high}以下のときだけ処理を開始できます。両端の値を含みます。"
        result = low <= value <= high
    elif family == "quantity_comparison":
        requested = 20 + group * 7 + example
        reserved = 3 + example
        available = requested + (example // 2 if required else -1 - example // 2)
        state.update({"総数量": available + reserved, "取り置き数": reserved, "今回必要数": requested})
        rule = "使える数量＝総数量−取り置き数です。使える数量が今回必要数以上なら処理を開始できます。不足なら開始できません。"
        result = state["総数量"] - reserved >= requested
    elif family == "quota_rule":
        cap = 40 + group * 13
        already = 9 + example * 2
        new = cap - already - (example // 2 if required else -1 - example // 2)
        state.update({"既に引き受けた件数": already, "今回追加する件数": new})
        rule = f"引き受け済みと今回追加の合計が上限{cap}件以下なら処理を開始できます。上限と同じ値は許可します。"
        result = already + new <= cap
    elif family == "state_transition":
        statuses = ("準備中", "照合済み", "処理中", "完了")
        start, end = statuses[group % 3], statuses[group % 3 + 1]
        current = start if required else statuses[(group % 3 + 2) % 4]
        state.update({"現在の状態": current, "要求された遷移先": end, "関連件数": rng.randint(2, 99)})
        rule = f"今回は『{start}』から『{end}』への遷移だけが許可されています。現在の状態と遷移先が両方一致するときだけ処理を開始できます。"
        result = current == start and state["要求された遷移先"] == end
    elif family == "exact_count":
        need = 1 + group % 4
        count = need if required else (need + 1 if example % 2 else need - 1)
        values = [True] * count + [False] * (5 - count)
        rng.shuffle(values)
        state.update({"確認": dict(zip(names, values)), "受け付けた数量": rng.randint(8, 95)})
        rule = f"確認項目のtrueがちょうど{need}個のときだけ処理を開始できます。{need}個より多くても少なくても開始できません。"
        result = sum(values) == need
    else:
        raise AssertionError(family)
    instructions = rule + ("この状態では処理を開始できない、という判断は正しいですか。" if inverted else "この状態で処理を開始できますか。")
    answer = not result if inverted else result
    assert answer == target
    return state, instructions, {"false": "質問への答えがいいえ", "true": "質問への答えがはい"}, answer


def make_score(family: str, group: int, example: int, rng: random.Random, target: int, n: int) -> tuple:
    domain, *items = DOMAINS[group]
    names = list(CHECKS[group][:n - 1])
    state = {"業務": domain, "対象": items[example % 6]}
    if family == "completed_count":
        flags = [True] * target + [False] * (n - 1 - target)
        rng.shuffle(flags)
        state.update({"完了項目": dict(zip(names, flags)), "予定作業時間": 30 + example})
        instructions = "完了項目のtrueを数えて評価してください。falseは未完了です。作業時間は評価に使いません。"
        criteria = [f"完了が{i}項目" for i in range(n)]
        gold = sum(flags)
    elif family == "numeric_band":
        step = 9 + group * 2
        value = target * step + example % step
        state["測定値"] = value
        criteria = [f"測定値が{i * step}以上{(i + 1) * step}未満" for i in range(n)]
        instructions = "測定値に該当する段階を選んでください。下端を含み、上端は含みません。"
        gold = value // step
    elif family == "shortage_level":
        step = 4 + group
        shortage = target * step + example % step
        need = 75 + group * 9 + example
        have = need - shortage
        state.update({"必要数": need, "用意できた数": have})
        criteria = [f"不足数が{i * step}以上{(i + 1) * step}未満" for i in range(n)]
        instructions = "不足数＝必要数−用意できた数です。不足数から段階を選んでください。"
        gold = (need - have) // step
    elif family == "weighted_points":
        # Distinct positive integer weights; all integers 0..n-1 are representable.
        weights = (1, 2, 4)
        flags = [bool(target & weight) for weight in weights]
        state.update({"検査": dict(zip(CHECKS[group][:3], flags)), "実施時刻（分）": 11 + example})
        rules = "、".join(f"{name}がtrueなら{weight}点" for name, weight in zip(CHECKS[group][:3], weights))
        instructions = f"{rules}を加算し、falseは0点としてください。合計点で段階を選びます。"
        criteria = [f"合計{i}点" for i in range(n - 1)] + [f"合計{n - 1}点以上"]
        gold = min(sum(weight for weight, flag in zip(weights, flags) if flag), n - 1)
    elif family == "completion_ratio":
        unit = 5 + group
        total = n * unit
        done = target * unit + example % unit
        state.update({"作業全体の件数": total, "完了件数": done})
        instructions = f"全体の件数を{n}等分します。完了件数がいくつ分の区間に入るかを選んでください。最後の区間は全件完了も含みます。"
        criteria = [f"完了件数が{i * unit}件以上{(i + 1) * unit}件未満" for i in range(n - 1)] + [f"完了件数が{(n - 1) * unit}件以上{n * unit}件以下"]
        gold = min(done // unit, n - 1)
    elif family == "maximum_risk":
        area_count = 3 + example % 4
        readings = [rng.randint(0, target) for _ in range(area_count)]
        readings[example % area_count] = target
        state["区画ごとの検査値"] = dict(zip(items[:area_count], readings))
        instructions = "各区画の検査値の最大値を全体の警戒段階にします。平均値や合計値は使いません。"
        criteria = [f"最大値が{i}の警戒段階" for i in range(n)]
        gold = max(readings)
    elif family == "violation_count":
        # Numeric thresholds vary across the semantic groups and checks.
        limits = [20 + group * 8 + j * 3 for j in range(n - 1)]
        fail = [True] * target + [False] * (n - 1 - target)
        rng.shuffle(fail)
        values = [limit + 1 + example if bad else limit - example for limit, bad in zip(limits, fail)]
        state["検査値"] = dict(zip(items[:n - 1], values))
        limits_text = "、".join(f"{item}は{limit}以下" for item, limit in zip(items[:n - 1], limits))
        instructions = f"合格基準は{limits_text}です。上限を超えた項目の数を数え、違反の段階を選んでください。上限と同じ値は合格です。"
        criteria = [f"基準違反が{i}項目" for i in range(n)]
        gold = sum(value > limit for value, limit in zip(values, limits))
    elif family == "consecutive_checks":
        flags = [True] * target
        if target < n - 1:
            flags.append(False)
        flags += [bool(rng.randrange(2)) for _ in range(n - 1 - len(flags))]
        state.update({"検査結果": dict(zip(names, flags)), "今回の処理件数": 14 + example * 2})
        instructions = "次の順に検査を読みます：" + "、".join(names) + "。先頭から連続したtrueの数を段階にしてください。最初のfalseより後は数えません。"
        criteria = [f"先頭から{i}項目が連続してtrue" for i in range(n)]
        gold = next((i for i, value in enumerate(flags) if not value), n - 1)
    else:
        raise AssertionError(family)
    assert gold == target, (family, group, example, gold, target)
    return state, instructions, criteria, gold


def canonical_input(row: dict) -> str:
    """Sorting mapping keys deliberately ignores Choice presentation order."""
    payload = {key: row[key] for key in ("type", "state", "instructions", "criteria")}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def generate(seed: int = SEED) -> tuple[dict, dict]:
    rng = random.Random(seed)
    rows = {split: [] for split in ("train", "dev", "calibration")}
    counters = Counter()
    groups = defaultdict(list)
    for kind, families in FAMILIES.items():
        for family_index, family in enumerate(families):
            for group, split in enumerate(SPLITS):
                group_id = f"{kind}/{family}/g{group:02}"
                groups[split].append(group_id)
                for example in range(8):
                    if kind == "choice":
                        state, instruction, criteria, label = make_choice(family, group, example, rng)
                        n = len(criteria)
                        position = counters[split, kind, n] % n
                        counters[split, kind, n] += 1
                        others = [key for key in criteria if key != label]
                        rng.shuffle(others)
                        others.insert(position, label)
                        criteria = {key: criteria[key] for key in others}
                    elif kind == "noul":
                        state, instruction, criteria, label = make_noul(family, group, example, rng)
                    else:
                        n = 3 + (family_index + group) % 4
                        target = counters[split, kind, n] % n
                        counters[split, kind, n] += 1
                        state, instruction, criteria, label = make_score(family, group, example, rng, target, n)
                    rows[split].append({"id": f"{split}-{kind}-{family}-g{group:02}-{example:02}",
                                        "type": kind, "state": state, "instructions": instruction,
                                        "criteria": criteria, "label": label, "family": family,
                                        "split": split})
    for data in rows.values():
        rng.shuffle(data)
    return rows, dict(groups)


def validate(rows: dict, groups: dict) -> dict:
    all_ids, signatures = set(), {}
    report = {}
    for split, data in rows.items():
        assert len(data) == (768 if split == "train" else 192)
        type_counts = Counter(row["type"] for row in data)
        assert len(set(type_counts.values())) == 1
        family_counts = Counter(f"{row['type']}/{row['family']}" for row in data)
        assert len(family_counts) == 24
        positions = defaultdict(Counter)
        polarity = Counter()
        for row in data:
            assert set(row) == {"id", "type", "state", "instructions", "criteria", "label", "family", "split"}
            assert row["split"] == split and row["id"] not in all_ids
            all_ids.add(row["id"])
            signature = canonical_input(row)
            assert signature not in signatures, ("duplicate input", row["id"], signatures.get(signature))
            signatures[signature] = row["id"]
            criteria, label = row["criteria"], row["label"]
            if row["type"] == "choice":
                assert 2 <= len(criteria) <= 6 and label in criteria
                pos = list(criteria).index(label)
                positions[f"choice/{len(criteria)}"][pos] += 1
            elif row["type"] == "score":
                assert 3 <= len(criteria) <= 6 and type(label) is int and 0 <= label < len(criteria)
                positions[f"score/{len(criteria)}"][label] += 1
            else:
                assert set(criteria) == {"false", "true"} and type(label) is bool
                polarity[str(label).lower()] += 1
        assert polarity["true"] == polarity["false"]
        for key, counts in positions.items():
            n = int(key.split("/")[1])
            assert set(counts) == set(range(n))
            assert max(counts.values()) - min(counts.values()) <= 1, (split, key, counts)
        report[split] = {"count": len(data), "by_type": dict(type_counts),
                         "by_family": dict(sorted(family_counts.items())),
                         "answer_positions_by_candidate_count": {key: dict(sorted(value.items())) for key, value in sorted(positions.items())},
                         "noul_labels": dict(sorted(polarity.items())), "semantic_group_count": len(groups[split])}
    for left in groups:
        for right in groups:
            if left != right:
                assert not set(groups[left]) & set(groups[right])
    report["checks"] = {"unique_ids": len(all_ids), "unique_inputs_ignoring_choice_order": len(signatures),
                        "cross_split_duplicate_inputs": 0, "cross_split_shared_semantic_groups": 0,
                        "families_per_type": 8,
                        "position_count_max_gap_within_each_candidate_count": 1,
                        "source_eval_files_read": False}
    return report


def write_notes(path: Path, report: dict, groups: dict, hashes: dict, seed: int) -> None:
    text = ["# 出力ヘッド学習用の合成データ", "", f"生成seed: `{seed}`。生成器: `make_training_data.py`。",
            "", "このデータは日本語の明示ルール適用を人工的に構成したものです。実業務データでも、独立評価データでもありません。既存の eval_ja.jsonl は生成・設計・検証で読んでいません。",
            "", "## 分割と用途", "",
            "- train: 768件、出力ヘッドの学習専用。",
            "- dev: 192件、学習条件・停止時点の選択専用。",
            "- calibration: 192件、選択完了後の温度等の校正専用。精度の最終評価には使用しない。",
            "- 各分割はChoice/Noul/Scoreが均等。各型8 family、各familyはtrain32件/dev8件/calibration8件。",
            "", "各familyは6つの意味設定グループを持ち、業務対象・語彙・規則の数値設定を群ごとに固定します。g00〜g03をtrain、g04をdev、g05をcalibrationへ割り当て、同一群の8例は分割しません。trainは部品倉庫・図書室・生花店・料理教室、devは観測所、calibrationは舞台設備室です。familyのアルゴリズム構造は共有しており、これは同一テンプレート族内の語彙・設定への一般化を確認する分割です。未知の推論構造への一般化を保証しません。",
            "", "各例の正解は明記された数値・条件から算出します。Choiceの候補順はseed付きで変更し、候補数ごとに正解表示位置を均等化。Scoreの基準は低段階から高段階の順を保持し、候補数ごとに正解段階を均等化。Noulは真偽が同数で、否定形の質問も含みます。",
            "", "状態に正解キー・正解説明を単独で埋め込む方式は使いません。表の照合・時刻比較・最小費用では対象名が全候補について状態にも現れます。正解が文字列一致だけで決まる例や算術中心の例も含む、限定的な合成タスクです。",
            "", "Choiceの候補順を無視した全入力の重複検査、ID重複検査、群の分割重複検査、型とfamilyの件数検査、正解位置・真偽の均等性検査を生成時に実施します。model/tokenizerの実行は行いません。入力長の上限は特徴抽出側で確認してください。",
            "", "## ファイル整合性", "", "```json", json.dumps(hashes, ensure_ascii=False, indent=2), "```",
            "", "## 検証集計", "", "```json", json.dumps(report, ensure_ascii=False, indent=2), "```",
            "", "## 意味設定グループ", "", "```json", json.dumps(groups, ensure_ascii=False, indent=2), "```", ""]
    path.write_text("\n".join(text), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "data")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    rows, groups = generate(args.seed)
    report = validate(rows, groups)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for split, data in rows.items():
        path = args.output_dir / f"head_{split}.jsonl"
        raw = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in data).encode("utf-8")
        path.write_bytes(raw)
        hashes[path.name] = hashlib.sha256(raw).hexdigest()
    write_notes(args.output_dir / "head_data_notes.md", report, groups, hashes, args.seed)
    print(json.dumps({"files": hashes, "counts": {key: value["count"] for key, value in report.items() if key != "checks"}, "checks": report["checks"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
