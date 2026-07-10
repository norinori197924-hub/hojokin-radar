"""data/subsidies.json から docs/ 配下の静的HTMLを生成する。
フェーズ1: トップページ(index.html)と個別詳細ページ(s/{id}.html)のみ。
"""
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "subsidies.json"
TEMPLATES_DIR = ROOT / "templates"
DOCS_DIR = ROOT / "docs"
JST = timezone(timedelta(hours=9))
NEW_ITEM_WINDOW_DAYS = 7
TOP_LIST_LIMIT = 10


def load_items():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def compute_days_left(deadline_str, today):
    if not deadline_str:
        return None
    deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
    return (deadline - today).days


def main():
    today = datetime.now(JST).date()
    generated_at = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    ga4_id = os.environ.get("GA4_ID") or None

    items = load_items()
    for item in items:
        item["days_left"] = compute_days_left(item.get("deadline"), today)

    visible_items = [i for i in items if i.get("status") != "closed"]
    all_items = sorted(
        visible_items,
        key=lambda x: (x.get("deadline") is None, x.get("deadline") or ""),
    )

    closing_soon = [i for i in all_items if i.get("status") == "closing_soon"][:TOP_LIST_LIMIT]

    new_items = [
        i for i in visible_items
        if i.get("first_seen") and (today - datetime.strptime(i["first_seen"], "%Y-%m-%d").date()).days <= NEW_ITEM_WINDOW_DAYS
    ]
    new_items.sort(key=lambda x: x["first_seen"], reverse=True)
    new_items = new_items[:TOP_LIST_LIMIT]

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "s").mkdir(parents=True, exist_ok=True)

    index_tmpl = env.get_template("index.html")
    index_html = index_tmpl.render(
        base_path="",
        generated_at=generated_at,
        ga4_id=ga4_id,
        closing_soon=closing_soon,
        new_items=new_items,
        all_items=all_items,
    )
    (DOCS_DIR / "index.html").write_text(index_html, encoding="utf-8")

    detail_tmpl = env.get_template("detail.html")
    for item in items:
        detail_html = detail_tmpl.render(
            base_path="../",
            generated_at=generated_at,
            ga4_id=ga4_id,
            item=item,
        )
        (DOCS_DIR / "s" / f"{item['id']}.html").write_text(detail_html, encoding="utf-8")

    print(f"Generated index.html and {len(items)} detail pages in {DOCS_DIR}")
    print(f"  open+closing_soon shown on index: {len(all_items)}, closing_soon: {len(closing_soon)}, new: {len(new_items)}")


if __name__ == "__main__":
    main()
