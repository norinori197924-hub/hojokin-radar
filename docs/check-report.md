# チェック結果（トップページUI改善）

対象差分: `scripts/generate_site.py` / `templates/index.html` / `templates/_macros.html` /
`static/filter.js` / `docs/style.css`（checkerサブエージェントによるレビュー、修正反映後）

## 総合判定: SAFE（CRITICAL 2件・CAUTION 3件は本レポート作成前にすべて修正済み）

## CRITICAL（修正済み）

1. **`hidden`属性が`.card`/`.chip`のCSSで無効化されていた**
   `docs/style.css`の`.card { display: flex; }`および`.chip { display: inline-block; }`が、
   `filter.js`が絞り込み時にセットする標準`hidden`属性のUA既定スタイル（`display: none`）を
   上書きし、非該当カードが表示されたまま残る／「もっと見る」展開が機能しない状態だった。
   → `docs/style.css`冒頭に`[hidden] { display: none !important; }`を追加して解消。
   完了条件「既存の検索・フィルタ結果が正しく機能している（デグレがない）」を満たす。

## CAUTION（修正済み）

1. 目的キーワードチップ群(`#purpose-chips`)に`role="group"`/`aria-labelledby`が無く、
   スクリーンリーダーでの文脈が伝わりにくかった → `templates/index.html`に追加。
2. カード全体を`<a>`化したことで、アクセシブルネームがバッジ・要約文まで連結され冗長
   だった → `<a class="card">`に簡潔な`aria-label`（タイトル・締切・地域）を追加。
3. JS無効時にソート切替ボタンが表示されたまま無反応になる → `noscript`のCSSに
   `#sort-toggle`を追加して非表示化。

## SAFE（指摘なし）

- ハードコードされた秘密情報・APIキーなし（GA4_IDは環境変数由来）
- Jinja2の`autoescape=True`が維持されており、外部データ由来フィールドはエスケープされる
- 地域/業種/キーワードの絞り込みロジック自体（`matchesArea`等）に変更なく、データの
  区切り文字（`/`）とも整合
- 新規CSSは既存のCSS変数（`--bg`/`--surface`/`--text`等）のみを使用しており、ライト/
  ダーク両テーマに自動追従
- フォームラベルの`for`/`id`対応は正しい
- カード内に入れ子のインタラクティブ要素（リンク/ボタン）はなし

## 備考

- ブラウザツール不使用の制約により、実ブラウザでの目視確認は行っていない。
  `py scripts/generate_site.py`実行後の生成HTML/CSS/JSをファイルとして確認する
  静的検証を最終防衛線としている。

---

# チェックレポート（広告枠プレースホルダー追加）

対象: `templates/_macros.html`(ad_slotマクロ新規)、`templates/index.html`、
`templates/detail.html`、`docs/style.css`

担当: checker サブエージェント

## 総合判定: CAUTION

CRITICAL・構文エラー・秘密情報の混入は検出なし。アクセシビリティ観点で
1件の修正推奨事項あり。

## SAFE

- `ad_slot(slot_id)`マクロの構文は正常、テンプレート継承にも問題なし。
- 広告枠2箇所(`index.html`)はいずれも`#all-items-list`(filter.jsの走査対象)の
  外側に配置されており、`data-filter-card`属性も付与していないため、
  検索・フィルタ機能への影響なし(設計通り)。
- `slot_id`は内部識別子のみで、AdSenseのpublisher ID等の秘密情報・実広告タグの
  ハードコードなし。
- `.ad-slot`は`min-height:100px`・`width:100%`でCLS対策とレスポンシブ対応を両立。
  既存CSS変数を再利用しダークモードにも自動追従。ラベルのコントラスト比は
  約5.03:1でWCAG AA(4.5:1)を満たす。
- クラス命名は既存の命名規則(kebab-case)と一貫。

## CAUTION（要対応）

1. **`.ad-label`の`aria-hidden="true"`により、スクリーンリーダー利用者に
   「広告」であることが伝わらない**
   実運用でプレースホルダーの`<p>広告スペース</p>`を削除して実広告タグを
   差し込むと、支援技術ユーザー向けの広告明示テキストが完全に消失する。
   景品表示法・ステマ規制の「一般消費者が広告と認識できること」という趣旨に
   照らしても、支援技術利用者を除外する実装は望ましくない。

## 次工程

CAUTION 1は「6. 修正」で対応する(`aria-hidden="true"`を削除し、常にラベルが
支援技術に伝わるようにする)。

---

# チェックレポート（SPEC.md セクション9 v1.2追加改善）

対象差分: `templates/index.html`（hero-lead追加・description block追加・
filter-feedback/clear-btn追加）、`scripts/generate_site.py`
（PURPOSE_KEYWORDS_EXCLUDED追加）、`static/filter.js`（フィードバック文言生成・
クリア処理追加）、`docs/style.css`（.hero-lead/.filter-feedback/.filter-clear-btn）

担当: checker サブエージェント

## 総合判定: SAFE（CAUTION 2件は本レポート作成前に修正済み、1件はSPEC.md更新で解消）

