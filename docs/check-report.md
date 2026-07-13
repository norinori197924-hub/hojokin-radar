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
