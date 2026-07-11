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
