"""Run with python -m service.example after starting the server."""
from dataclasses import asdict
import json

from .client import Choice, Client, Noul, Score


def main():
    with Client() as client:
        result = client.system_one(
            state={"message": "今朝から二重請求が発生しています。至急確認してください。", "language": "ja"},
            questions={
                "department": Choice("対応する部署を選んでください。", {
                    "billing": "料金・請求", "technical": "技術的な障害", "sales": "購入前の相談"}),
                "urgent": Noul("メッセージで至急の対応を求めていますか？"),
                "urgency": Score("対応の緊急度を評価してください。", [
                    "通常の情報提供でよい", "早めの対応が望ましい", "至急対応が必要"]),
            },
        )
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
