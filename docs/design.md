# トップページUI改善（コア体験）設計書

SPEC.md（UI改善フェーズ1版, v1.1）に基づく、トップページの検索〜一覧まわりの刷新。

## 1. 要件整理

SPEC.md 2〜4章のとおり、検索の入口優先度（地域→目的・キーワード→業種→新着/締切ソート）
に沿ってレイアウトを再構成する。詳細ページ・市区町村検索・広告タグ実挿入・データ取得ロジックは
スコープ外（SPEC.md 6章）。

## 2. 現状確認で判明した事実

- `data/subsidies.json`（299件）は `summary` が全件空、`catch_phrase` は180/299件のみ。
  カード要約は「catch_phraseがあれば表示、無ければ`summary`、どちらも無ければ定型文
  『詳細ページでご確認ください。』」とする（CLAUDE.mdの「推測でデータを補完しない」原則）。
- `scripts/fetch_jgrants.py` の `SEARCH_KEYWORDS`（21語）が、SPEC.md 8章が言う
  「実データの21キーワード」に一致。目的チップの候補語としてこの21語を流用する
  （fetch側の検索ロジックは変更しない。値のみ `generate_site.py` に複製）。
- 既存の絞り込みロジック（`matchesArea`/`matchesIndustry`/`matchesKeyword`、
  `#filter-area`/`#filter-industry`/`#filter-keyword` などのid）はそのまま維持し、
  デグレを防止する。

## 3. ページ構成（新）

SPEC.md 3章の順で配置。既存の「締切間近」「新着」の2独立セクションは、単一の
ソート可能な一覧に統合する（ユーザー承認済み）。新着案件は一覧内でNEWバッジ表示に変更。

1. 検索窓（`#filter-keyword`、最上部・大）
2. 地域選択（`#filter-area`、47都道府県セレクト）
3. 目的・キーワードチップ（21語を実データでの出現頻度順に並べ替え、上位9件を常時表示、
   残り12件は「もっと見る」で展開）
4. 業種絞り込み（`#filter-industry`、既存）
5. ソート切替（締切が近い順＝既定／新着順）
6. 補助金一覧（カード、要約付き、カード全体がリンク）

広告枠（`ad-slot-index-top`/`ad-slot-index-list`）は削除せず、ヒーロー検索の直後と
一覧直前に配置し直す。

## 4. 実装方針

- `scripts/generate_site.py`: `PURPOSE_KEYWORDS`定数（21語）を追加し、
  `build_purpose_keywords()`でタイトル・catch_phrase・summaryへの出現件数が多い順に
  並べ替えてテンプレートへ渡す。`closing_soon`/`new_items`の個別集計をやめ、
  各アイテムに`is_new`（first_seenが7日以内か）を付与して一覧内バッジ表示に切り替える。
- `templates/index.html`: SPEC.md 3章の順にセクションを再構成。
- `templates/_macros.html`: `subsidy_card`を`<a class="card">`に変更（カード全体を
  クリック可能にし、タイトル内の入れ子`<a>`を廃止）。`data-deadline`/`data-first-seen`
  をカードに付与し、クライアント側ソートに使う。要約表示・NEWバッジを追加。
  目的チップ用の`purpose_chip`マクロを追加。
- `static/filter.js`: 既存の絞り込み判定関数（`matchesArea`等）は無変更。
  ソート切替は、初期DOM順（＝サーバー生成時点の締切昇順）を`cardsByDeadline`として
  保持し、新着順選択時のみ`data-first-seen`降順に並べ替えた配列でDOMノードを
  実際に移動する（複製しないため`hidden`状態はノードに紐づいたまま維持される）。
  目的チップはクリックで`#filter-keyword`に値を反映し、既存の`matchesKeyword`
  （部分一致）をそのまま利用する。
- `docs/style.css`: 旧`.filter-panel`/`.filter-row`/`.filter-field`系クラスを
  `.hero-search`/`.hero-field`/`.chip`/`.sort-toggle`系に置き換え（未使用化した
  旧クラスは削除）。カードの要約は`-webkit-line-clamp:3`で2〜3行に収める。

## 5. 既知の留意事項

- 現在のデータは299件中295件の`first_seen`が直近7日以内であるため、"NEW"バッジが
  ほぼ全カードに付く（データ取得パイプラインの特性であり、本UI改善では調整しない）。
- 実ブラウザでの目視確認は行っていない（プロジェクト制約によりブラウザツール不使用）。
  `generate_site.py`実行結果のHTML/CSS/JSをファイルとして確認する形で検証した。

---

# 広告枠プレースホルダー追加 設計書

## 1. 要件整理

- 一覧ページ(`index.html`)に広告枠を1〜2箇所（カード一覧の間、または上部）
- 詳細ページ(`detail.html`)にも広告枠（本文の上下）
- `<div id="ad-slot-xxx">`形式のプレースホルダー。実広告タグは後から差し込むだけで済む構造
- モバイルでレイアウトが崩れない・CLS対策として最小高さを確保
- 「広告」ラベルを表示（景品表示法・ステマ規制対応）
- 検索・フィルタ機能や既存カードレイアウトに影響を与えない

## 2. 現状確認

- `templates/detail.html` には既に `<!-- AFFILIATE_SLOT_1 -->` というコメントの
  プレースホルダーが1箇所存在する（`.detail-header`の直後、CTAボタンの前）。
  今回これを実際の広告枠divに置き換える。
- `docs/style.css` には未使用の `.affiliate-slot { margin: 28px 0; }` が既に
  定義済み。今回のCSS設計のベースとして活用する。
