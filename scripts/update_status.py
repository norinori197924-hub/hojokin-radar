"""data/subsidies.json の各項目について、締切日と本日日付を比較してstatusを再計算する。

status:
  open          - 締切まで15日以上（または締切不明）
  closing_soon  - 締切まで14日以内
  closed        - 締切超過（削除はしない）
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "subsidies.json"
JST = timezone(timedelta(hours=9))
CLOSING_SOON_DAYS = 14


def compute_status(deadline_str, today):
    if not deadline_str:
        return "open"
    deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
    days_left = (deadline - today).days
    if days_left < 0:
        return "closed"
    if days_left <= CLOSING_SOON_DAYS:
        return "closing_soon"
    return "open"


def main():
    today = datetime.now(JST).date()

    with open(DATA_PATH, encoding="utf-8") as f:
        items = json.load(f)

    counts = {"open": 0, "closing_soon": 0, "closed": 0}
    for item in items:
        item["status"] = compute_status(item.get("deadline"), today)
        counts[item["status"]] += 1

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"status updated: {counts}")


if __name__ == "__main__":
    main()
