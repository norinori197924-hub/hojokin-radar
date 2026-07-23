"""data/subsidies.json から docs/ 配下の静的HTMLを生成する。
フェーズ1: トップページ(index.html)と個別詳細ページ(s/{id}.html)のみ。
"""
import json
import shutil
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

import nh3
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "subsidies.json"
TEMPLATES_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"
DOCS_DIR = ROOT / "docs"
JST = timezone(timedelta(hours=9))
NEW_ITEM_WINDOW_DAYS = 7

# v2.2 詳細ページ拡充: jGrants APIのdetailフィールド(リッチテキストHTML)を
# 表示する際のホワイトリスト。属性は一切許可せず、script/styleは中身ごと除去する。
DETAIL_ALLOWED_TAGS = {"p", "br", "strong", "em", "ul", "ol", "li"}
DETAIL_DROP_CONTENT_TAGS = {"script", "style"}

# 旧データ(このバージョン以前にfetch_jgrants.pyで取得され、募集終了により
# 再取得対象から外れた項目)にはこれらのキー自体が存在しないため、Jinja2の
# Undefinedとの曖昧な比較を避けるべく明示的にNoneへ正規化する。
NEW_DETAIL_FIELDS = (
    "detail_html",
    "target_number_of_employees",
    "request_reception_presence",
    "is_enable_multiple_request",
    "project_end_deadline",
)


# KANBEI SIGN・CLOUDPHONEはHPDXと同一キーワード群だが、v2.4ではHPDX固定選出のため
# 判定ロジックには含めない(SPEC.md v2.4「出し分けロジック」参照。将来のローテーション
# 導入時に候補として追加検討する)。
# v2.4.1: 実データ検証でURUMAP営業代行が一度も表示されない問題が判明したため、
# より対象を絞り込んだ条件であるURUMAP営業代行をHPDXより優先する順に変更。
AFFILIATE_OFFERS = [
    {
        "name": "URUMAP営業代行",
        "url": "https://px.a8.net/svt/ejp?a8mat=4B83D0+7GIILU+3SPO+A94YS2",
        "keywords": ["小規模事業者", "持続化"],
    },
    {
        "name": "ホームページDX(HPDX)",
        "url": "https://px.a8.net/svt/ejp?a8mat=4B83D0+7H3Y7M+3SPO+89OY6Q",
        "keywords": ["IT導入", "システム", "デジタル化"],
    },
]


def select_affiliate(item):
    text = " ".join(p for p in (item.get("title"), item.get("summary")) if p).lower()
    for offer in AFFILIATE_OFFERS:
        if any(kw.lower() in text for kw in offer["keywords"]):
            return offer
    return None


def sanitize_detail_html(raw_html):
    if not raw_html:
        return None
    cleaned = nh3.clean(
        raw_html,
        tags=DETAIL_ALLOWED_TAGS,
        attributes={},
        clean_content_tags=DETAIL_DROP_CONTENT_TAGS,
    ).strip()
    return cleaned or None


def normalize_new_fields(items):
    for item in items:
        for field in NEW_DETAIL_FIELDS:
            item.setdefault(field, None)

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


# v2.3 表示品質改善: target_areaが47都道府県すべてを含む場合は「全国」に畳んで表示する。
# フィルター用のdata-area属性（filter.js参照）は元の文字列のまま変えない。
def collapse_area_display(target_area):
    if not target_area:
        return target_area
    tokens = {p.strip() for p in target_area.split("/") if p.strip()}
    if set(PREFECTURE_ORDER) <= tokens:
        return "全国"
    return target_area


# v2.3 表示品質改善: summary/catch_phraseが両方空、またはtitleの単純な繰り返しに
# 過ぎない場合はNoneを返し、テンプレート側で表示自体を省略する
# （定型プレースホルダー文言の重複表示によるAdSense審査上の低品質コンテンツ判定を避ける）。
def display_summary(item):
    title = (item.get("title") or "").strip()
    text = (item.get("summary") or "").strip() or (item.get("catch_phrase") or "").strip()
    if not text or text == title:
        return None
    return text


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


