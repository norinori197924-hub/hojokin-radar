# hojokin-radar（補助金レーダー）

中小企業・個人事業主向けの補助金・助成金情報を自動収集し、締切順・業種別・地域別に整理して
GitHub Pagesで公開する静的サイト。RSS/API収集 → (Claude Batch APIで要約・分類) → 静的HTML生成
→ GitHub Actionsで日次自動実行、というアーキテクチャ（chosa-ratingを踏襲）。

## 絶対に守る設計原則

1. **一次情報リンク必須**: 全項目に公式ページURLを表示。取得できない項目は掲載しない。
2. **免責表示**: 全ページフッターに「本サイトは公開情報の整理であり、正確性を保証しません。
   申請前に必ず公式ページをご確認ください。」を表示する。
3. **締切切れの自動除外**: 締切超過項目は一覧から除外するが、削除はせずstatus="closed"にする。
4. **推測でデータを補完しない**: 取得できないフィールドは「不明」/null。金額・締切をAIに推測させない。

## パイプライン

```
scripts/fetch_jgrants.py   # jGrants公開API → data/subsidies.json にupsert
scripts/fetch_jnet21.py    # J-Net21 RSS（フェーズ2）
scripts/enrich.py          # Claude Batch APIで要約+カテゴリ分類、新規項目のみ（フェーズ2）
scripts/update_status.py   # 締切からstatus (open/closing_soon/closed) を再計算
scripts/generate_site.py   # data/subsidies.json → docs/ 配下にJinja2でHTML生成
```

daily.yml（GitHub Actions）はこの順で実行し、各fetchはソース単位でtry/exceptし合いに失敗を波及させない。

## jGrants API利用時の注意（実装時に判明した仕様）

- `GET /exp/v1/public/subsidies` は `keyword` パラメータが必須（2文字以上）。ページングは無く、
  マッチした全件を一度に返す。複数の広いキーワードで検索して`id`で重複排除している。
- `acceptance=1`（募集中フラグ）は自治体側の手動設定であり、締切日を過ぎていても`1`のままの
  データが存在する。**表示側のstatusは必ずupdate_status.pyで締切日から再計算する**。
- 詳細は `GET /exp/v1/public/subsidies/id/{id}` で取得。`front_subsidy_detail_page_url`が
  jGrantsポータル上の公式詳細ページURL（official_url/detail_urlとして使用）。
- `industry`（対象業種）フィールドの区切り文字は `/` と `、` の両方が使われ、`・`は業種名内部の
  区切り（例:「電気・ガス・熱供給・水道業」は1つの業種名）なので分割してはいけない。
- `institution_name`（実施機関）はnullのことが多く、まれにtitleと同じ値が入っていることもある
  （データ提供元側の入力の揺れ。推測で補完せずそのまま表示する）。
- レスポンスは正しくUTF-8だが、Windows上でPythonから直接printすると既定のコンソール
  コードページにより文字化けする。`PYTHONUTF8=1`環境変数を設定して実行すること。

## データモデル

`data/subsidies.json`（配列、各要素のスキーマ）は実装仕様書（当初のチャット指示）を参照。
主要フィールド: id, source, title, organization, summary, catch_phrase, amount_max, amount_text,
subsidy_rate, deadline, start_date, target_industries, target_area, category, official_url,
detail_url, status, first_seen, last_updated。

## 実装フェーズの状態

- フェーズ1（MVP）: 完了。fetch_jgrants.py単体でsubsidies.json生成、generate_site.pyで
  トップ+詳細ページ生成（要約なしでも動作）。GitHub Pages公開・Actions日次実行は未設定
  （リポジトリ作成・pushはユーザーの指示待ち）。
- フェーズ2以降: 未着手（enrich.py、fetch_jnet21.py、カテゴリ/地域ページ、検索、
  closing-soon.html、JSON-LD、sitemap.xml）。

## UI改善フェーズ1 作業ルール（2026-07-13 追記）

トップページUI改善（検索窓配置・地域/目的/業種の絞り込み・締切/新着ソート・
要約付きカード・詳細ページ遷移）を行うにあたり、以下を追加で遵守すること。

### 着手前に必ず守ること

- **`SPEC.md`（UI改善フェーズ1版）を必読**。対象範囲・完了条件・スコープ外はすべてそこに定義。
- **実装計画を先に提示し、承認を得てから着手**すること。計画には、変更ファイル一覧・
  実装手順・既存の検索/フィルタ機能への影響とデグレ防止方針・完了条件との対応表を含める。
- 作業中に仕様変更の要望が出た場合は、**先に SPEC.md を更新して差分を提示**し、承認を得てから進める。

### 本フェーズのスコープ外（上記4原則に加えて厳守）

- 詳細ページのデザイン改修（遷移先として利用するのみ）
- 市区町村単位の検索（47都道府県まで）
- プライバシーポリシー・運営者情報ページの新設
- 実際の広告タグの挿入
- データ取得・要約生成ロジックの新設（カード要約は既存 `summary` を使用。
  空の場合は「推測でデータを補完しない」原則に従い、AI生成で埋めない）

### 作業上の制約

- ブラウザツール（claude-in-chrome）は使用しないこと。
- Node.js 未導入環境のため、ビルドツールに依存しない構成とすること。

### 完了時の報告

- 変更したファイルの一覧
- SPEC.md 完了条件チェックリストの充足状況
- スコープ外に手を出していないことの確認