- `templates/index.html` の一覧カードリスト(`#all-items-list`)は
  `static/filter.js` が `querySelectorAll("[data-filter-card]")` で走査し、
  条件に応じて`hidden`属性を切り替える。**このリスト内に広告divを混入させると**、
  絞り込み結果が0件になった際に広告だけが取り残されて表示される、
  `filter-count`の分母（`cards.length`）とは無関係な要素が挟まる、といった
  副作用が起きうる。→ 広告枠はフィルタ対象の`#all-items-list`の**外側**に置き、
  `data-filter-card`属性も付与しないことで、フィルタ機能に一切影響を与えない
  設計とする。

## 3. 配置設計

### index.html（2箇所）
1. `ad-slot-index-top`: `{% block content %}`の直後、「締切間近」見出しより前
   （ページ最上部＝「上部」要件）
2. `ad-slot-index-list`: 「新着」セクションと「募集中の一覧」見出し（フィルタ
   パネル・`#all-items-list`）の間（2つのカードリストの「間」＝「カード一覧の
   間」要件を満たしつつ、フィルタ対象リストの外側に配置）

### detail.html（2箇所、本文の上下）
1. `ad-slot-detail-top`: パンくずリストの直後、`.detail-header`（タイトル・
   詳細情報テーブル＝本文）より前
2. `ad-slot-detail-bottom`: 既存の`<!-- AFFILIATE_SLOT_1 -->`コメントを置き換え。
   `.detail-header`（本文）の直後、CTAボタンの前（本文の「下」）

## 4. マークアップ構造

再利用のため`_macros.html`に`ad_slot(slot_id)`マクロを追加する。

```html
<div class="ad-slot-wrap">
  <span class="ad-label" aria-hidden="true">広告</span>
  <div class="ad-slot" id="{{ slot_id }}">
    <!-- ここにAdSense等の広告タグを挿入 -->
    <p class="ad-slot-placeholder">広告スペース</p>
  </div>
</div>
```

- `id="ad-slot-xxx"`の`div`は広告タグの純粋な差し込み先とする（将来
  AdSenseの`<ins class="adsbygoogle">`等をこの中に追加するだけで済むように、
  「広告」ラベルは外側の兄弟要素にする＝広告スクリプトが中身を書き換えても
  ラベル表示は消えない）。
- プレースホルダーの`<p class="ad-slot-placeholder">広告スペース</p>`は
  実装時点の見た目確認用。広告タグを差し込む際に削除する想定であることを
  HTMLコメントで明記する。

## 5. CLS対策・レスポンシブ

- `.ad-slot`に`min-height`を指定し、広告読み込み前後で高さが変わらないように
  する（`min-height: 100px`、一般的なレスポンシブ表示広告の目安値）。
- 幅は`.container`（`max-width: 900px`）に追従する`width: 100%`とし、
  メディアクエリ無しでモバイルでも崩れない（既存の`.filter-panel`等と同じ
  流し込み方式を踏襲）。
- ダークモード対応は既存のCSS変数（`--surface`, `--border`, `--text-muted`）を
  使うことで、追加のダークモード専用ルールなしに自動対応する。

## 6. 広告ラベル（景品表示法・ステマ規制対応）

- `.ad-label`で「広告」の文字を常に表示する（広告タグ読み込みの成否に関わらず
  独立して表示されるようにするため、`#ad-slot-xxx`の外側に配置）。
- 参考: 消費者庁の「一般消費者が事業者の表示であることを判別することが困難で
  ある表示」規制（2023年10月施行）に対応する一般的な実装パターン
  （広告枠に隣接する形での明示ラベル）を踏襲。

## 7. 申し送り事項（実広告タグ差し込み時に対応）

analyzerサブエージェントの分析（`docs/analysis-report.md`）より、現時点の
プレースホルダー実装では対応不要だが、実際の広告タグ（AdSense等）を
差し込む際に確認・対応すべき項目:

1. `.ad-slot`の`min-height: 100px`は「レイアウト崩れのゼロ回避」の暫定値。
   実際に配信される広告フォーマット（レスポンシブ広告は150〜300px超になる
   ことがある）に応じて`min-height`（必要ならブレークポイント別の値や
   `aspect-ratio`）を再設定しないと、広告読み込み時にCLSが発生しうる。
2. `ad-slot-index-top`はページ本文冒頭（h2「締切間近」より前）に位置する。
   実広告差し込み後、Googleの「ファーストビューの過度な広告占有」に関する
   ガイドラインに抵触しないか、実際のレンダリング結果で確認する。
3. 広告のインプレッション/クリック計測（GA4連携等）は今回スコープ外。
   導入時は各広告枠の`id`（`ad-slot-xxx`）をイベントlabelとして流用できる。

## 8. 変更差分

- `templates/_macros.html`: `ad_slot(slot_id)`マクロを追加
- `templates/index.html`: `ad_slot('ad-slot-index-top')`,
  `ad_slot('ad-slot-index-list')`を追加
- `templates/detail.html`: `ad_slot('ad-slot-detail-top')`を追加、既存の
  `<!-- AFFILIATE_SLOT_1 -->`コメントを`ad_slot('ad-slot-detail-bottom')`に置換
- `docs/style.css`: `.ad-slot-wrap`, `.ad-label`, `.ad-slot`,
  `.ad-slot-placeholder`を追加。未使用だった既存の`.affiliate-slot`は
  今回の`.ad-slot`系クラスに統合するため削除する
- `scripts/generate_site.py`: 変更なし（広告枠はテンプレート側のみの変更で
  データ・生成ロジックには影響しない）