# --- v2.5 補助金統計ページ: 補助率テキストのカテゴリ正規化 -----------------
# subsidy_rateは自由記述で表記ゆれが大きい(実データで130種類/290件)。厳密な
# フラクション解析はせず、部分一致による正規化にとどめる(推測でデータを
# 補完しない原則のため)。「10/10」「100%」は概念上「定額」(全額補助)と同一
# のため統合する。2カテゴリ以上に一致する場合(例:「1/2 もしくは 2/3」)は
# 単一カテゴリに押し込めず別枠集計する。
RATE_CATEGORIES = [
    ("定額", ("定額", "10/10", "10分の10", "100%")),
    ("4分の3", ("3/4", "4分の3")),
    ("3分の2", ("2/3", "3分の2")),
    ("2分の1", ("1/2", "2分の1")),
    ("3分の1", ("1/3", "3分の1")),
]
RATE_CATEGORY_MULTI = "複数の補助率(要公募要領確認)"
RATE_CATEGORY_OTHER = "その他・要確認"
RATE_CATEGORY_ORDER = [name for name, _ in RATE_CATEGORIES] + [RATE_CATEGORY_MULTI, RATE_CATEGORY_OTHER]
_FULLWIDTH_TO_HALFWIDTH = str.maketrans("０１２３４５６７８９／", "0123456789/")


def categorize_subsidy_rate(raw_rate):
    text = (raw_rate or "").translate(_FULLWIDTH_TO_HALFWIDTH)
    matched = [name for name, patterns in RATE_CATEGORIES if any(p in text for p in patterns)]
    if not matched:
        return RATE_CATEGORY_OTHER
    if len(matched) >= 2:
        return RATE_CATEGORY_MULTI
    return matched[0]


def format_yen(amount):
    return f"{round(amount):,}円"


def build_bar_list(pairs, total):
    """(ラベル, 件数)のリストから、比率(全体に対する%)と棒グラフ幅(区分内最大値
    に対する%)を付与したリストを作る。最大値に対する相対幅で描画し、実数と
    全体比率はテキストで別途明示する(色・幅だけに情報を依存させない)。"""
    max_count = max((c for _, c in pairs), default=0)
    result = []
    for label, count in pairs:
        pct = round(count / total * 100, 1) if total else 0.0
        bar_pct = round(count / max_count * 100, 1) if max_count else 0.0
        result.append({"label": label, "count": count, "pct": pct, "bar_pct": bar_pct})
    return result


