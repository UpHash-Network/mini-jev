"""Create 2,220 deterministic, oracle-checked Japanese blind acceptance cases.

This file never imports the model, training data, or earlier evaluation results.
Version 2 excludes every v1 canonical oracle-fact identity.
Only state/instructions/type/criteria are model inputs. Metadata is audit-only.
Run: python make_generated_eval.py --check
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import random
from pathlib import Path

SEED = 202609201731
ROOT = Path(__file__).resolve().parent
NAMES = ["青木", "石田", "上田", "遠藤", "大野", "加藤", "木村", "佐藤", "高橋", "中村", "林", "松本", "森", "山田", "吉田", "渡辺"]
ITEMS = ["ノート", "封筒", "ファイル", "ペン", "ラベル", "付箋", "クリップ", "用紙", "箱", "袋", "冊子", "カード", "シール", "名札", "テープ", "ケース"]
PROJECTS = ["青空", "若葉", "白波", "春風", "朝露", "夕凪", "星空", "木漏れ日", "山道", "水面", "灯台", "草原"]
COLORS = ["赤", "青", "緑", "黄", "白", "黒", "紫", "茶"]
MATERIALS = ["紙", "木", "布", "金属", "ガラス", "樹脂"]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def pick(rng, items, count):
    return rng.sample(items, count)


def choose(rng, *texts):
    index = rng.randrange(len(texts))
    return texts[index], index + 1


def clamp(value, low, high):
    return max(low, min(high, value))


def solve(rule, f):
    """Independent executable oracle over semantic facts, not rendered labels."""
    if rule == "route":
        return next(k for k, topics in f["routes"].items() if f["topic"] in topics)
    if rule == "policy_exception":
        if f["excluded"]:
            return "通常"
        return "優待" if f["member"] and f["amount"] >= f["minimum"] else "通常"
    if rule == "latest":
        return max(f["updates"], key=lambda x: x["time"])["value"]
    if rule == "reference":
        linked = f["links"][f["reference"]]
        return f["owners"][linked]
    if rule == "unique_filter":
        matches = [x["name"] for x in f["records"] if all(x[k] == v for k, v in f["required"].items())]
        assert len(matches) == 1
        return matches[0]
    if rule == "slot":
        matches = [x["name"] for x in f["rooms"] if x["start"] <= f["start"] and x["end"] >= f["end"]]
        assert len(matches) == 1
        return matches[0]
    if rule == "revision":
        return f["exception_value"] if f["exception"] else f["revisions"][-1]
    if rule == "set_difference":
        possible = set(f["available"]) - set(f["reserved"])
        assert len(possible) == 1
        return next(iter(possible))
    if rule == "delegate":
        owner = f["owners"][f["topic"]]
        return f["deputies"][owner] if owner in f["absent"] else owner
    if rule == "net_stock":
        values = {x["name"]: x["stock"] - x["reserved"] for x in f["records"]}
        answer = (min if f["direction"] == "smallest" else max)(values, key=values.get)
        assert list(values.values()).count(values[answer]) == 1
        return answer
    if rule == "required_document":
        needed = f["priority"][:]
        if not f["special"]:
            needed.remove(f["special_document"])
        missing = [x for x in needed if x not in f["submitted"]]
        return missing[0] if missing else "追加不要"
    if rule == "workflow":
        return next((x for x in f["steps"] if x not in f["done"]), "完了")
    if rule == "pair_lookup":
        matched = [x["name"] for x in f["records"] if x["color"] == f["color"] and x["material"] == f["material"]]
        assert len(matched) == 1
        return matched[0]
    if rule == "rank_reference":
        return f["order"][f["rank"] - 1]
    if rule == "fact_negation":
        return f["fact"] != f["negated_query"]
    if rule == "and":
        return all(f["conditions"])
    if rule == "or":
        return any(f["conditions"])
    if rule == "except":
        return f["eligible"] and not f["exception"]
    if rule == "deadline":
        return f["actual"] <= f["deadline"] if f["inclusive"] else f["actual"] < f["deadline"]
    if rule == "latest_is":
        return max(f["updates"], key=lambda x: x["time"])["value"] == f["query"]
    if rule == "exact":
        return f["left"] == f["right"]
    if rule == "membership":
        return (f["entity"] in f["members"]) == f["positive"]
    if rule == "distinct_count":
        return len(set(f["entries"])) >= f["minimum"]
    if rule == "implication":
        return (not f["premise"]) or f["conclusion"]
    if rule == "reference_is":
        return f["owners"][f["links"][f["reference"]]] == f["person"]
    if rule == "evidence":
        return f["recorded"] == f["asserted"]
    if rule == "range":
        low_ok = f["value"] >= f["low"] if f["low_closed"] else f["value"] > f["low"]
        high_ok = f["value"] <= f["high"] if f["high_closed"] else f["value"] < f["high"]
        return low_ok and high_ok
    if rule == "overlap":
        return max(f["a_start"], f["b_start"]) < min(f["a_end"], f["b_end"])
    if rule == "precedence":
        return f["events"].index(f["first"]) < f["events"].index(f["second"])
    if rule == "threshold_score":
        return sum(f["value"] >= edge for edge in f["thresholds"])
    if rule == "sentiment_score":
        return f["ordered_meanings"].index(f["meaning"])
    if rule == "progress_score":
        return len(f["done"])
    if rule == "dimensions_score":
        return sum(f["satisfied"])
    if rule == "priority_score":
        urgent = f["hours_left"] <= f["urgent_within"] if "hours_left" in f else f["urgent"]
        raw = f["impact"] + (1 if urgent else 0)
        return clamp(raw, 0, f["max_score"])
    if rule == "delay_score":
        value = max(0, f["arrival"] - f["promised"])
        return sum(value >= edge for edge in f["thresholds"])
    if rule == "evidence_score":
        return max((f["levels"][x] for x in f["present"]), default=0)
    if rule == "match_score":
        return sum(f["actual"][k] == v for k, v in f["requirements"].items())
    if rule == "capped_score":
        raw = sum(f["checks"])
        return min(raw, f["cap"]) if f["exception"] else raw
    if rule == "missing_score":
        return len(set(f["required"]) - set(f["provided"]))
    if rule == "temporal_score":
        return max(f["updates"], key=lambda x: x["time"])["value"]
    if rule == "distance_score":
        distance = abs(f["actual"] - f["target"])
        return min(distance, f["max_score"])
    if rule == "reversible_score":
        value = sum(f["accepted"]) - sum(f["revoked"])
        return min(value, f.get("max_score", value))
    if rule == "lookup_score":
        return f["scale"][f["code"]]
    if rule == "weighted_score":
        return min(sum(weight for active, weight in zip(f["active"], f["weights"]) if active), f["max_score"])
    raise AssertionError(f"Unknown oracle rule: {rule}")


def explanation(rule, facts, answer):
    # Kept outside all model input fields. This is an auditable derivation record.
    reasons = {
        "route": "記録された主題を含む受付分類は一つだけであり、その分類の窓口を選ぶ",
        "policy_exception": "予約品なら優待を無効化する。予約品でない場合だけ、会員資格と購入数の下限を両方確認する",
        "latest": "記載の順番ではなく時刻を最大にする更新を探し、その状態を採用する",
        "reference": "資料から所属案件を引き、その案件から担当者を引く二段階の参照を行う",
        "unique_filter": "各品の属性を全条件と照合する。条件をすべて満たす品が一つだけ存在する",
        "slot": "部屋の空き開始が会議開始以前で、空き終了が会議終了以後であるものを選ぶ。端の一致を許す",
        "revision": "例外対象なら例外指定を採用する。それ以外は古い順の改訂一覧の末尾を採用する",
        "set_difference": "利用可能品の集合から予約済み品の集合を引くと一つだけ残る",
        "delegate": "案件担当を引く。本人が不在なら指定代理に一回だけ振り替え、不在でなければ本人とする",
        "net_stock": "品ごとに総在庫から予約分を引き、質問で指定された最大または最小を選ぶ。同数の首位はない",
        "required_document": "申請区分に応じて不要書類を除き、残る必要書類のうち未提出の最優先を選ぶ。不足がなければ追加不要",
        "workflow": "工程順に未完了の最初の工程を探す。全工程が完了なら完了を返す",
        "pair_lookup": "色と素材が両方一致する唯一の品を選ぶ",
        "rank_reference": "先頭を1番目とする順序で、質問に指定された順位の人を選ぶ",
        "fact_negation": "確定事実の真偽を確認し、質問が否定形なら真偽を反転する",
        "and": "記載された全条件が成立するときだけ質問は真になる",
        "or": "記載条件の少なくとも一つが成立するとき質問は真になる",
        "except": "許可条件に該当し、かつ優先禁止例外に該当しないときだけ許可する",
        "deadline": "提出時刻を締切と比較する。同時刻を含むかは明示された規則に従う",
        "latest_is": "最大時刻の更新から現在状態を求め、質問の状態と照合する",
        "exact": "大文字小文字と記号を含めて二つの文字列を比較する",
        "membership": "完全な名簿に対象者が存在するかを確認し、非所属を問う場合は真偽を反転する",
        "distinct_count": "品名の重複を除いた集合の要素数を求め、必要最小数以上かを判定する",
        "implication": "義務条件に該当しているのに必要処置が未実施の場合だけ違反となる。条件に該当しなければ違反なし",
        "reference_is": "資料の所属案件から担当者を求め、質問で指定された人物と照合する",
        "evidence": "対象入口の確定記録にある相互排他的な開き方を、質問の主張と照合する",
        "range": "下限条件と上限条件を別々に判定し、両方を満たす場合だけ適合とする。境界を含むかも区別する",
        "overlap": "二つの開始時刻の遅い方が、二つの終了時刻の早い方より厳密に早い場合だけ重なりがある",
        "precedence": "実施順一覧の中で二つの作業の位置を探し、質問の先行作業が前にあるか判定する",
        "threshold_score": "値が以上条件を満たす段階境界の本数を数える。境界の値ちょうどは上の段階に入る",
        "sentiment_score": "発言に明示された満足の程度を、今回用意された順序尺度内の同じ意味の段階へ対応づける",
        "progress_score": "先頭から完了している工程数を数え、その数の段階とする",
        "dimensions_score": "各独立チェックの成立を一点ずつ数え、成立項目数を段階とする",
        "priority_score": "締切までの時間が明示された基準時間以内なら基本優先度へ1加算し、そうでなければ加算しない。上限を適用する",
        "delay_score": "実到着時刻から約束時刻を引く。負なら遅れ0とし、遅延時間が以上条件を満たす境界数を段階とする",
        "evidence_score": "得られた証拠を今回の段階表で引き、その最大段階を採用する。証拠がなければ0",
        "match_score": "注文要件と提案品の同じ属性を比較し、値が完全一致する属性を一つずつ数える",
        "capped_score": "合格した検査項目数を数える。要再確認の印がある場合だけ指定上限との小さい方を採用する",
        "missing_score": "必要書類の集合から届いた書類を除き、残る種類数を数える。余分な書類は代用にならない",
        "temporal_score": "最大時刻の更新に記載された段階を採用する。段階値の最大や一覧の最後とは限らない",
        "distance_score": "実績と目標の差の絶対値を求め、最終段階の上限との小さい方を採用する",
        "reversible_score": "受付済み件数から取消済み件数を引く。有効件数が最終段階の基準以上なら最終段階へまとめる",
        "lookup_score": "確定検査票の印を今回の対応表で引く。色に一般的な順位を仮定しない",
        "weighted_score": "発生した不備の指定点だけを合計し、合計が最終段階の基準以上なら最終段階へまとめる",
    }
    return f"{reasons[rule]}。この規則による正解は {answer!r}。判定に用いた事実: {canonical(facts)}"


def state_form(rng, narrative, structured):
    return structured if rng.randrange(2) else narrative


def choice_case(family, rng, index):
    k = rng.randint(2, 8)
    names = pick(rng, NAMES, k)
    items = pick(rng, ITEMS, k)
    project = rng.choice(PROJECTS)
    if family == "問い合わせ経路":
        definitions = [("請求", ["二重請求", "領収書", "返金"]), ("配送", ["届け先変更", "荷物の遅延", "追跡番号"]), ("アカウント", ["ログイン", "パスワード", "退会"]), ("製品", ["破損", "初期不良", "部品交換"]), ("契約", ["契約更新", "プラン変更", "解約手続き"]), ("店舗", ["営業時間", "店内設備", "店舗の場所"]), ("イベント", ["申込期限", "会場案内", "参加取消"]), ("修理", ["修理見積", "修理進捗", "保証修理"])]
        selected = pick(rng, definitions, rng.randint(2, 6))
        routes = {key: topics for key, topics in selected}
        topic = rng.choice(rng.choice(selected)[1])
        paraphrases = {"申込期限": "イベントの参加申込みはいつまでですか", "会場案内": "イベントの会場への行き方を教えてください", "参加取消": "申込み済みイベントへの参加を取り消したいです", "修理見積": "故障した製品の修理代の見積もりをお願いします", "修理進捗": "依頼中の修理がどこまで進んだか知りたいです", "保証修理": "保証期間内の修理を申し込みたいです", "二重請求": "同じ代金が二回引き落とされています", "領収書": "支払い済みなので領収書を発行してほしいです", "返金": "返金の入金予定を知りたいです", "届け先変更": "発送前の荷物の届け先を変えたいです", "荷物の遅延": "荷物が予定日を過ぎても届きません", "追跡番号": "配送状況を見るための追跡番号を教えてください", "ログイン": "自分のアカウントにログインできません", "パスワード": "パスワードを忘れたので再設定したいです", "退会": "アカウントを退会したいです", "破損": "開封すると製品が割れていました", "初期不良": "買った製品が最初から動きません", "部品交換": "付属の部品だけ交換してほしいです", "契約更新": "今の契約を更新したいです", "プラン変更": "契約中のプランを変更したいです", "解約手続き": "サービスの解約手続きを知りたいです", "営業時間": "お店は何時から何時まで開いていますか", "店内設備": "お店に車いす用の設備はありますか", "店舗の場所": "お店がどこにあるか知りたいです"}
        f = {"routes": routes, "topic": topic}
        # Customer/topic relation is explicit in both forms to avoid open-world knowledge.
        inquiry = paraphrases[topic]
        mapping = " / ".join(f"{key}窓口: {'・'.join(topics)}" for key, topics in selected)
        narrative = f"受付分類表は次のとおりです。{mapping}。問い合わせ本文:「{inquiry}」。受付担当が付けた主題は「{topic}」です。"
        state = state_form(rng, narrative, {"分類表": routes, "本文": inquiry, "受付主題": topic})
        ins, v = choose(rng, "分類表に従い、この問い合わせを担当する窓口を一つ選んでください。", "記録された主題を扱う転送先はどこですか。", "受付分類表を使って、この相談の担当を決めてください。")
        return state, ins, [(key, f"{key}の窓口") for key, _ in selected], "route", f, v
    if family == "条件と優先例外":
        amount, minimum = rng.randint(1, 15), rng.randint(3, 12)
        member, excluded = bool(rng.randrange(2)), bool(rng.randrange(2))
        f = {"member": member, "excluded": excluded, "amount": amount, "minimum": minimum}
        narrative = f"{project}店では会員で購入数が{minimum}個以上なら優待扱いです。ただし予約品は購入数や会員資格にかかわらず通常扱いです。今回は{amount}個、{'会員' if member else '非会員'}、{'予約品' if excluded else '通常在庫品'}です。"
        state = state_form(rng, narrative, {"規則": f"会員かつ{minimum}個以上なら優待。ただし予約品は常に通常", "会員": member, "購入数": amount, "予約品": excluded})
        ins, v = choose(rng, "この購入に適用する扱いを選んでください。", "例外も踏まえて、今回の購入区分はどれですか。", "会計時の区分を一つ決めてください。")
        return state, ins, [("通常", "通常の扱い"), ("優待", "優待の扱い")], "policy_exception", f, v
    if family == "最終更新":
        values = pick(rng, ["未着手", "確認中", "保留", "承認", "差戻し", "取消", "発送済み", "受取済み"], k)
        times = sorted(pick(rng, list(range(8, 21)), rng.randint(3, 5)))
        updates = [{"time": t, "value": rng.choice(values)} for t in times]
        rng.shuffle(updates)
        f = {"updates": updates}
        narrative = f"案件「{project}」の記録です。" + " ".join(f"{x['time']}時の更新: {x['value']}。" for x in updates)
        state = state_form(rng, narrative, {"案件": project, "更新記録": [{"時": x["time"], "状態": x["value"]} for x in updates]})
        ins, v = choose(rng, "記載順ではなく更新時刻を比べ、最新の状態を選んでください。", "最後の時刻の記録が有効です。現在の状態はどれですか。", "時刻が最も新しい更新に基づく状態を答えてください。")
        return state, ins, [(x, x) for x in values], "latest", f, v
    if family == "参照先の担当":
        projects = pick(rng, PROJECTS, k)
        owners = dict(zip(projects, names))
        references = pick(rng, ITEMS, k)
        links = dict(zip(references, rng.sample(projects, k)))
        reference = rng.choice(references)
        f = {"owners": owners, "links": links, "reference": reference}
        narrative = "担当: " + "、".join(f"{p}は{n}" for p, n in owners.items()) + "。資料の所属: " + "、".join(f"{a}は{p}案件" for a, p in links.items()) + f"。確認する資料は{reference}です。"
        state = state_form(rng, narrative, {"案件担当": owners, "資料の所属案件": links, "確認資料": reference})
        ins, v = choose(rng, "確認資料が属する案件の担当者を選んでください。", "この資料について、所属案件を通じて連絡すべき担当者は誰ですか。", "確認する資料の案件を担当している人を答えてください。")
        return state, ins, [(x, f"{x}さん") for x in names], "reference", f, v
    if family == "否定条件で選択":
        correct = rng.randrange(k)
        required = {"sealed": bool(rng.randrange(2)), "wet": False}
        records = []
        wrong = [(not required["sealed"], False), (required["sealed"], True), (not required["sealed"], True)]
        for i, name in enumerate(items):
            sealed, wet = (required["sealed"], False) if i == correct else rng.choice(wrong)
            records.append({"name": name, "sealed": sealed, "wet": wet})
        f = {"records": records, "required": required}
        narrative = "検品記録: " + "、".join(f"{x['name']}は{'封あり' if x['sealed'] else '封なし'}で{'濡れている' if x['wet'] else '濡れていない'}" for x in records) + "。"
        structured = {"検品": [{"品名": x["name"], "封がある": x["sealed"], "濡れている": x["wet"]} for x in records]}
        state = state_form(rng, narrative, structured)
        seal = "封がある" if required["sealed"] else "封がない"
        ins, v = choose(rng, f"{seal}もので、かつ濡れていない品を選んでください。", f"対象は『{seal}』『濡れていない』の両方を満たす品です。どれですか。", f"濡れた品は除外し、{seal}品を一つ選んでください。")
        return state, ins, [(x, x) for x in items], "unique_filter", f, v
    if family == "時間枠の包含":
        start = rng.randint(9, 16)
        end = start + rng.randint(1, 3)
        correct = rng.randrange(k)
        rooms = []
        for i, name in enumerate(pick(rng, COLORS, k)):
            if i == correct:
                a, b = start - rng.randint(0, 2), end + rng.randint(0, 2)
            elif rng.randrange(2):
                a, b = start + 1, end + rng.randint(1, 2)
            else:
                a, b = start - rng.randint(1, 2), end - 1
            rooms.append({"name": name, "start": a, "end": b})
        f = {"rooms": rooms, "start": start, "end": end}
        narrative = "部屋の連続利用可能時間: " + "、".join(f"{x['name']}室は{x['start']}時から{x['end']}時まで" for x in rooms) + f"。会議は{start}時開始、{end}時終了です。"
        state = state_form(rng, narrative, {"空き時間": [{"部屋": x["name"], "開始": x["start"], "終了": x["end"]} for x in rooms], "会議開始": start, "会議終了": end})
        ins, v = choose(rng, "会議の全時間を連続して確保できる部屋を選んでください。開始・終了の一致は許可します。", "会議開始から終了まで空いている部屋はどれですか。境界時刻が一致していても利用できます。", "会議時間の一部だけでなく全体を含む空き時間を持つ部屋を答えてください。端の一致は可です。")
        return state, ins, [(x["name"], f"{x['name']}室") for x in rooms], "slot", f, v
    if family == "複数属性の制約":
        correct = rng.randrange(k)
        color, material = rng.choice(COLORS), rng.choice(MATERIALS)
        required = {"color": color, "material": material, "stock": True}
        records = []
        for i, name in enumerate(items):
            record = {"name": name, **required}
            if i != correct:
                bad = rng.choice(list(required))
                record[bad] = (not required[bad]) if bad == "stock" else rng.choice([x for x in (COLORS if bad == "color" else MATERIALS) if x != required[bad]])
            records.append(record)
        f = {"records": records, "required": required}
        narrative = "在庫表: " + "、".join(f"{x['name']}は{x['color']}色・{x['material']}製・{'在庫あり' if x['stock'] else '在庫なし'}" for x in records) + "。"
        state = state_form(rng, narrative, {"在庫表": [{"品名": x["name"], "色": x["color"], "素材": x["material"], "在庫あり": x["stock"]} for x in records]})
        ins, v = choose(rng, f"{color}色で{material}製、在庫もある品を選んでください。", f"必要条件は{color}色、{material}製、在庫ありの三つです。全部に合う品はどれですか。", f"今注文できる{material}製の{color}色の商品を答えてください。在庫なしは選べません。")
        return state, ins, [(x, x) for x in items], "unique_filter", f, v
    if family == "改訂と例外の優先":
        labels = pick(rng, COLORS, k)
        revisions = rng.sample(labels, min(k, 3))
        special = rng.choice(labels)
        exception = bool(rng.randrange(2))
        f = {"revisions": revisions, "exception_value": special, "exception": exception}
        narrative = "通常品の貼付ラベルについて、連絡は古い順に「" + "」「".join(revisions) + f"」でした。後の連絡が前の連絡を上書きします。ただし冷蔵品には連絡履歴に関係なく{special}ラベルを貼ります。今回の荷物は{'冷蔵品' if exception else '通常品'}です。"
        state = state_form(rng, narrative, {"通常品ラベルの改訂・古い順": revisions, "優先例外": f"冷蔵品は{special}", "荷物": "冷蔵品" if exception else "通常品", "規則": "後の改訂が前を上書きする"})
        ins, v = choose(rng, "この荷物に貼るラベルの色を選んでください。", "例外と改訂の順序を考慮して、使用する色はどれですか。", "今回適用されるラベルを一つ決めてください。")
        return state, ins, [(x, f"{x}ラベル") for x in labels], "revision", f, v
    if family == "利用可能集合の差":
        available = rng.sample(items, rng.randint(1, k))
        answer = rng.choice(available)
        reserved = [x for x in available if x != answer]
        reserved += rng.sample([x for x in items if x not in available], rng.randint(0, k - len(available)))
        rng.shuffle(reserved)
        f = {"available": available, "reserved": reserved}
        narrative = f"貸出台帳で利用可能と記録されている品は{'、'.join(available)}。予約済みの品は{'、'.join(reserved) if reserved else 'なし'}です。"
        state = state_form(rng, narrative, {"利用可能品": available, "予約済み品": reserved})
        ins, v = choose(rng, "利用可能品のうち、予約されていない品を選んでください。", "今貸せるのは利用可能かつ未予約の品です。該当するものはどれですか。", "予約済みを利用可能一覧から除いたとき、残る品を答えてください。")
        return state, ins, [(x, x) for x in items], "set_difference", f, v
    if family == "不在時の代理":
        k = max(3, k)
        names = pick(rng, NAMES, k)
        topics = pick(rng, PROJECTS, k)
        owners = dict(zip(topics, names))
        rotated = names[1:] + names[:1]
        deputies = dict(zip(names, rotated))
        absent = rng.sample(names, rng.randint(0, k - 1))
        topic = rng.choice(topics)
        f = {"owners": owners, "deputies": deputies, "absent": absent, "topic": topic}
        narrative = "担当者: " + "、".join(f"{x}は{y}" for x, y in owners.items()) + "。代理者: " + "、".join(f"{x}の代理は{y}" for x, y in deputies.items()) + f"。本日の不在者は{'、'.join(absent) if absent else 'なし'}。問い合わせ先の案件は{topic}です。代理への振替は一回だけ行い、その先の不在は判定しません。"
        state = state_form(rng, narrative, {"案件担当": owners, "代理者": deputies, "不在者": absent, "案件": topic, "ルール": "担当者が不在なら指定代理に一度だけ振替。代理の在席状況は問わない"})
        ins, v = choose(rng, "本日の規則に従う連絡相手を選んでください。", "この案件を担当本人または指定代理に連絡します。宛先は誰ですか。", "一回だけの代理振替を適用した後の宛先を答えてください。")
        return state, ins, [(x, f"{x}さん") for x in names], "delegate", f, v
    if family == "小数量の比較":
        nets = pick(rng, list(range(0, 13)), k)
        records = [{"name": name, "stock": net + (reserved := rng.randint(0, 5)), "reserved": reserved} for name, net in zip(items, nets)]
        direction = rng.choice(["smallest", "largest"])
        f = {"records": records, "direction": direction}
        narrative = "入出庫記録: " + "、".join(f"{x['name']}は在庫{x['stock']}個、そのうち予約{x['reserved']}個" for x in records) + "。予約分は自由在庫に含めません。"
        state = state_form(rng, narrative, {"在庫": [{"品名": x["name"], "総在庫": x["stock"], "予約分": x["reserved"]} for x in records], "自由在庫": "総在庫から予約分を引く"})
        word = "少ない" if direction == "smallest" else "多い"
        ins, v = choose(rng, f"自由在庫が最も{word}品を選んでください。", f"予約分を差し引いた残りが一番{word}のはどれですか。", f"今使える個数が最も{word}品を答えてください。")
        return state, ins, [(x, x) for x in items], "net_stock", f, v
    if family == "条件付き不足書類":
        docs = pick(rng, ["申込書", "本人確認票", "同意書", "承認書", "受領票", "見積書", "委任状"], rng.randint(2, 7))
        special_doc = rng.choice(docs)
        special = bool(rng.randrange(2))
        submitted = rng.sample(docs, rng.randint(0, len(docs)))
        f = {"priority": docs, "special_document": special_doc, "special": special, "submitted": submitted}
        narrative = f"書類確認の優先順は{'→'.join(docs)}。{special_doc}だけは代理申請の場合に限って必要で、それ以外は常に必要です。今回は{'代理申請' if special else '本人申請'}。提出済みは{'、'.join(submitted) if submitted else 'なし'}です。"
        state = state_form(rng, narrative, {"確認優先順": docs, "代理申請だけに必要": special_doc, "代理申請": special, "提出済み": submitted})
        ins, v = choose(rng, "未提出の必要書類のうち優先順が最初のものを選んでください。全部そろっていれば追加不要です。", "必要な不足書類を先頭から一つだけ案内します。どれですか。必要書類に不足がなければ追加不要です。", "申請区分に応じて必要書類を確認し、最優先で追加提出を求めるものを答えてください。なければ追加不要です。")
        return state, ins, [(x, x) for x in docs] + [("追加不要", "必要書類はすべて提出済み")], "required_document", f, v
    if family == "工程の依存順":
        steps = pick(rng, ["受付", "内容確認", "見積作成", "承認", "準備", "実施", "報告"], rng.randint(2, 7))
        done = steps[:rng.randint(0, len(steps))]
        f = {"steps": steps, "done": done}
        narrative = f"案件「{project}」の工程順は{'→'.join(steps)}です。途中の工程を飛ばすことはできません。完了済みは{'、'.join(done) if done else 'なし'}です。"
        state = state_form(rng, narrative, {"案件": project, "工程順": steps, "完了済み": done, "規則": "順に実行し未完了工程を飛ばさない"})
        ins, v = choose(rng, "次に行う工程を選んでください。すべて済んでいれば完了を選びます。", "まだ済んでいない最初の工程は何ですか。存在しない場合は完了です。", "この作業を一段進めるときに着手する工程を答えてください。残りがなければ完了です。")
        return state, ins, [(x, x) for x in steps] + [("完了", "全工程が完了")], "workflow", f, v
    if family == "二属性照合":
        pairs = rng.sample([(a, b) for a in COLORS for b in MATERIALS], k)
        records = [{"name": name, "color": pair[0], "material": pair[1]} for name, pair in zip(items, pairs)]
        color, material = rng.choice(pairs)
        f = {"records": records, "color": color, "material": material}
        narrative = "展示品の札: " + "、".join(f"{x['name']}は{x['color']}色・{x['material']}製" for x in records) + f"。探しているのは{color}色の{material}製です。"
        state = state_form(rng, narrative, {"展示品": [{"品名": x["name"], "色": x["color"], "素材": x["material"]} for x in records], "指定色": color, "指定素材": material})
        ins, v = choose(rng, "指定された色と素材の両方が一致する品を選んでください。", "二つの指定を同時に満たす展示品はどれですか。", "色だけ・素材だけの一致では足りません。該当品を答えてください。")
        return state, ins, [(x, x) for x in items], "pair_lookup", f, v
    if family == "文章内の順序参照":
        order = rng.sample(names, k)
        rank = rng.randint(1, k)
        f = {"order": order, "rank": rank}
        narrative = f"{project}会議では、発表者を発表順に「{'、'.join(order)}」と紹介しました。同じ人の再登場はありません。"
        state = state_form(rng, narrative, {"会議": project, "発表順": order})
        ins, v = choose(rng, f"最初を1番目として、{rank}番目の発表者を選んでください。", f"紹介された順番で{rank}人目に発表する人は誰ですか。", f"発表順の先頭から{rank}番目にいる人を答えてください。")
        return state, ins, [(x, f"{x}さん") for x in names], "rank_reference", f, v
    raise AssertionError(family)


CHOICE_FAMILIES = ["問い合わせ経路", "条件と優先例外", "最終更新", "参照先の担当", "否定条件で選択", "時間枠の包含", "複数属性の制約", "改訂と例外の優先", "利用可能集合の差", "不在時の代理", "小数量の比較", "条件付き不足書類", "工程の依存順", "二属性照合", "文章内の順序参照"]


def noul_case(family, rng, index):
    target = bool(index % 2)
    person = rng.choice(NAMES)
    project = rng.choice(PROJECTS)
    if family == "事実と否定質問":
        negated = bool(rng.randrange(2))
        fact = target != negated
        attribute = rng.choice(["研修を修了", "参加登録を完了", "本人確認を完了", "資料を受領", "内容を確認", "支払いを完了", "出席を表明", "荷物を発送", "申請の取り下げを実施", "予約変更を実施", "鍵を返却", "契約を更新", "同意書に署名", "面談に参加", "報告書を提出", "連絡を受領", "点検を実施", "承認を取得", "作業を中断", "欠席を連絡", "面談日程を確定", "支店へ移動", "貸出品を回収", "試験に合格", "本人情報を更新", "引継ぎを完了", "確認メールを送信", "交通費を精算", "議事録を作成", "提出物を再確認", "会場を設営", "機器を充電", "見積書を承認", "受領印を押印", "説明会を受講", "配送先を確認", "検収を完了", "案内状を送付", "現地調査を実施", "備品を補充"])
        f = {"fact": fact, "negated_query": negated, "attribute": attribute}
        narrative = f"{person}さんについての確定記録: {attribute}{'しています' if fact else 'していません'}。"
        state = state_form(rng, narrative, {"対象者": person, "項目": attribute, "実施済み": fact})
        statement = f"{attribute}していない" if negated else f"{attribute}している"
        ins, v = choose(rng, f"記録上、{person}さんは{statement}と言えますか。", f"『{person}さんは{statement}』はこの記録と一致しますか。", f"確定情報だけから、{person}さんが{statement}という判断は正しいですか。")
        return state, ins, "fact_negation", f, v
    if family == "全条件の充足":
        attrs = pick(rng, ["事前登録", "本人確認", "会費支払い", "講習受講", "同意書提出", "所属確認", "申込書提出", "利用説明受講"], rng.randint(2, 4))
        conditions = [True] * len(attrs)
        if not target:
            for j in rng.sample(range(len(attrs)), rng.randint(1, len(attrs))):
                conditions[j] = False
        f = {"conditions": conditions, "attributes": attrs}
        narrative = f"{project}の利用には{'・'.join(attrs)}がすべて必要です。{person}さん: " + "、".join(f"{a}は{'完了' if b else '未完了'}" for a, b in zip(attrs, conditions)) + "。"
        state = state_form(rng, narrative, {"すべて必要な条件": attrs, "対象": person, "完了状況": dict(zip(attrs, conditions))})
        ins, v = choose(rng, "この人は記載された利用条件をすべて満たしていますか。", "不足条件なく利用を許可できますか。", "規則に照らし、この人の利用資格は成立しますか。")
        return state, ins, "and", f, v
    if family == "いずれかの条件":
        attrs = pick(rng, ["紹介状", "会員証", "招待券", "事前予約票", "当日券", "入場証", "引換券", "受付確認票"], rng.randint(2, 4))
        conditions = [False] * len(attrs)
        if target:
            for j in rng.sample(range(len(attrs)), rng.randint(1, len(attrs))):
                conditions[j] = True
        f = {"conditions": conditions, "attributes": attrs}
        narrative = f"{project}の受付では{'・'.join(attrs)}のうち一つ以上があれば通れます。{person}さん: " + "、".join(f"{a}は{'あり' if b else 'なし'}" for a, b in zip(attrs, conditions)) + "。"
        state = state_form(rng, narrative, {"いずれか一つ以上必要": attrs, "所持状況": dict(zip(attrs, conditions)), "対象": person})
        ins, v = choose(rng, "記載された条件で受付を通れますか。", "少なくとも一つの必要条件が成立していますか。", "この人は受付基準を満たしていますか。")
        return state, ins, "or", f, v
    if family == "例外の優先":
        eligible, exception = (True, False) if target else rng.choice([(False, False), (False, True), (True, True)])
        required = rng.choice(["会員", "予約済み", "認定済み", "登録済み", "講習修了", "本人確認済み", "招待あり", "事前承認済み"])
        excluded = rng.choice(["会費滞納", "利用停止中", "資格取消中", "登録凍結中", "再審査中", "未返却品あり", "申請保留中", "入場制限中"])
        f = {"eligible": eligible, "exception": exception, "required": required, "excluded": excluded}
        narrative = f"規則: {required}であれば{project}を利用できます。ただし{excluded}なら利用できません。{person}さんは{required}に{'該当' if eligible else '非該当'}、{excluded}に{'該当' if exception else '非該当'}です。"
        state = state_form(rng, narrative, {"許可条件": required, "優先禁止条件": excluded, "対象": person, "許可条件に該当": eligible, "禁止条件に該当": exception})
        ins, v = choose(rng, "例外を含む規則のもとで利用は許可されますか。", "この人は現在、利用可能ですか。", "禁止例外を先に考慮すると、この利用を認められますか。")
        return state, ins, "except", f, v
    if family == "締切の境界":
        deadline = rng.randint(10, 18)
        inclusive = bool(rng.randrange(2))
        true_values = list(range(8, deadline + (1 if inclusive else 0)))
        false_values = list(range(deadline + (1 if inclusive else 0), 22))
        actual = rng.choice(true_values if target else false_values)
        f = {"actual": actual, "deadline": deadline, "inclusive": inclusive}
        rule = f"{deadline}時ちょうどまで受け付け、同時刻の提出も有効" if inclusive else f"{deadline}時より前だけ受け付け、{deadline}時ちょうどは無効"
        narrative = f"{project}の提出は{rule}です。{person}さんの提出記録は{actual}時ちょうどです。"
        state = state_form(rng, narrative, {"受付規則": rule, "提出者": person, "提出時刻": actual})
        ins, v = choose(rng, "この提出は時間条件を満たしていますか。", "記録された提出時刻は締切内ですか。", "時刻だけを基準に、この提出を有効と判定できますか。")
        return state, ins, "deadline", f, v
    if family == "更新後の状態":
        values = pick(rng, ["受付中", "停止中", "満席", "空席あり", "点検中", "使用可能"], rng.randint(2, 5))
        times = sorted(pick(rng, list(range(7, 22)), rng.randint(3, 5)))
        updates = [{"time": t, "value": rng.choice(values)} for t in times]
        latest = updates[-1]["value"]
        query = latest if target else rng.choice([x for x in values if x != latest])
        rng.shuffle(updates)
        f = {"updates": updates, "query": query}
        narrative = f"{project}の状態記録: " + "、".join(f"{x['time']}時には{x['value']}" for x in updates) + "。時刻が新しい記録が古い記録を上書きします。"
        state = state_form(rng, narrative, {"対象": project, "更新記録": [{"時刻": x["time"], "状態": x["value"]} for x in updates], "規則": "最新時刻の記録が有効"})
        ins, v = choose(rng, f"現在の状態は「{query}」ですか。", f"最新の有効な記録から「{query}」と言えますか。", f"最後の更新を適用すると、状態は「{query}」になっていますか。")
        return state, ins, "latest_is", f, v
    if family == "識別文字列の完全一致":
        left = rng.choice(["AB", "CD", "EF", "GH", "JK", "MN", "PQ", "RS"]) + str(rng.randint(1, 9)) + "-" + rng.choice(["A", "B", "C", "D"])
        if target:
            right = left
        else:
            transforms = [left.lower(), left.replace("-", "_"), left.replace("-", ""), left[:-1] + ("D" if left[-1] != "D" else "A")]
            right = rng.choice(transforms)
        f = {"left": left, "right": right}
        narrative = f"商品ラベルの管理コードは「{left}」、注文票の管理コードは「{right}」です。照合では大文字と小文字、記号の違いも区別します。"
        state = state_form(rng, narrative, {"商品ラベル": left, "注文票": right, "照合規則": "大文字小文字と記号も含む完全一致"})
        ins, v = choose(rng, "二つの管理コードは完全一致していますか。", "同一コードとして扱ってよいですか。", "指定された照合規則で一致と判定できますか。")
        return state, ins, "exact", f, v
    if family == "集合と否定所属":
        members = pick(rng, NAMES, rng.randint(2, 7))
        positive = bool(rng.randrange(2))
        wanted_member = target == positive
        entity = rng.choice(members if wanted_member else [x for x in NAMES if x not in members])
        f = {"members": members, "entity": entity, "positive": positive}
        narrative = f"{project}の参加者名簿は{'、'.join(members)}です。この名簿は完全で、記載のない人は参加者ではありません。"
        state = state_form(rng, narrative, {"催し": project, "完全な参加者名簿": members, "補足": "名前のない人は参加者ではない"})
        claim = "参加者である" if positive else "参加者ではない"
        ins, v = choose(rng, f"{entity}さんは{claim}と言えますか。", f"『{entity}さんは{claim}』という記述は正しいですか。", f"名簿に基づき、{entity}さんが{claim}という判断に同意できますか。")
        return state, ins, "membership", f, v
    if family == "重複を除いた件数":
        minimum = rng.randint(2, 6)
        count = rng.randint(minimum, 8) if target else rng.randint(1, minimum - 1)
        entries = pick(rng, ITEMS, count)
        entries += rng.choices(entries, k=rng.randint(1, 4))
        rng.shuffle(entries)
        f = {"entries": entries, "minimum": minimum}
        narrative = f"{project}棚で読み取った品名は{'、'.join(entries)}でした。同じ品名の繰り返しは一種類として数えます。"
        state = state_form(rng, narrative, {"棚": project, "読み取り品名": entries, "数え方": "同一品名の重複を除く"})
        ins, v = choose(rng, f"品物の種類は{minimum}種類以上ありますか。", f"異なる品名だけ数えると{minimum}種類以上ですか。", f"重複を除いた種類数は{minimum}以上という条件を満たしますか。")
        return state, ins, "distinct_count", f, v
    if family == "条件付き義務":
        premise, conclusion = rng.choice([(False, False), (False, True), (True, True)]) if target else (True, False)
        category = rng.choice(["社外向け", "夜間受付", "新規申請", "代理申請", "当日申請", "法人向け", "追加申請", "個人向け"])
        action = rng.choice(["上長の承認", "事前連絡", "確認票の添付", "担当者の署名", "受付印の押印", "記録票の保存", "依頼者への通知", "控えの交付"])
        f = {"premise": premise, "conclusion": conclusion, "category": category, "action": action}
        narrative = f"規則: {category}のときだけ{action}が必須です。それ以外の場合にはこの義務はなく、実施していても構いません。今回の案件は{category}に{'該当' if premise else '非該当'}で、{action}は{'実施済み' if conclusion else '未実施'}です。"
        state = state_form(rng, narrative, {"規則": f"{category}なら{action}が必要。それ以外では義務なし", "条件に該当": premise, "必要処置を実施": conclusion})
        ins, v = choose(rng, "この案件は記載された義務のルールに違反していませんか。違反がなければはいです。", "この記録は規則を守っていますか。", "この義務に関して、規則上問題なしと判定できますか。")
        return state, ins, "implication", f, v
    if family == "参照関係の真偽":
        count = rng.randint(2, 6)
        projects, names, refs = pick(rng, PROJECTS, count), pick(rng, NAMES, count), pick(rng, ITEMS, count)
        owners = dict(zip(projects, names))
        links = dict(zip(refs, rng.sample(projects, count)))
        reference = rng.choice(refs)
        correct_person = owners[links[reference]]
        queried = correct_person if target else rng.choice([x for x in names if x != correct_person])
        f = {"owners": owners, "links": links, "reference": reference, "person": queried}
        narrative = "担当表: " + "、".join(f"{p}は{n}" for p, n in owners.items()) + "。資料の関連先: " + "、".join(f"{a}は{p}" for a, p in links.items()) + "。"
        state = state_form(rng, narrative, {"案件担当": owners, "資料関連先": links})
        ins, v = choose(rng, f"{reference}に関連する案件の担当は{queried}さんですか。", f"{reference}の関連先を担当表で引くと{queried}さんになりますか。", f"{queried}さんは{reference}が属する案件の担当者と言えますか。")
        return state, ins, "reference_is", f, v
    if family == "記録と主張の照合":
        attrs = ["完全に開いている", "完全に閉じている", "半分だけ開いている", "4分の1だけ開いている"]
        recorded = rng.choice(attrs)
        asserted = recorded if target else rng.choice([x for x in attrs if x != recorded])
        location = rng.choice(["北口", "南口", "東口", "西口", "裏口", "搬入口"])
        observations = {x: rng.choice(attrs) for x in ["北口", "南口", "東口", "西口", "裏口", "搬入口"]}
        observations[location] = recorded
        f = {"recorded": recorded, "asserted": asserted, "location": location, "observations": observations}
        narrative = f"{project}施設の入口について、いま確認した確定記録は" + "、".join(f"{x}は{status}" for x, status in observations.items()) + "です。現在の判断にはこの確定記録だけを使います。"
        state = state_form(rng, narrative, {"施設": project, "入口ごとの現在の確定記録": observations, "判定資料": "現在の確定記録のみ"})
        ins, v = choose(rng, f"『現在の{location}は{asserted}』という主張は確定記録と一致しますか。", f"いま{location}が{asserted}という判断は正しいですか。", f"確定情報から、{location}は{asserted}と言えますか。")
        return state, ins, "evidence", f, v
    if family == "範囲の開閉境界":
        low = rng.randint(1, 8)
        high = low + rng.randint(3, 8)
        lc, hc = bool(rng.randrange(2)), bool(rng.randrange(2))
        good = [x for x in range(low - 1, high + 2) if (x >= low if lc else x > low) and (x <= high if hc else x < high)]
        bad = [x for x in range(low - 1, high + 2) if x not in good]
        value = rng.choice(good if target else bad)
        f = {"low": low, "high": high, "low_closed": lc, "high_closed": hc, "value": value}
        lower = f"{low}個以上" if lc else f"{low}個より多い"
        upper = f"{high}個以下" if hc else f"{high}個未満"
        narrative = f"{project}の受付数は、{lower}、かつ{upper}の場合に限り適合です。今回の数は{value}個です。"
        state = state_form(rng, narrative, {"下限条件": lower, "上限条件": upper, "今回の個数": value, "関係": "両方を満たすこと"})
        ins, v = choose(rng, "今回の個数は適合範囲に入っていますか。", "下限と上限の両方の条件に合いますか。", "指定された範囲条件を満たしていますか。")
        return state, ins, "range", f, v
    if family == "予定時間の重なり":
        a_start = rng.randint(8, 15)
        a_end = a_start + rng.randint(1, 4)
        if target:
            b_start = rng.randint(a_start, a_end - 1)
            b_end = b_start + rng.randint(1, 4)
        elif rng.randrange(2):
            b_start = a_end + rng.randint(0, 2)
            b_end = b_start + rng.randint(1, 3)
        else:
            b_end = a_start - rng.randint(0, 2)
            b_start = b_end - rng.randint(1, 3)
        f = {"a_start": a_start, "a_end": a_end, "b_start": b_start, "b_end": b_end}
        narrative = f"{person}さんの予定: {project}会議は{a_start}時から{a_end}時、面談は{b_start}時から{b_end}時。終了と次の開始が同時刻の場合は重複とは扱いません。"
        state = state_form(rng, narrative, {"対象者": person, "会議": [a_start, a_end], "面談": [b_start, b_end], "規則": "終了時刻と開始時刻が一致するだけなら重複なし"})
        ins, v = choose(rng, "二つの予定の時間は重なっていますか。", "同時に二つの予定に出席しなければならない時間がありますか。", "指定された端点の扱いで予定の重複はありますか。")
        return state, ins, "overlap", f, v
    if family == "出来事の前後関係":
        events = pick(rng, ["荷物受取", "電話連絡", "検品", "伝票記入", "棚への配置", "報告", "休憩", "引継ぎ"], rng.randint(3, 8))
        i, j = sorted(rng.sample(range(len(events)), 2))
        first, second = (events[i], events[j]) if target else (events[j], events[i])
        f = {"events": events, "first": first, "second": second}
        narrative = f"{person}さんの作業日誌は実施順に{'→'.join(events)}です。記載した各作業は一回ずつ実施しました。"
        state = state_form(rng, narrative, {"担当者": person, "実施順": events, "各作業の実施回数": 1})
        ins, v = choose(rng, f"{first}は{second}より前に行われましたか。", f"日誌では{first}の方が{second}より先ですか。", f"『{first}が先、{second}が後』という順序は正しいですか。")
        return state, ins, "precedence", f, v
    raise AssertionError(family)


NOUL_FAMILIES = ["事実と否定質問", "全条件の充足", "いずれかの条件", "例外の優先", "締切の境界", "更新後の状態", "識別文字列の完全一致", "集合と否定所属", "重複を除いた件数", "条件付き義務", "参照関係の真偽", "記録と主張の照合", "範囲の開閉境界", "予定時間の重なり", "出来事の前後関係"]


def threshold_criteria(thresholds, unit, prefix="値"):
    out = [f"{prefix}が{thresholds[0]}{unit}未満"]
    out += [f"{prefix}が{low}{unit}以上、{high}{unit}未満" for low, high in zip(thresholds, thresholds[1:])]
    out += [f"{prefix}が{thresholds[-1]}{unit}以上"]
    return out


def score_case(family, rng, index):
    # Global cycling makes candidate-count and conditional bucket distributions balanced.
    k = 2 + index % 7
    desired = (index // 7) % k
    project = rng.choice(PROJECTS)
    person = rng.choice(NAMES)
    if family == "件数の段階境界":
        spacing = rng.choice([1, 2, 3, 4, 5])
        thresholds = [spacing * i for i in range(1, k)]
        low = 0 if desired == 0 else thresholds[desired - 1]
        high = thresholds[desired] - 1 if desired < k - 1 else low + spacing
        value = rng.randint(low, high)
        what = rng.choice(["未処理の連絡", "検品で見つかった不備", "確認待ちの申請", "未回答の質問"])
        f = {"value": value, "thresholds": thresholds}
        narrative = f"{project}で{what}を数えたところ、現在{value}件でした。処理済みは数に含めていません。"
        state = state_form(rng, narrative, {"案件": project, "計数対象": what, "件数": value, "処理済みを除外": True})
        ins, v = choose(rng, "現在の件数を指定の段階基準に当てはめてください。", "記録された数に対応する段階を選んでください。", "件数だけを評価尺度に照らして判定してください。")
        return state, ins, threshold_criteria(thresholds, "件", "対象件数"), "threshold_score", f, v
    if family == "記述の満足段階":
        meanings = ["極めて強い不満", "強い不満", "不満", "やや不満", "どちらでもない", "やや満足", "満足", "強い満足", "極めて強い満足", "最高の満足"]
        ordered = [meanings[i] for i in sorted(rng.sample(range(len(meanings)), k))]
        meaning = ordered[desired]
        phrases = {"極めて強い不満": ["極めて強い不満を感じ、到底受け入れられない", "不満の程度は極めて強かった"], "極めて強い満足": ["極めて強い満足を感じたが、最高とまでは言わない", "最高の一歩手前で、満足の程度は極めて強かった"], "強い不満": ["強い不満があり、受け入れられない", "到底納得できず、強い不満を感じた"], "不満": ["期待に届かず、不満だった", "改善を求めたい。不満が残った"], "やや不満": ["大きな問題ではないが、やや不満がある", "惜しい点があり、少し不満だった"], "どちらでもない": ["満足でも不満でもない", "特に良くも悪くも感じなかった"], "やや満足": ["少し良いと感じ、やや満足した", "完全ではないが、少し満足している"], "満足": ["期待を満たしていて、満足した", "良い結果で、満足している"], "強い満足": ["予想を超えており、強く満足した", "とても良い結果で、強い満足がある"], "最高の満足": ["これ以上は考えられず、最高に満足した", "満足の程度は最高だった"]}
        quote = rng.choice(phrases[meaning])
        f = {"ordered_meanings": ordered, "meaning": meaning}
        narrative = f"{person}さんは{project}の体験について「{quote}」と回答しました。追加の発言はありません。"
        state = state_form(rng, narrative, {"回答者": person, "対象": project, "感想原文": quote})
        ins, v = choose(rng, "発言の意味に最も合う満足段階を選んでください。", "回答者が表明した満足の程度を分類してください。", "感想に明示された評価を尺度へ対応づけてください。")
        return state, ins, ordered, "sentiment_score", f, v
    if family == "順番に進む工程":
        steps = pick(rng, ["受付", "調査", "審査", "承認", "準備", "実施", "報告", "日程調整", "検収", "引継ぎ"], k - 1)
        done = steps[:desired]
        f = {"steps": steps, "done": done}
        narrative = f"{project}の工程順は{'→'.join(steps)}。先頭から順に進め、完了済みは{'、'.join(done) if done else 'なし'}です。着手中の工程は完了に含めません。"
        state = state_form(rng, narrative, {"案件": project, "工程順": steps, "完了済み": done, "着手中は完了に含めない": True})
        criteria = ["完了した工程はまだない"] + [f"先頭から{j}工程が完了（最後に完了したのは{steps[j-1]}）" for j in range(1, k)]
        ins, v = choose(rng, "完了済みの到達段階を選んでください。", "この案件は完了ベースでどの段階まで進みましたか。", "工程の完了状況を段階尺度で評価してください。")
        return state, ins, criteria, "progress_score", f, v
    if family == "独立チェックの合計":
        attrs = pick(rng, ["題名あり", "日付あり", "署名あり", "添付あり", "宛先あり", "承認印あり", "ページ番号あり", "管理番号あり", "部署名あり", "連絡先あり"], k - 1)
        satisfied = [True] * desired + [False] * (k - 1 - desired)
        rng.shuffle(satisfied)
        f = {"satisfied": satisfied, "attributes": attrs}
        narrative = f"{project}資料の点検: " + "、".join(f"{a}は{'満たす' if ok else '満たさない'}" for a, ok in zip(attrs, satisfied)) + "。各項目は一つずつ数えます。"
        state = state_form(rng, narrative, {"資料": project, "チェック項目": dict(zip(attrs, satisfied)), "各項目の重み": 1})
        ins, v = choose(rng, "満たしたチェック項目の数を段階として選んでください。", "合格した項目数に対応する段階を答えてください。", "条件を満たした項目を一つ一点として集計してください。")
        return state, ins, [f"満たした項目が{j}個" for j in range(k)], "dimensions_score", f, v
    if family == "緊急条件の加点":
        urgent = bool(rng.randrange(2)) if desired > 0 else False
        impact = desired - int(urgent)
        urgent_within = rng.randint(2, 8)
        hours_left = rng.randint(0, urgent_within) if urgent else rng.randint(urgent_within+1, 14)
        f = {"impact": impact, "urgent": urgent, "max_score": k - 1, "urgent_within": urgent_within, "hours_left": hours_left}
        narrative = f"{project}の基本優先度は{impact}です。締切まで残り{urgent_within}時間以内なら1だけ加点し、それより長ければ加点しません。上限は{k-1}です。今回は締切まで{hours_left}時間です。"
        state = state_form(rng, narrative, {"案件": project, "基本優先度": impact, "締切までの残り時間": hours_left, "規則": f"残り{urgent_within}時間以内なら1加点、それより長ければ0加点。上限{k-1}"})
        ins, v = choose(rng, "条件付き加点後の優先度を選んでください。", "今回の最終優先段階を求めてください。", "締切までの時間による条件を反映した段階を答えてください。")
        return state, ins, [f"最終優先度{j}" for j in range(k)], "priority_score", f, v
    if family == "約束時刻からの遅れ":
        spacing = rng.choice([1, 2])
        thresholds = [spacing * j for j in range(1, k)]
        promised = rng.randint(5, min(12, 23-(thresholds[-1]+1)))
        low = 0 if desired == 0 else thresholds[desired-1]
        high = thresholds[desired] - 1 if desired < k-1 else low + 1
        delay = rng.randint(low, high)
        arrival = promised + delay
        if desired == 0 and rng.randrange(2):
            arrival = promised - rng.randint(0, 2)
        f = {"arrival": arrival, "promised": promised, "thresholds": thresholds}
        narrative = f"{project}便は{promised}時到着の約束でした。実際の到着は同じ日の{arrival}時です。早着した場合の遅れは0時間とします。"
        state = state_form(rng, narrative, {"便": project, "約束時刻": promised, "実際の到着時刻": arrival, "同日": True, "早着時の遅れ": 0})
        ins, v = choose(rng, "到着の遅れを段階基準で評価してください。", "約束時刻と到着時刻の差から、遅延段階を選んでください。", "遅れの時間に対応する段階を答えてください。")
        return state, ins, threshold_criteria(thresholds, "時間", "遅れ"), "delay_score", f, v
    if family == "証拠の最高到達段階":
        kinds = pick(rng, ["口頭メモ", "担当者報告", "写真記録", "一次資料", "署名済み文書", "第三者確認", "監査記録", "計測記録", "立会記録", "検収記録"], k-1)
        levels = {kind: j+1 for j, kind in enumerate(kinds)}
        present = [] if desired == 0 else [kinds[desired-1]] + rng.sample(kinds[:desired-1], rng.randint(0, desired-1))
        rng.shuffle(present)
        f = {"levels": levels, "present": present}
        narrative = "この調査固有の証拠段階表: " + "、".join(f"{kind}は段階{level}" for kind, level in levels.items()) + f"。{project}で得られた証拠は{'、'.join(present) if present else 'なし'}。複数ある場合は最大の段階を使い、なければ0です。"
        state = state_form(rng, narrative, {"調査": project, "この調査の証拠段階": levels, "得られた証拠": present, "集約規則": "得られた段階の最大。証拠なしは0"})
        ins, v = choose(rng, "この調査の証拠段階を選んでください。", "記録済みの証拠から得られる最高段階はどれですか。", "明示された段階表だけで証拠を評価してください。")
        return state, ins, ["証拠なしの段階0"] + [f"表に基づく最高証拠段階{j}" for j in range(1, k)], "evidence_score", f, v
    if family == "要件への一致数":
        attributes = pick(rng, ["色", "素材", "形", "包装", "配送", "サイズ", "印字"], k-1)
        choices = {"色": ["赤", "青", "白"], "素材": ["紙", "木", "布"], "形": ["丸", "四角", "三角"], "包装": ["箱", "袋", "なし"], "配送": ["店頭", "郵送", "宅配"], "サイズ": ["小", "中", "大"], "印字": ["あり", "なし", "片面のみ"]}
        requirements = {a: rng.choice(choices[a]) for a in attributes}
        matched = set(rng.sample(attributes, desired))
        actual = {a: value if a in matched else rng.choice([x for x in choices[a] if x != value]) for a, value in requirements.items()}
        f = {"requirements": requirements, "actual": actual}
        narrative = "注文要件: " + "、".join(f"{a}={x}" for a, x in requirements.items()) + "。提案品: " + "、".join(f"{a}={x}" for a, x in actual.items()) + "。"
        state = state_form(rng, narrative, {"注文要件": requirements, "提案品": actual})
        ins, v = choose(rng, "注文要件と一致している属性の数を段階として選んでください。", "提案品が満たす要件数はいくつの段階ですか。", "各属性の完全一致を一点として採点してください。")
        return state, ins, [f"一致した要件が{j}項目" for j in range(k)], "match_score", f, v
    if family == "例外による上限":
        # Sometimes the exception clips a higher raw count; sometimes it is inactive.
        exception = desired < k-1 and bool(rng.randrange(2))
        cap = desired if exception else rng.randint(0, k-1)
        raw = rng.randint(desired, k-1) if exception else desired
        checks = [True]*raw + [False]*(k-1-raw)
        rng.shuffle(checks)
        attrs = pick(rng, ["外観", "寸法", "動作", "包装", "付属品", "表示", "記録"], k-1)
        f = {"checks": checks, "cap": cap, "exception": exception, "attributes": attrs}
        narrative = "検査合格状況: " + "、".join(f"{a}は{'合格' if b else '不合格'}" for a, b in zip(attrs, checks)) + f"。合格項目一つにつき1点ですが、要再確認の印があれば上限{cap}点に制限します。今回その印は{'あります' if exception else 'ありません'}。"
        state = state_form(rng, narrative, {"検査合格": dict(zip(attrs, checks)), "要再確認の印あり": exception, "採点規則": f"合格数が点数。ただし印があれば上限{cap}点"})
        ins, v = choose(rng, "上限制限を適用した最終点を選んでください。", "例外条件を反映した評価段階を答えてください。", "単純な合格数ではなく、上限ルール適用後の点数を求めてください。")
        return state, ins, [f"最終点{j}点" for j in range(k)], "capped_score", f, v
    if family == "不足の段階":
        required = pick(rng, ["申込書", "確認票", "同意書", "承認書", "添付図", "見積書", "受領票"], k-1)
        provided = rng.sample(required, k-1-desired)
        if rng.randrange(2):
            provided += [rng.choice(["案内状", "挨拶状", "参考資料"])]
        rng.shuffle(provided)
        f = {"required": required, "provided": provided}
        narrative = f"{project}申請で必要なものは{'、'.join(required)}。届いたものは{'、'.join(provided) if provided else 'なし'}です。必要一覧にない書類は不足を埋めません。"
        state = state_form(rng, narrative, {"申請": project, "必要書類": required, "届いた書類": provided, "余分な書類で代用できる": False})
        ins, v = choose(rng, "必要書類の不足数に対応する段階を選んでください。", "未提出の必要書類はいくつの段階ですか。", "必要一覧と届いた一覧を照合し、不足の程度を判定してください。")
        return state, ins, [f"不足が{j}種類" for j in range(k)], "missing_score", f, v
    if family == "時刻順の評価更新":
        times = sorted(pick(rng, list(range(7, 22)), rng.randint(3, 6)))
        updates = [{"time": t, "value": rng.randrange(k)} for t in times]
        updates[-1]["value"] = desired
        rng.shuffle(updates)
        f = {"updates": updates}
        narrative = f"{project}の評価更新履歴: " + "、".join(f"{x['time']}時に段階{x['value']}" for x in updates) + "。評価は最新時刻の値だけを採用します。"
        state = state_form(rng, narrative, {"案件": project, "評価更新": [{"時刻": x["time"], "段階": x["value"]} for x in updates], "採用規則": "最新時刻だけを採用"})
        ins, v = choose(rng, "現在採用すべき評価段階を選んでください。", "履歴の記載順に惑わされず、最新評価を答えてください。", "最後に更新された有効な段階はいくつですか。")
        return state, ins, [f"評価段階{j}" for j in range(k)], "temporal_score", f, v
    if family == "目標からの差":
        target = rng.randint(8, 15)
        distance = desired if desired < k-1 else desired + rng.randint(0, 2)
        actual = target + rng.choice([-1, 1])*distance
        f = {"target": target, "actual": actual, "max_score": k-1}
        narrative = f"{project}の目標数は{target}個、実績は{actual}個です。多すぎても少なすぎても、目標から何個離れたかで評価します。差が{k-1}個以上なら最終段階{k-1}にまとめます。"
        state = state_form(rng, narrative, {"案件": project, "目標数": target, "実績数": actual, "採点": f"差の絶対値。ただし{k-1}以上は段階{k-1}"})
        ins, v = choose(rng, "目標からのずれの段階を選んでください。", "不足・超過の向きではなく差の大きさで評価してください。", "示された上限を含め、実績のずれを段階に変換してください。")
        return state, ins, [f"目標との差が{j}個" for j in range(k-1)] + [f"目標との差が{k-1}個以上"], "distance_score", f, v
    if family == "取消しを反映した件数":
        count = rng.randint(max(3, k-1), 8)
        final_count = rng.randint(desired, count) if desired == k-1 else desired
        accepted_count = rng.randint(final_count, count)
        revoked_count = accepted_count - final_count
        names = pick(rng, NAMES, count)
        accepted_people = set(rng.sample(names, accepted_count))
        revoked_people = set(rng.sample(sorted(accepted_people), revoked_count))
        accepted = [x in accepted_people for x in names]
        revoked = [x in revoked_people for x in names]
        f = {"accepted": accepted, "revoked": revoked, "max_score": k-1}
        narrative = f"{project}の申込み記録: " + "、".join(f"{name}は{'受付済み' if a else '未受付'}・{'取消済み' if r else '取消なし'}" for name, a, r in zip(names, accepted, revoked)) + f"。取消済みの申込みは有効件数から除きます。{k-1}件以上は最終段階{k-1}にまとめます。"
        state = state_form(rng, narrative, {"催し": project, "申込み": [{"氏名": name, "受付済み": a, "取消済み": r} for name, a, r in zip(names, accepted, revoked)], "まとめ方": f"{k-1}件以上は段階{k-1}"})
        ins, v = choose(rng, "取消し後に残る有効申込み数を段階として選んでください。", "受付済みから取消済みを除いた件数はいくつの段階ですか。", "現在有効な申込みだけを数えて評価してください。")
        return state, ins, [f"有効申込みが{j}件" for j in range(k-1)] + [f"有効申込みが{k-1}件以上"], "reversible_score", f, v
    if family == "参照表の順序尺度":
        codes = pick(rng, COLORS, k)
        scale = dict(zip(codes, range(k)))
        code = codes[desired]
        narrative = "今回の検査用の対応表: " + "、".join(f"{c}印は段階{j}" for c, j in scale.items()) + f"。{project}の確定検査票には{code}印が付いています。色に一般的な良し悪しは仮定しません。"
        f = {"scale": scale, "code": code}
        state = state_form(rng, narrative, {"検査対象": project, "今回の対応表": scale, "確定票の印": code})
        ins, v = choose(rng, "今回の対応表を使って検査票の段階を選んでください。", "検査票の印を指定尺度に変換してください。", "一般常識ではなく示された表に従って段階を答えてください。")
        return state, ins, [f"表による段階{j}" for j in range(k)], "lookup_score", f, v
    if family == "軽重のある項目":
        # One weight-2 issue plus weight-1 issues gives small sums with unequal weights.
        n = max(2, k-1)
        weights = [2] + [1]*(n-1)
        patterns = [list(bits) for bits in __import__("itertools").product([False, True], repeat=n) if min(sum(w for w, b in zip(weights, bits) if b), k-1) == desired]
        active = rng.choice(patterns)
        attrs = pick(rng, ["署名欠落", "日付欠落", "添付欠落", "誤字", "余白不備", "宛名不備", "頁番号欠落"], n)
        f = {"active": active, "weights": weights, "max_score": k-1, "attributes": attrs}
        narrative = "この点検の配点: " + "、".join(f"{a}は{w}点" for a, w in zip(attrs, weights)) + "。見つかった不備: " + "、".join(a for a, b in zip(attrs, active) if b) + f"{'なし' if not any(active) else ''}。該当項目の点を合計し、{k-1}点以上は段階{k-1}にまとめます。"
        state = state_form(rng, narrative, {"不備ごとの配点": dict(zip(attrs, weights)), "不備あり": dict(zip(attrs, active)), "上限": k-1})
        ins, v = choose(rng, "配点の違いを反映した最終段階を選んでください。", "見つかった不備の点数を合計し、上限を適用してください。", "項目数ではなく指定された点数で評価してください。")
        return state, ins, [f"不備点の合計が{j}点" for j in range(k-1)] + [f"不備点の合計が{k-1}点以上"], "weighted_score", f, v
    raise AssertionError(family)


SCORE_FAMILIES = ["件数の段階境界", "記述の満足段階", "順番に進む工程", "独立チェックの合計", "緊急条件の加点", "約束時刻からの遅れ", "証拠の最高到達段階", "要件への一致数", "例外による上限", "不足の段階", "時刻順の評価更新", "目標からの差", "取消しを反映した件数", "参照表の順序尺度", "軽重のある項目"]


def semantic_identity(rule, facts, instruction, criteria):
    # Ignore presentation order when the order has no semantic role.
    normalized = json.loads(canonical(facts))
    for field in ["records", "rooms", "updates"]:
        if field in normalized:
            normalized[field] = sorted(normalized[field], key=canonical)
    for field in ["available", "reserved", "members", "present", "provided", "submitted", "absent"]:
        if field in normalized:
            normalized[field] = sorted(normalized[field])
    # A checklist reordering is presentation only: keep predicate/value pairs.
    if rule in {"and", "or", "dimensions_score", "capped_score", "weighted_score"}:
        attrs = normalized.pop("attributes", None)
        if attrs is not None:
            values_name = {"and": "conditions", "or": "conditions", "dimensions_score": "satisfied", "capped_score": "checks", "weighted_score": "active"}[rule]
            values = normalized.pop(values_name)
            weights = normalized.pop("weights", [1]*len(attrs))
            normalized["named_predicates"] = sorted(zip(attrs, values, weights))
    if rule == "missing_score":
        normalized["required"] = sorted(normalized["required"])
    if rule == "distinct_count":
        normalized["entries"] = sorted(set(normalized["entries"]))
    if rule == "reversible_score":
        normalized["applicant_states"] = sorted(zip(normalized.pop("accepted"), normalized.pop("revoked")))
    if rule == "overlap":
        normalized = {"intervals": sorted([[normalized["a_start"], normalized["a_end"]], [normalized["b_start"], normalized["b_end"]]])}
    # Oracle facts alone can omit meaningful entity names or rubric conditions.
    # The semantic identity is deliberately stricter: two identical mathematical
    # structures are treated as duplicates even when only names/prose differ.
    return digest({"rule": rule, "facts": normalized})


def baseline():
    """Read only frozen v1 inputs/oracle metadata, never any model predictions."""
    path = ROOT.parent / "acceptance" / "private" / "generated_2220.jsonl"
    raw = path.read_bytes()
    expected = "141ee4c379fa8d72df6bca3fe793054c9d2847ca7d16d2fa6622bc92558d4bb3"
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("v1 baseline changed; audit exclusion provenance before continuing")
    rows = [json.loads(line) for line in raw.splitlines()]
    semantic = {semantic_identity(r["oracle"]["rule"], r["oracle"]["facts"], r["instructions"], r["criteria"]) for r in rows}
    semantic.update(r["semantic_sha256"] for r in rows)
    inputs = {digest({k: r[k] for k in ["type", "state", "instructions", "criteria"]}) for r in rows}
    return semantic, inputs, expected


def build():
    cases = []
    seen_semantic, seen_inputs, _ = baseline()
    duplicate_attempts = 0
    choice_position_counter = collections.Counter()
    for kind, families, factory in [("choice", CHOICE_FAMILIES, choice_case), ("noul", NOUL_FAMILIES, noul_case), ("score", SCORE_FAMILIES, score_case)]:
        global_index = 0
        for family_index, family in enumerate(families):
            desired_count = 50 if family_index < 5 else 49
            for position in range(desired_count):
                attempt = 0
                desired_candidate_count = None
                while True:
                    case_seed = SEED + {"choice": 10000000, "noul": 20000000, "score": 30000000}[kind] + family_index*100000 + position*1000 + attempt
                    rng = random.Random(case_seed)
                    spec = factory(family, rng, global_index)
                    if kind == "choice":
                        state, instructions, pairs, rule, facts, variant = spec
                        rng.shuffle(pairs)
                        criteria = dict(pairs)
                    elif kind == "noul":
                        state, instructions, rule, facts, variant = spec
                        criteria = {"false": "いいえ。質問の命題は成立しない。", "true": "はい。質問の命題が成立する。"}
                    else:
                        state, instructions, criteria, rule, facts, variant = spec
                    if kind == "choice":
                        # Pin candidate cardinality to the first draw, so
                        # position rejection cannot favor easier small sets.
                        if desired_candidate_count is None:
                            desired_candidate_count = len(criteria)
                        elif len(criteria) != desired_candidate_count:
                            attempt += 1
                            if attempt >= 1000:
                                raise RuntimeError(f"insufficient fixed-cardinality variety: {kind}/{family}/{position}/k={desired_candidate_count}")
                            continue
                    answer = solve(rule, facts)
                    label = str(answer).lower() if kind == "noul" else str(answer)
                    if kind == "choice":
                        options = list(criteria.items())
                        correct_pair = next(pair for pair in options if pair[0] == label)
                        options = [pair for pair in options if pair[0] != label]
                        rng.shuffle(options)
                        target_position = choice_position_counter[len(criteria)] % len(criteria)
                        options.insert(target_position, correct_pair)
                        criteria = dict(options)
                        # The decision runtime sorts Choice keys. Balance the
                        # actual canonical prompt position, not insertion alone.
                        if sorted(criteria).index(label) != target_position:
                            attempt += 1
                            if attempt >= 1000:
                                raise RuntimeError(f"insufficient canonical-position variety: {kind}/{family}/{position}/k={desired_candidate_count}")
                            continue
                        criteria = dict(sorted(criteria.items()))
                    semantic = semantic_identity(rule, facts, instructions, criteria)
                    inputs = {"type": kind, "state": state, "instructions": instructions, "criteria": criteria}
                    exact = digest(inputs)
                    if semantic not in seen_semantic and exact not in seen_inputs:
                        break
                    duplicate_attempts += 1
                    attempt += 1
                    if attempt >= 1000:
                        raise RuntimeError(f"Insufficient semantic variety for {kind}/{family}/{position}")
                seen_semantic.add(semantic)
                seen_inputs.add(exact)
                cases.append({"id": f"v2-gen-{kind}-{family_index+1:02d}-{position+1:03d}", **inputs, "label": label, "source": "generated", "family": family, "seed": case_seed, "variant": f"template-{variant}", "semantic_sha256": semantic, "oracle": {"rule": rule, "facts": facts, "explanation": explanation(rule, facts, answer)}})
                if kind == "choice":
                    choice_position_counter[len(criteria)] += 1
                global_index += 1
    random.Random(SEED).shuffle(cases)
    return cases, duplicate_attempts


def oracle_unit_tests():
    """Hand-specified examples, including boundaries and negative cases."""
    tests = [
        ("route", {"routes": {"a": ["x"], "b": ["y"]}, "topic": "y"}, "b"),
        ("policy_exception", {"member": True, "excluded": True, "amount": 9, "minimum": 2}, "通常"),
        ("policy_exception", {"member": True, "excluded": False, "amount": 2, "minimum": 2}, "優待"),
        ("latest", {"updates": [{"time": 14, "value": "b"}, {"time": 9, "value": "a"}]}, "b"),
        ("reference", {"links": {"doc": "p"}, "owners": {"p": "person"}, "reference": "doc"}, "person"),
        ("unique_filter", {"records": [{"name": "a", "wet": True}, {"name": "b", "wet": False}], "required": {"wet": False}}, "b"),
        ("slot", {"rooms": [{"name": "a", "start": 9, "end": 12}, {"name": "b", "start": 10, "end": 11}], "start": 9, "end": 12}, "a"),
        ("revision", {"exception": False, "exception_value": "z", "revisions": ["a", "b"]}, "b"),
        ("revision", {"exception": True, "exception_value": "z", "revisions": ["a", "b"]}, "z"),
        ("set_difference", {"available": ["a", "b"], "reserved": ["b", "c"]}, "a"),
        ("delegate", {"owners": {"p": "a"}, "deputies": {"a": "b"}, "absent": ["a", "b"], "topic": "p"}, "b"),
        ("net_stock", {"records": [{"name": "a", "stock": 7, "reserved": 5}, {"name": "b", "stock": 6, "reserved": 1}], "direction": "largest"}, "b"),
        ("required_document", {"priority": ["a", "b"], "special_document": "a", "special": False, "submitted": ["b"]}, "追加不要"),
        ("workflow", {"steps": ["a", "b"], "done": ["a"]}, "b"),
        ("pair_lookup", {"records": [{"name": "a", "color": "r", "material": "m"}, {"name": "b", "color": "b", "material": "m"}], "color": "b", "material": "m"}, "b"),
        ("rank_reference", {"order": ["a", "b", "c"], "rank": 2}, "b"),
        ("fact_negation", {"fact": False, "negated_query": True}, True),
        ("fact_negation", {"fact": True, "negated_query": True}, False),
        ("and", {"conditions": [True, False]}, False),
        ("or", {"conditions": [False, True]}, True),
        ("except", {"eligible": True, "exception": True}, False),
        ("deadline", {"actual": 12, "deadline": 12, "inclusive": True}, True),
        ("deadline", {"actual": 12, "deadline": 12, "inclusive": False}, False),
        ("latest_is", {"updates": [{"time": 13, "value": "b"}, {"time": 8, "value": "a"}], "query": "a"}, False),
        ("exact", {"left": "AB1-A", "right": "ab1-a"}, False),
        ("membership", {"entity": "a", "members": ["b"], "positive": False}, True),
        ("distinct_count", {"entries": ["a", "a", "b"], "minimum": 3}, False),
        ("implication", {"premise": False, "conclusion": False}, True),
        ("implication", {"premise": True, "conclusion": False}, False),
        ("reference_is", {"owners": {"p": "a"}, "links": {"d": "p"}, "reference": "d", "person": "a"}, True),
        ("evidence", {"recorded": "closed", "asserted": "open"}, False),
        ("range", {"value": 3, "low": 3, "high": 8, "low_closed": False, "high_closed": True}, False),
        ("range", {"value": 8, "low": 3, "high": 8, "low_closed": False, "high_closed": True}, True),
        ("overlap", {"a_start": 9, "a_end": 11, "b_start": 11, "b_end": 12}, False),
        ("overlap", {"a_start": 9, "a_end": 12, "b_start": 11, "b_end": 13}, True),
        ("precedence", {"events": ["a", "b", "c"], "first": "c", "second": "a"}, False),
        ("threshold_score", {"value": 4, "thresholds": [2, 4, 6]}, 2),
        ("sentiment_score", {"ordered_meanings": ["bad", "neutral", "good"], "meaning": "neutral"}, 1),
        ("progress_score", {"steps": ["a", "b"], "done": ["a"]}, 1),
        ("dimensions_score", {"satisfied": [True, False, True]}, 2),
        ("priority_score", {"impact": 2, "urgent": True, "max_score": 2}, 2),
        ("delay_score", {"arrival": 9, "promised": 10, "thresholds": [1, 2]}, 0),
        ("delay_score", {"arrival": 12, "promised": 10, "thresholds": [1, 2]}, 2),
        ("evidence_score", {"levels": {"a": 1, "b": 2}, "present": ["a", "b"]}, 2),
        ("evidence_score", {"levels": {"a": 1}, "present": []}, 0),
        ("match_score", {"requirements": {"x": "a", "y": "b"}, "actual": {"x": "a", "y": "c"}}, 1),
        ("capped_score", {"checks": [True, True], "cap": 1, "exception": True}, 1),
        ("capped_score", {"checks": [True, True], "cap": 1, "exception": False}, 2),
        ("missing_score", {"required": ["a", "b"], "provided": ["b", "c"]}, 1),
        ("temporal_score", {"updates": [{"time": 14, "value": 1}, {"time": 9, "value": 2}]}, 1),
        ("distance_score", {"actual": 4, "target": 8, "max_score": 3}, 3),
        ("reversible_score", {"accepted": [True, True, False], "revoked": [False, True, False]}, 1),
        ("lookup_score", {"scale": {"red": 2, "blue": 0}, "code": "blue"}, 0),
        ("weighted_score", {"active": [True, False, True], "weights": [2, 1, 1], "max_score": 2}, 2),
    ]
    for rule, facts, expected in tests:
        actual = solve(rule, facts)
        assert actual == expected, (rule, actual, expected)
    return len(tests)


def validate(cases):
    assert len(cases) == 2220
    excluded_semantics, excluded_inputs, _ = baseline()
    assert len({c["id"] for c in cases}) == len(cases)
    assert collections.Counter(c["type"] for c in cases) == {"choice": 740, "noul": 740, "score": 740}
    assert len({c["semantic_sha256"] for c in cases}) == len(cases)
    exact = set()
    for c in cases:
        assert c["source"] == "generated"
        assert c["semantic_sha256"] not in excluded_semantics
        assert c["family"] and c["seed"] and c["variant"]
        assert isinstance(c["state"], (str, dict))
        assert isinstance(c["instructions"], str) and c["instructions"]
        criteria, kind = c["criteria"], c["type"]
        assert 2 <= len(criteria) <= 8
        answer = solve(c["oracle"]["rule"], c["oracle"]["facts"])
        rule, facts = c["oracle"]["rule"], c["oracle"]["facts"]
        if rule == "priority_score":
            assert facts["urgent"] == (facts["hours_left"] <= facts["urgent_within"])
        if rule == "evidence":
            assert facts["recorded"] == facts["observations"][facts["location"]]
        if rule == "delay_score":
            assert 0 <= facts["arrival"] <= 23 and 0 <= facts["promised"] <= 23
        if rule == "reversible_score":
            assert not any(revoked and not accepted for accepted, revoked in zip(facts["accepted"], facts["revoked"]))
        if rule == "progress_score":
            assert facts["done"] == facts["steps"][:len(facts["done"])]
        expected = str(answer).lower() if kind == "noul" else str(answer)
        assert c["label"] == expected
        assert c["oracle"]["explanation"] == explanation(c["oracle"]["rule"], c["oracle"]["facts"], answer)
        assert semantic_identity(c["oracle"]["rule"], c["oracle"]["facts"], c["instructions"], criteria) == c["semantic_sha256"]
        if kind == "score":
            assert isinstance(criteria, list) and len(set(criteria)) == len(criteria)
            assert 0 <= int(c["label"]) < len(criteria)
        else:
            assert isinstance(criteria, dict) and c["label"] in criteria
            if kind == "noul":
                assert set(criteria) == {"false", "true"}
            # Permute option insertion order and remap the selected alphabetic
            # symbol: the semantic key and description must remain unchanged.
            keys = list(criteria)
            random.Random(c["seed"] + 91).shuffle(keys)
            symbol_index = keys.index(c["label"])
            reordered = dict((key, criteria[key]) for key in keys)
            assert list(reordered)[symbol_index] == c["label"]
            assert reordered[c["label"]] == criteria[c["label"]]
        input_hash = digest({key: c[key] for key in ["type", "state", "instructions", "criteria"]})
        assert input_hash not in exact
        assert input_hash not in excluded_inputs
        exact.add(input_hash)
    by_type = {}
    for kind in ["choice", "noul", "score"]:
        subset = [c for c in cases if c["type"] == kind]
        families = collections.Counter(c["family"] for c in subset)
        assert len(families) == 15
        assert sorted(families.values()) == [49]*10 + [50]*5
        variants = {family: len({c["variant"] for c in subset if c["family"] == family}) for family in families}
        assert all(v >= 2 for v in variants.values())
        forms = collections.Counter("json" if isinstance(c["state"], dict) else "natural" for c in subset)
        assert min(forms.values()) >= 250
        conditional_positions = {}
        for k in range(2, 9):
            rows = [c for c in subset if len(c["criteria"]) == k]
            if rows:
                counts = collections.Counter(int(c["label"]) if kind == "score" else list(c["criteria"]).index(c["label"]) for c in rows)
                conditional_positions[str(k)] = {str(j): counts[j] for j in range(k)}
                if kind in {"choice", "score"}:
                    assert max(counts.get(j, 0) for j in range(k)) - min(counts.get(j, 0) for j in range(k)) <= 1
        by_type[kind] = {"count": len(subset), "family_count": len(families), "families": dict(sorted(families.items())), "state_forms": dict(forms), "candidate_counts": dict(sorted(collections.Counter(len(c["criteria"]) for c in subset).items())), "position_counts_by_candidate_count": conditional_positions}
    n = collections.Counter(c["label"] for c in cases if c["type"] == "noul")
    assert n == {"false": 370, "true": 370}
    # Dataset order changes may not change any (id, semantic label) pair.
    shuffled = list(cases)
    random.Random(SEED + 1).shuffle(shuffled)
    assert {c["id"]: c["label"] for c in cases} == {c["id"]: c["label"] for c in shuffled}
    return by_type


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Also regenerate and verify byte-identical deterministic output")
    args = parser.parse_args()
    unit_count = oracle_unit_tests()
    cases, rejected = build()
    stats = validate(cases)
    text = "".join(json.dumps(c, ensure_ascii=False, separators=(",", ":")) + "\n" for c in cases)
    if args.check:
        again, rejected_again = build()
        assert rejected == rejected_again
        assert text == "".join(json.dumps(c, ensure_ascii=False, separators=(",", ":")) + "\n" for c in again)
    output = ROOT / "private" / "generated_2220.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    file_hash = hashlib.sha256(text.encode()).hexdigest()
    report = {"version": 2, "v1_sha256": baseline()[2], "v1_semantic_overlap": 0, "v1_exact_input_overlap": 0, "seed": SEED, "total": len(cases), "sha256": file_hash, "oracle_unit_cases_passed": unit_count, "semantic_duplicates_rejected_during_generation": rejected, "duplicate_inputs": 0, "duplicate_semantics": 0, "deterministic_regeneration_checked": args.check, "by_type": stats}
    (ROOT / "private" / "generated_stats.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    notes = f"""# Generated blind acceptance block — version 2

