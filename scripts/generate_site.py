"""data/subsidies.json から docs/ 配下の静的HTMLを生成する。
フェーズ1: トップページ(index.html)と個別詳細ページ(s/{id}.html)のみ。
"""
import json
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "subsidies.json"
TEMPLATES_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"
DOCS_DIR = ROOT / "docs"
JST = timezone(timedelta(hours=9))
NEW_ITEM_WINDOW_DAYS = 7

# 表示順を安定させるための行政区画順（北海道→沖縄）。
# 実データに出現する都道府県だけをこの順で抽出する（存在しない値は追加しない）。
PREFECTURE_ORDER = [
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県",
    "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県",
    "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県",
    "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
]


def collect_available_areas(items):
    """出現する都道府県を行政区画順で集計する（「全国」「不明」は選択肢に含めない）。"""
    seen = set()
    for item in items:
        area = item.get("target_area") or ""
        if area in ("全国", "不明", ""):
            continue
        for pref in area.split("/"):
            pref = pref.strip()
            if pref:
                seen.add(pref)
    return [p for p in PREFECTURE_ORDER if p in seen]


# 日本標準産業分類（大分類）の公式順。jGrants industryフィールドの分割元と一致する。
# 業種名の五十音順は読み仮名の恣意的な付与が必要になるため、代わりに一次情報である
# 産業分類の公式順を採用する。
INDUSTRY_ORDER = [
    "農業", "林業", "漁業",
    "鉱業", "採石業", "砂利採取業",
    "建設業", "製造業",
    "電気・ガス・熱供給・水道業", "情報通信業",
    "運輸業", "郵便業",
    "卸売業", "小売業",
    "金融業", "保険業",
    "不動産業", "物品賃貸業",
    "学術研究", "専門・技術サービス業",
    "宿泊業", "飲食サービス業",
    "生活関連サービス業", "娯楽業",
    "教育", "学習支援業",
    "医療", "福祉",
    "複合サービス事業",
    "サービス業（他に分類されないもの）",
    "公務（他に分類されるものを除く）",
    "分類不能の産業",
]


def collect_available_industries(items):
    """出現する業種を集計し、日本標準産業分類の大分類順で返す。
    分類表にない値（表記ゆれ等）は末尾にコードポイント順で追加する。"""
    seen = set()
    for item in items:
        for industry in item.get("target_industries") or []:
            if industry and industry != "不明":
                seen.add(industry)
    ordered = [i for i in INDUSTRY_ORDER if i in seen]
    unknown = sorted(seen - set(INDUSTRY_ORDER))
    return ordered + unknown


# 目的・キーワードチップの候補語。scripts/fetch_jgrants.py の SEARCH_KEYWORDS と
# 同じ21語（jGrants収集時に使う検索キーワード＝ユーザーが探す目的語としても妥当なため
# 流用）。fetch_jgrants.py を import すると requests 依存が生じるため値は複製する。
# fetch_jgrants.SEARCH_KEYWORDS を変更した場合はこちらも合わせて更新すること。
PURPOSE_KEYWORDS = [
    "補助", "助成", "支援", "創業", "事業",
    "中小企業", "小規模", "スタートアップ", "事業承継",
    "DX", "IT", "ものづくり",
    "省エネ", "脱炭素", "環境",
    "観光", "農業", "海外展開",
    "人材", "女性", "賃上げ",
]
PURPOSE_KEYWORDS_PRIMARY_COUNT = 9

# 補助金サイトでは自明で絞り込みに寄与しない汎用語（v1.2 SPEC 9-4）。
# 前面（primary）表示から外すが、検索対象からは外さず「もっと見る」内に残す。
# 新規語は創作せず、PURPOSE_KEYWORDS に実在する語のみを列挙する。
PURPOSE_KEYWORDS_EXCLUDED = {"補助", "助成", "支援", "事業", "中小企業"}


def build_purpose_keywords(items):
    """目的キーワードを実データでの出現頻度（タイトル・キャッチコピー・要約に
    含まれる件数）が多い順に並べ替える。0件のキーワードも一覧末尾に残す
    （「もっと見る」展開後も候補として選べるようにするため、除外はしない）。
    ただし PURPOSE_KEYWORDS_EXCLUDED に含まれる汎用語は、頻度順ロジックは
    維持したまま前面表示の対象外とするため、非汎用語グループの後ろに回す。"""
    def searchable_text(item):
        parts = [item.get("title"), item.get("catch_phrase"), item.get("summary")]
        return " ".join(p for p in parts if p).lower()

    haystacks = [searchable_text(item) for item in items]
    counts = {
        kw: sum(1 for h in haystacks if kw.lower() in h)
        for kw in PURPOSE_KEYWORDS
    }
    ordered = sorted(PURPOSE_KEYWORDS, key=lambda kw: counts[kw], reverse=True)
    included = [kw for kw in ordered if kw not in PURPOSE_KEYWORDS_EXCLUDED]
    excluded = [kw for kw in ordered if kw in PURPOSE_KEYWORDS_EXCLUDED]
    return included + excluded


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
    ga4_id = "G-NKJELNWQKD"

    items = load_items()
    for item in items:
        item["days_left"] = compute_days_left(item.get("deadline"), today)

    visible_items = [i for i in items if i.get("status") != "closed"]
    all_items = sorted(
        visible_items,
        key=lambda x: (x.get("deadline") is None, x.get("deadline") or ""),
    )

    for item in all_items:
        item["is_new"] = bool(
            item.get("first_seen")
            and (today - datetime.strptime(item["first_seen"], "%Y-%m-%d").date()).days <= NEW_ITEM_WINDOW_DAYS
        )

    available_areas = collect_available_areas(all_items)
    available_industries = collect_available_industries(all_items)
    purpose_keywords = build_purpose_keywords(all_items)

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "s").mkdir(parents=True, exist_ok=True)

    filter_js_src = STATIC_DIR / "filter.js"
    if filter_js_src.exists():
        shutil.copyfile(filter_js_src, DOCS_DIR / "filter.js")

    index_tmpl = env.get_template("index.html")
    index_html = index_tmpl.render(
        base_path="",
        generated_at=generated_at,
        ga4_id=ga4_id,
        all_items=all_items,
        available_areas=available_areas,
        available_industries=available_industries,
        purpose_keywords=purpose_keywords,
        purpose_keywords_primary_count=PURPOSE_KEYWORDS_PRIMARY_COUNT,
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
    print(f"  shown on index: {len(all_items)}, new (last {NEW_ITEM_WINDOW_DAYS} days): {sum(1 for i in all_items if i['is_new'])}")


if __name__ == "__main__":
    main()
