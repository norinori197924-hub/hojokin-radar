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