## CAUTION（修正済み）

1. `#filter-clear-btn`クリック後、ボタン自身が`hidden`になりキーボード/
   スクリーンリーダー利用者のフォーカスが行方不明になる可能性
   → `static/filter.js`のクリック処理末尾で`keywordInput.focus()`を呼び、
   絞り込み条件欄の先頭へフォーカスを明示的に移すよう修正。
2. `.filter-clear-btn`の`min-height`が32pxで、既存の`.chip`/`.sort-btn`(36px)と
   不揃いだった → 36pxに統一。

## 備考（SPEC.md更新で解消）

- SPEC.md 9-2の例文は単一条件時「『人材』で絞り込み中：34件」・複数条件時
  「東京都 × IT導入：12件」と書式が異なっていたが、着手前のヒアリングで
  ユーザーが「条件数によらない統一フォーマット（例: 〇〇 × △△：N件、単一時は
  『』を付けない）」を採用する方針を確定。SPEC.md 9-2を実装内容に合わせて
  更新済み（仕様変更時は先にSPEC.mdを更新するというCLAUDE.mdの原則に従う）。

## SAFE（指摘なし）

- ハードコードされた秘密情報・APIキーなし
- 既存の`matchesArea`/`matchesIndustry`/`matchesKeyword`・ソート・チップ
  クリックロジックは変更なし（デグレなし）
- `PURPOSE_KEYWORDS_EXCLUDED`は`PURPOSE_KEYWORDS`実在語のみを列挙しており、
  新規語の創作なし。頻度順ロジック（`sorted`のstable性）も維持
- 新規CSSは既存のCSS変数のみを使用しライト/ダーク両テーマに追従。
  375px幅想定の`@media (max-width: 480px)`にも追記済み
- `#filter-count`の`aria-live="polite"`は維持されており、フィードバック文言の
  動的更新がスクリーンリーダーに通知される
- meta description / og:description は静的な確定文面でエスケープ無効化なし。
  一次情報リンク・免責フッターの構造に変更なし

---

# チェックレポート（SPEC.md セクション10 v1.3追加改善）

対象差分: `templates/base.html`（`.site-tagline`削除）、`templates/index.html`
（広告枠の削除・新設）、`docs/style.css`（`.site-tagline`削除、カラートークン
更新、`.hero-search`グラデーション、`.card`ホバー効果、`.badge-new`box-shadow）

担当: checker サブエージェント

## 総合判定: SAFE（CRITICAL・CAUTIONともになし）

## SAFE（指摘なし）

- `.site-tagline`削除により、SPEC.md 10-1どおり「サイト名→キャッチコピー→
  リード文」の3段構成が実現されている。header/footer構造・免責表示は無変更
- 広告枠は`ad-slot-index-top`（検索エリア下）と`ad-slot-index-bottom`
  （`#all-items-list`外側の一覧最下部）の2箇所のみとなり、見出し直下の広告枠は
  削除済み（SPEC.md 10-2に合致）
- `ad-slot-index-bottom`が`#all-items-list`の外側にあるため、`static/filter.js`の
  `applySort()`（DocumentFragmentでのカード再配置処理）に巻き込まれず、ソート時に
  広告枠が消失・移動する不具合はない
- 新配色（`--danger`/`--danger-bg`/`--success-bg`/`--success-text`）は4テーマ
  ブロック（`:root`/`prefers-color-scheme: dark`/`data-theme="dark"`/
  `data-theme="light"`）すべてに反映され、コントラスト比は約5.1:1〜9.2:1で
  WCAG AA（4.5:1）を満たす（旧配色より改善）
- `.card`の`transition`/`transform`に対し`prefers-reduced-motion: reduce`で
  無効化する`@media`が追加されており、アクセシビリティ配慮が適切
- `.card:focus-visible`のoutlineスタイルはホバー効果追加と競合せず、キーボード
  フォーカス時の可視性は維持されている
- `.hero-search`の薄いブルーグラデーションもlight/dark双方に定義されており、
  背景変更によるテキストコントラスト低下は見られない
- 目的チップ（`.chip`系マークアップ・CSS・`static/filter.js`のチップ処理）は
  今回の差分に含まれておらず、挙動・見た目は変更されていない（SPEC.md 10-4の
  スコープ外要件を遵守）
- `body`の`font-family`宣言は変更なし（同10-4を遵守）
- ハードコードされた秘密情報・APIキーなし（GA4_IDは環境変数由来）
- 生成済みHTML（`docs/index.html`、`docs/s/*.html`）にもヘッダー変更・広告枠
  変更が正しく反映されており、テンプレートと実出力に乖離なし

## 備考

- `docs/design.md`の初期フェーズ（v1.1）設計セクションに旧`ad-slot-index-list`
  への言及が残っているが、これは設計メモの過去記録であり実装ファイルではない
  ため今回の判定に影響しない。v1.3分の設計セクションを`docs/design.md`に追記し、
  最新の広告枠構成を記録した。
