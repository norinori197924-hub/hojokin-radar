# チェックレポート（データ取得頻度・取得件数の拡大）

対象: `scripts/fetch_jgrants.py`（SEARCH_KEYWORDS拡張・REQUEST_INTERVAL_SEC変更・
search_ids()のtry/except追加）、`.github/workflows/daily.yml`（現状確認のみ、変更なし）

担当: checker サブエージェント

## 総合判定: CAUTION

CRITICAL・明確なバグは検出なし。今回の3変更自体は意図通り機能しているが、
キーワード拡張に伴うリクエスト数増加が既存の潜在的な弱点を顕在化させやすくして
いる点について対応を推奨。

## SAFE

- `search_ids()`への`try/except requests.RequestException`追加により、
  1キーワードの通信/HTTPエラーで検索フェーズ全体が停止する問題は解消。
- APIキー・秘密情報のハードコードなし（jGrants公開APIは認証不要、
  `ANTHROPIC_API_KEY`/`GA4_ID`は既存通りsecrets経由）。
- URLクエリインジェクション・XSSのリスクなし（`requests.get(params=...)`で
  自動エスケープ、HTML生成にも関与しない）。
- 追加した21キーワードはいずれもjGrants APIの`keyword`仕様（2文字以上）を満たす。
- `to_schema()`のNoneガード・「不明」/null補完ロジックは変更しておらず、
  CLAUDE.mdの「推測でデータを補完しない」原則に反する変更はない。
- 命名規則・ディレクトリ構成はCLAUDE.mdの既存パイプライン構成を踏襲。

## CAUTION（要対応）

1. **`resp.json()`のパース失敗（`json.JSONDecodeError`）が捕捉範囲外**
   `search_ids()`・`fetch_detail()`呼び出し側どちらも`requests.RequestException`
   のみを捕捉しており、不正/空レスポンスによる`JSONDecodeError`はスクリプト全体を
   停止させる。既存の穴だが、キーワード拡張でAPIコール数が5→21(検索)+候補id数
   (詳細)に増え、遭遇確率が上がった。
2. **Actions実行時間の増加に対しtimeout-minutesが未設定**
   `REQUEST_INTERVAL_SEC=1.1`自体はレート制限に対して妥当だが、リクエスト総数
   増加で1回の実行時間が確実に伸びる。`daily.yml`の`update`ジョブに
   `timeout-minutes`が設定されておらず、上限がGitHub既定値(6時間)任せになっている。

## 次工程

CAUTION 1（JSONDecodeErrorの捕捉漏れ）は「6. 修正」で対応する。
CAUTION 2（timeout-minutes）は実行時間の実測値を分析工程で確認したうえで
対応要否を判断する。