Created by `make_generated_eval.py`; master seed `{SEED}`.

- Total: 2,220; Choice 740, Noul 740, Score 740.
- Fifteen families per type, 45 total; each family has 49 or 50 cases.
- Each family uses three natural-language question templates and a mixture of natural text and JSON state.
- Choice and Score have 2–8 candidates; Noul has exactly two. Noul truth labels are exactly 370/370. For each candidate count, Choice and Score answer positions differ by at most one case.
- Only `type`, `state`, `instructions`, and `criteria` are inference inputs. IDs, answers, sources, families, seeds, variants, and oracle records must not enter prompts.
- Every answer comes from the executable `solve` oracle applied to recorded facts; no external factual knowledge is required. Oracle facts and explanations are audit metadata.
- Exact-input duplicates: 0. Canonical oracle-fact duplicates: 0. Generation rejected {rejected} duplicate attempts, including variants that changed only wording or irrelevant names. Unordered record lists and set-like lists are normalized before semantic deduplication.
- In addition to all-case schema, range, truth-balance, uniqueness, template, and answer checks, {unit_count} independently specified oracle test examples passed. The tests include strict/inclusive boundaries, exceptions, latest-record precedence, negation, end-to-start schedules, and weighted-score caps.
- Candidate insertion-order permutations preserve semantic answer keys and descriptions. Score criteria are ordered scales and are deliberately not reordered. Dataset permutation preserves every ID/answer pair.
- Deterministic byte-for-byte second generation checked: {args.check}.
- This is a generated behavioral acceptance suite, not a sample of real user traffic. Repeated families and synthetic rubrics mean that overall accuracy measures these documented tasks, not general intelligence or calibration under distribution shift.
- This generator reads the frozen v1 generated block only to exclude all exact inputs and canonical oracle-fact identities. It never reads model outputs, manual/calibration blocks, or training data. No inference or tuning is performed here.
- V1 exact-input overlap: 0. V1 canonical semantic overlap: 0. V1 baseline file SHA-256: `{baseline()[2]}`.
- Finite predicate/scale pools were expanded in nine families without changing per-question logical operators, condition counts, or candidate counts: routing categories, action vocabulary, all/any predicates, checklist attributes, workflow steps, evidence types, satisfaction scale vocabulary, and integer threshold spacing. Required-document sets and redundant scan entries receive stricter order/multiplicity normalization for exclusion.
- Choice answers are balanced within one count at every candidate count after canonical sorting of keys, matching the actual inference prompt. Each case keeps the candidate cardinality from its first draw, preventing positional rejection from favoring small/easy candidate sets. Score positions are also balanced within one. V1 is unchanged; its insertion-order balance should not be interpreted as canonical prompt-position balance.

SHA-256 of `private/generated_2220.jsonl`: `{file_hash}`.

Detailed counts and candidate-position histograms are in `private/generated_stats.json`.
"""
    (ROOT / "generated_notes.md").write_text(notes, encoding="utf-8")
    # Emit only public aggregate statistics; never expose blind examples.
    print(json.dumps({key: value for key, value in report.items() if key != "by_type"}, ensure_ascii=False, indent=2))
    print(json.dumps({kind: {key: value for key, value in values.items() if key not in {"families", "position_counts_by_candidate_count"}} for kind, values in stats.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