def compute_amount_stats(items):
    amounts = sorted(i["amount_max"] for i in items if i.get("amount_max") is not None)
    n = len(amounts)
    if n == 0:
        return None
    median = amounts[n // 2] if n % 2 == 1 else (amounts[n // 2 - 1] + amounts[n // 2]) / 2
    mean = sum(amounts) / n
    return {
        "median_text": format_yen(median),
        "mean_text": format_yen(mean),
        "sample_count": n,
        "null_count": len(items) - n,
    }


# 業種を「絞った」案件とみなす上限業種数。insight_industry_concentrationと
# 業種別分布の集計で共通の基準として使う(target_industriesに31〜32業種=
# ほぼ全産業分類を列挙する「実質全業種対象」の制度が多数存在し、これを
# そのまま集計に含めると全業種が軒並み高比率になり分布として意味を持たない)。
INDUSTRY_TARGETED_MAX = 5


def get_targeted_industries(item):
    """業種を絞った案件(1〜INDUSTRY_TARGETED_MAX業種)ならその業種リストを、
    そうでなければ(0件、またはINDUSTRY_TARGETED_MAXを超える実質全業種対象)
    Noneを返す。"""
    industries = [ind for ind in (item.get("target_industries") or []) if ind and ind != "不明"]
    if 1 <= len(industries) <= INDUSTRY_TARGETED_MAX:
        return industries
    return None


def compute_industry_distribution(items):
    """業種を絞った案件のみを対象に集計する。戻り値は
    (件数降順の(業種名, 件数)リスト, 集計対象件数, 実質全業種対象として
    除外した件数)のタプル。"""
    counter = Counter()
    targeted_count = 0
    broad_count = 0
    for item in items:
        industries = get_targeted_industries(item)
        if industries is not None:
            targeted_count += 1
            counter.update(industries)
        elif item.get("target_industries"):
            broad_count += 1
    return counter.most_common(), targeted_count, broad_count


def compute_rate_distribution(items):
    counter = Counter(categorize_subsidy_rate(item.get("subsidy_rate")) for item in items)
    return [(name, counter[name]) for name in RATE_CATEGORY_ORDER if counter.get(name)]


def compute_month_distribution(items, today):
    """当月を含む今後3か月分。締切がゼロ件の月も表示するため、実データに
    存在しない月も(0件として)必ず3件分そろえて返す。"""
    counter = Counter()
    for item in items:
        deadline = item.get("deadline")
        if not deadline:
            continue
        dt = datetime.strptime(deadline, "%Y-%m-%d").date()
        delta_months = (dt.year - today.year) * 12 + (dt.month - today.month)
        if 0 <= delta_months <= 2:
            counter[dt.strftime("%Y-%m")] += 1

    result = []
    year, month = today.year, today.month
    for i in range(3):
        total_month = month + i
        y = year + (total_month - 1) // 12
        m = (total_month - 1) % 12 + 1
        key = f"{y:04d}-{m:02d}"
        result.append((f"{y}年{m}月", counter.get(key, 0)))
    return result


def compute_area_distribution(items):
    national = sum(1 for i in items if i.get("target_area_display") == "全国")
    specific = sum(
        1 for i in items if i.get("target_area_display") and i.get("target_area_display") != "全国"
    )
    return national, specific


# --- v2.5 インサイト文言: あらかじめ定義した条件分岐の定型文のみを使う。
# AIによる自由生成は行わない。該当しない場合はNoneを返し非表示にする。

def insight_industry_concentration(items, today):
    """当月締切分のうち、業種を広く網羅する制度(全業種対象に近いもの)を
    ノイズとして除外したうえで、最頻業種が一定割合を占める場合のみ言及する。
    (target_industriesが31〜32件など「実質全業種対象」の制度が多数存在し、
    単純集計では見かけ上の集中がすべての業種で発生してしまうため)"""
    cur_ym = today.strftime("%Y-%m")
    counter = Counter()
    total_targeted = 0
    for item in items:
        deadline = item.get("deadline")
        if not deadline or not deadline.startswith(cur_ym):
            continue
        industries = get_targeted_industries(item)
        if industries is not None:
            total_targeted += 1
            counter.update(industries)
    if total_targeted < 10 or not counter:
        return None
    industry, count = counter.most_common(1)[0]
    if count / total_targeted >= 0.3:
        return f"今月は{industry}向けの締切が集中しています(業種を絞った案件{total_targeted}件中{count}件)。"
    return None


def insight_deadline_soon(items):
    count = sum(1 for i in items if i.get("days_left") is not None and 0 <= i["days_left"] <= 7)
    if count >= 5:
        return f"まもなく締切を迎える補助金が{count}件あります。お早めのご確認をおすすめします。"
    return None


def insight_rate_dominant(rate_pairs, total):
    candidates = [(n, c) for n, c in rate_pairs if n not in (RATE_CATEGORY_MULTI, RATE_CATEGORY_OTHER)]
    if not candidates or not total:
        return None
    name, count = max(candidates, key=lambda pair: pair[1])
    share = count / total
    if share >= 0.4:
        return f"補助率は「{name}」が最も多く、全体の{share * 100:.0f}%を占めています。"
    return None


def insight_area_bias(national, specific):
    total = national + specific
    if not total:
        return None
    if national / total >= 0.7:
        return f"全国対象の補助金が全体の{national / total * 100:.0f}%を占めています。"
    if specific / total >= 0.7:
        return f"特定地域限定の補助金が全体の{specific / total * 100:.0f}%を占めています。"
    return None


def build_insights(items, today, rate_pairs, total, national, specific):
    candidates = [
        insight_industry_concentration(items, today),
        insight_deadline_soon(items),
        insight_rate_dominant(rate_pairs, total),
        insight_area_bias(national, specific),
    ]
    return [c for c in candidates if c][:2]


def compute_stats(items, today):
    total = len(items)
    within_7 = sum(1 for i in items if i.get("days_left") is not None and 0 <= i["days_left"] <= 7)
    within_30 = sum(1 for i in items if i.get("days_left") is not None and 0 <= i["days_left"] <= 30)

    rate_pairs = compute_rate_distribution(items)
    month_pairs = compute_month_distribution(items, today)
    month_total = sum(c for _, c in month_pairs)
    national, specific = compute_area_distribution(items)
    industry_pairs, industry_targeted_count, industry_broad_count = compute_industry_distribution(items)

    return {
        "total_count": total,
        "within_7": within_7,
        "within_30": within_30,
        "amount": compute_amount_stats(items),
        "industry_stats": build_bar_list(industry_pairs, industry_targeted_count),
        "industry_targeted_count": industry_targeted_count,
        "industry_broad_count": industry_broad_count,
        "industry_max_count": INDUSTRY_TARGETED_MAX,
        "rate_stats": build_bar_list(rate_pairs, total),
        "month_stats": build_bar_list(month_pairs, month_total),
        "area_stats": build_bar_list([("全国", national), ("特定地域限定", specific)], national + specific),
        "insights": build_insights(items, today, rate_pairs, total, national, specific),
    }


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
    adsense_client_id = "ca-pub-9507761841542746"

    items = load_items()
    normalize_new_fields(items)
    for item in items:
        item["days_left"] = compute_days_left(item.get("deadline"), today)
        item["target_area_display"] = collapse_area_display(item.get("target_area"))
        item["summary_display"] = display_summary(item)

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
        adsense_client_id=adsense_client_id,
        all_items=all_items,
        available_areas=available_areas,
        available_industries=available_industries,
        purpose_keywords=purpose_keywords,
        purpose_keywords_primary_count=PURPOSE_KEYWORDS_PRIMARY_COUNT,
    )
    (DOCS_DIR / "index.html").write_text(index_html, encoding="utf-8")

    stats = compute_stats(all_items, today)
    stats_tmpl = env.get_template("stats.html")
    stats_html = stats_tmpl.render(
        base_path="",
        generated_at=generated_at,
        ga4_id=ga4_id,
        adsense_client_id=adsense_client_id,
        stats=stats,
    )
    (DOCS_DIR / "stats.html").write_text(stats_html, encoding="utf-8")

    for page_name in ("privacy-policy.html", "about.html"):
        page_tmpl = env.get_template(page_name)
        page_html = page_tmpl.render(
            base_path="",
            generated_at=generated_at,
            ga4_id=ga4_id,
            adsense_client_id=adsense_client_id,
        )
        (DOCS_DIR / page_name).write_text(page_html, encoding="utf-8")

    (DOCS_DIR / "guide").mkdir(parents=True, exist_ok=True)
    for page_name in (
        "guide/index.html",
        "guide/rejection-reasons.html",
        "guide/application-flow.html",
        "guide/cautions.html",
    ):
        page_tmpl = env.get_template(page_name)
        page_html = page_tmpl.render(
            base_path="../",
            generated_at=generated_at,
            ga4_id=ga4_id,
            adsense_client_id=adsense_client_id,
        )
        (DOCS_DIR / page_name).write_text(page_html, encoding="utf-8")

    detail_tmpl = env.get_template("detail.html")
    for item in items:
        detail_body_html = sanitize_detail_html(item.get("detail_html"))
        affiliate = select_affiliate(item)
        detail_page_html = detail_tmpl.render(
            base_path="../",
            generated_at=generated_at,
            ga4_id=ga4_id,
            adsense_client_id=adsense_client_id,
            item=item,
            detail_body_html=detail_body_html,
            affiliate=affiliate,
        )
        (DOCS_DIR / "s" / f"{item['id']}.html").write_text(detail_page_html, encoding="utf-8")

    print(f"Generated index.html and {len(items)} detail pages in {DOCS_DIR}")
    print(f"  shown on index: {len(all_items)}, new (last {NEW_ITEM_WINDOW_DAYS} days): {sum(1 for i in all_items if i['is_new'])}")


if __name__ == "__main__":
    main()
