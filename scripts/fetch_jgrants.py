"""jGrants公開API (https://api.jgrants-portal.go.jp) から募集中の補助金を取得し、
data/subsidies.json に source="jgrants" の項目としてupsertする。

APIはkeywordパラメータが必須（2文字以上）かつページングが無いため、
複数の広いキーワードで検索してid単位に重複排除し、詳細APIで1件ずつ補完する。
"""
import json
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "subsidies.json"

API_BASE = "https://api.jgrants-portal.go.jp/exp/v1/public/subsidies"
JST = timezone(timedelta(hours=9))

# jGrants APIはkeyword必須・全文検索でページング機構が無い（1レスポンスでヒット全件を
# 返す）ため、広いキーワードを多数投げてカバー範囲を広げることが取得件数拡大の唯一の
# 手段となる。分野横断的な語を追加し、個別分野の専門語のみを含む案件（「補助/助成/
# 支援/事業」を含まないタイトル等）の取りこぼしを減らす。
SEARCH_KEYWORDS = [
    "補助", "助成", "支援", "創業", "事業",
    "中小企業", "小規模", "スタートアップ", "事業承継",
    "DX", "IT", "ものづくり",
    "省エネ", "脱炭素", "環境",
    "観光", "農業", "海外展開",
    "人材", "女性", "賃上げ",
]

# jGrants APIのレート制限は60リクエスト/分が推奨値（公式ドキュメント）。
# 1.1秒間隔（約54リクエスト/分）で安全マージンを確保する。
REQUEST_INTERVAL_SEC = 1.1

# v2.3 表示品質改善: 撤回届・中止届・変更届・練習用ダミー・状況報告など、
# 補助金そのものではない手続き用レコードをタイトルで除外する（静的リスト、
# 継続的なメンテナンス自動化は対象外）。
EXCLUDE_TITLE_KEYWORDS = [
    "撤回届",
    "中止届",
    "変更届",
    "申請練習用補助金",
    "状況報告等について",
]


def _to_jst_date(iso_str):
    if not iso_str:
        return None
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return dt.astimezone(JST).date().isoformat()


def search_ids():
    """複数キーワードで検索し、重複排除したid一覧を返す。
    1キーワードの通信エラーで全体を止めないよう、キーワード単位でtry/exceptする
    （キーワード数が増えるほど単発エラーに当たる確率も上がるため）。"""
    ids = {}
    for kw in SEARCH_KEYWORDS:
        try:
            resp = requests.get(
                API_BASE,
                params={
                    "keyword": kw,
                    "sort": "acceptance_end_datetime",
                    "order": "ASC",
                    "acceptance": 1,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("result", []):
                ids[item["id"]] = item
        except (requests.RequestException, ValueError) as e:
            print(f"WARN: search failed for keyword '{kw}': {e}", file=sys.stderr)
        time.sleep(REQUEST_INTERVAL_SEC)
    return ids


def fetch_detail(subsidy_id):
    resp = requests.get(f"{API_BASE}/id/{subsidy_id}", timeout=30)
    resp.raise_for_status()
    result = resp.json().get("result", [])
    if not result:
        return None
    return result[0]


_INDUSTRY_SPLIT_RE = re.compile(r"\s*/\s*|、")


def parse_industries(industry_str):
    if not industry_str:
        return ["不明"]
    # "・"は業種名内部の区切り（例: 電気・ガス・熱供給・水道業）なので分割しない。
    # "/" と "、" が業種同士の区切り。
    parts = [p.strip() for p in _INDUSTRY_SPLIT_RE.split(industry_str) if p.strip()]
    return parts or ["不明"]


def to_schema(detail):
    official_url = detail.get("front_subsidy_detail_page_url")
    if not official_url:
        # 一次情報リンクが取得できない項目は掲載しない
        return None

    amount_max = detail.get("subsidy_max_limit") or None
    if amount_max == 0:
        amount_max = None
    amount_text = f"最大{amount_max:,}円" if amount_max else "不明"

    return {
        "id": f"jgrants-{detail['id']}",
        "source": "jgrants",
        "title": detail.get("title") or "不明",
        "organization": detail.get("institution_name") or "不明",
        "catch_phrase": detail.get("subsidy_catch_phrase") or None,
        "summary": None,
        "amount_max": amount_max,
        "amount_text": amount_text,
        "subsidy_rate": detail.get("subsidy_rate") or None,
        "deadline": _to_jst_date(detail.get("acceptance_end_datetime")),
        "start_date": _to_jst_date(detail.get("acceptance_start_datetime")),
        "target_industries": parse_industries(detail.get("industry")),
        "target_area": detail.get("target_area_search") or "不明",
        "category": None,
        "official_url": official_url,
        "detail_url": official_url,
        "status": "open",
        "detail_html": detail.get("detail") or None,
        "target_number_of_employees": detail.get("target_number_of_employees") or None,
        "request_reception_presence": detail.get("request_reception_presence") or None,
        "is_enable_multiple_request": detail.get("is_enable_multiple_request"),
        "project_end_deadline": _to_jst_date(detail.get("project_end_deadline")),
    }


def load_existing():
    if not DATA_PATH.exists():
        return {}
    with open(DATA_PATH, encoding="utf-8") as f:
        items = json.load(f)
    return {item["id"]: item for item in items}


def main():
    today = datetime.now(JST).date().isoformat()
    existing = load_existing()

    print("Searching jGrants for candidate ids...", file=sys.stderr)
    candidates = search_ids()
    print(f"Found {len(candidates)} unique candidate ids", file=sys.stderr)

    fetched_count = 0
    error_count = 0
    excluded_count = 0
    for subsidy_id in candidates:
        try:
            detail = fetch_detail(subsidy_id)
            if detail is None:
                continue

            title = detail.get("title") or ""
            if any(kw in title for kw in EXCLUDE_TITLE_KEYWORDS):
                existing.pop(f"jgrants-{subsidy_id}", None)
                excluded_count += 1
                continue

            record = to_schema(detail)
            if record is None:
                continue

            key = record["id"]
            if key in existing:
                record["first_seen"] = existing[key].get("first_seen", today)
                record["status"] = existing[key].get("status", "open")
            else:
                record["first_seen"] = today
            record["last_updated"] = today
            existing[key] = record
            fetched_count += 1
        except (requests.RequestException, ValueError) as e:
            print(f"WARN: failed to fetch detail for {subsidy_id}: {e}", file=sys.stderr)
            error_count += 1
        time.sleep(REQUEST_INTERVAL_SEC)

    print(f"Upserted {fetched_count} jgrants records ({error_count} errors, {excluded_count} excluded by title filter)", file=sys.stderr)

    all_items = list(existing.values())
    all_items.sort(key=lambda x: (x.get("deadline") is None, x.get("deadline") or ""))

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(all_items)} total records to {DATA_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
