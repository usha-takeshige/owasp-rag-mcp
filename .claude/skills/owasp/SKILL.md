---
name: owasp
description: OWASP ASVS / AISVS の要件を検索・参照・カバレッジ確認するスキル。セキュリティ要件の調査、機能実装のカバレッジ確認、PRのセキュリティレビューに使う。サブコマンド: search / coverage / get / categories / review
allowed-tools: mcp__owasp-rag__search_requirements, mcp__owasp-rag__get_requirement, mcp__owasp-rag__list_categories, mcp__owasp-rag__check_coverage, Bash(git diff *), Bash(git diff)
---

# OWASP RAG スキル

引数 `$ARGUMENTS` の先頭キーワードでサブコマンドを判定する。キーワードがなければ `search` として扱う。

MCPツール呼び出しが接続エラーで失敗した場合は、処理を中断して「`docker compose up -d` を実行してから再試行してください」と伝える。

---

## search — 自然言語で要件を検索

**判定:** 引数が `search` で始まる、またはキーワードなしの自然言語

1. 引数からクエリ本文、`--standard`（`ASVS`/`AISVS`）、`--level`（`1`/`2`/`3`）、`--top`（件数）を解析する
2. `mcp__owasp-rag__search_requirements` を呼び出す
3. 結果を表形式で出力する:

   | 要件ID | 標準 | Lv | 章 / セクション | 説明 | スコア |
   |---|---|---|---|---|---|

4. 上位3件について、要件の意味と実装時の注意点を日本語で1〜2文補足する
5. 0件の場合は「該当する要件が見つかりませんでした。クエリを変えて再試行してください」と伝える

**例:** `/owasp search セッション管理` / `/owasp search input validation --standard ASVS --level 1`

---

## coverage — 機能のOWASPカバレッジを確認

**判定:** 引数が `coverage` で始まる

1. 引数から機能説明、`--standard`、`--top`（デフォルト10）を解析する
2. `mcp__owasp-rag__check_coverage` を呼び出す
3. 結果を標準・章ごとにグループ化して表示する
4. スコアが0.7未満または未登場の章を「未カバーの可能性がある領域」として指摘する

**例:** `/owasp coverage JWT を使ったユーザー認証機能` / `/owasp coverage プロンプトインジェクション対策 --standard AISVS`

---

## get — 要件IDで詳細を取得

**判定:** 引数が `get` で始まる、または `V1.2.3` / `C1.2.3` 形式のIDが含まれる

1. 引数から `req_id`（例: `V2.1.1`）と `standard`（`ASVS` または `AISVS`）を取得する
2. `mcp__owasp-rag__get_requirement` を呼び出す
3. 全フィールドを表示し、`description` を日本語に翻訳して添える

**例:** `/owasp get V2.1.1 ASVS` / `/owasp get C1.1.1 AISVS`

---

## categories — 章・セクション一覧を表示

**判定:** 引数が `categories` で始まる

1. 引数から `standard`（省略可）を取得する
2. `mcp__owasp-rag__list_categories` を呼び出す
3. 章 > セクション > 要件数 のツリー形式で表示する

**例:** `/owasp categories` / `/owasp categories ASVS`

---

## review — 差分をOWASP要件と照合

**判定:** 引数が `review` で始まる

1. `git diff main --stat` で変更ファイル一覧を取得する
2. `git diff main` で差分を取得する（大きすぎる場合は `--stat` の結果だけを使う）
3. 差分から認証・入力検証・暗号化・セッション管理など関連するセキュリティ領域を推定する
4. 推定したキーワードで `mcp__owasp-rag__search_requirements` を1〜3回呼び出す
5. 結果を以下の2セクションに分けて出力する:
   - **満たすべき要件** — 差分のどのファイル・行と関係するかをパスで明示する
   - **未対応の可能性がある要件** — 対応が必要な理由を一言添える

**例:** `/owasp review` / `/owasp review --standard ASVS`

---

$ARGUMENTS
