# owasp — OWASP RAG MCP スキル

OWASP ASVS / AISVS の要件を MCP ツール経由で参照・検索するスキル。

## 使い方

```
/owasp <サブコマンド> [引数]
```

サブコマンドが省略された場合、または引数が自然言語の質問・機能説明の場合は `search` として扱う。

---

## サブコマンド一覧

### search [クエリ] [オプション]

自然言語で ASVS / AISVS の要件を検索する。日本語クエリでも英語ドキュメントを横断検索できる。

**引数の書式例:**
- `/owasp search セッション管理の要件`
- `/owasp search input validation --standard ASVS --level 1`
- `/owasp search プロンプトインジェクション対策 --standard AISVS`

**オプション:**
- `--standard ASVS|AISVS` — 対象標準を絞り込む（省略時は両方）
- `--level 1|2|3` — 検証レベルで絞り込む
- `--top 数字` — 返却件数（デフォルト5、最大20）

**実行手順:**
1. `mcp__owasp-rag__search_requirements` を呼び出す
2. 結果を「要件ID / 章 / セクション / 説明 / スコア」の表形式で表示する
3. 上位3件については要件の意味と開発時の注意点を日本語で補足する

---

### coverage <機能説明>

実装した（または実装予定の）機能の説明を渡し、関連する ASVS / AISVS 要件を洗い出す。設計レビューや実装後のカバレッジ確認に使う。

**引数の書式例:**
- `/owasp coverage JWT を使ったユーザー認証機能`
- `/owasp coverage ユーザー入力をサニタイズしてプロンプトインジェクションを防ぐ機能 --standard AISVS`

**オプション:**
- `--standard ASVS|AISVS` — 対象標準を絞り込む
- `--top 数字` — 返却件数（デフォルト10、最大50）

**実行手順:**
1. `mcp__owasp-rag__check_coverage` を呼び出す
2. 結果を標準・章ごとにグループ化して表示する
3. カバーできていない可能性のある領域（スコアが低い、または未登場の章）を指摘する

---

### get <要件ID> <ASVS|AISVS>

要件IDを指定して詳細を取得する。`search` や `coverage` の結果に含まれるIDを使って詳細確認する際に使う。

**引数の書式例:**
- `/owasp get V2.1.1 ASVS`
- `/owasp get C1.1.1 AISVS`

**実行手順:**
1. `mcp__owasp-rag__get_requirement` を呼び出す
2. 要件の全フィールドを表示する
3. 要件本文を日本語に翻訳して補足する

---

### categories [ASVS|AISVS]

標準の章・セクション一覧と各セクションの要件数を表示する。どの章に何件の要件があるかを確認する際に使う。

**引数の書式例:**
- `/owasp categories` — 全標準
- `/owasp categories ASVS`
- `/owasp categories AISVS`

**実行手順:**
1. `mcp__owasp-rag__list_categories` を呼び出す
2. 章・セクションをツリー形式で表示する

---

### review

現在のブランチの変更差分（`git diff main`）を解析し、セキュリティ観点でのOWASP要件を照合する。PRレビュー前のセルフチェックに使う。

**引数の書式例:**
- `/owasp review`
- `/owasp review --standard ASVS`

**実行手順:**
1. `git diff main --stat` と `git diff main` で変更ファイルと差分を取得する
2. 変更内容から関連するセキュリティ領域（認証・入力検証・暗号化など）を推定する
3. 推定したキーワードで `mcp__owasp-rag__search_requirements` を1〜3回呼び出す
4. 関連度の高い要件を一覧表示し、「この変更で満たすべき要件」と「未対応の可能性がある要件」に分類する
5. 各要件について、変更差分のどの部分に関係するかをファイル・行番号付きで指摘する

---

## 引数の解釈ルール

`$ARGUMENTS` の内容に応じて以下のように動作する：

| 入力パターン | 動作 |
|---|---|
| `search ...` | search サブコマンドを実行 |
| `coverage ...` | coverage サブコマンドを実行 |
| `get <ID> <標準>` | get サブコマンドを実行 |
| `categories [標準]` | categories サブコマンドを実行 |
| `review` | review サブコマンドを実行 |
| サブコマンドなし（自然言語） | search として処理 |

---

## 前提条件

- `docker compose up -d` でサービスが起動済みであること
- MCP サーバーが `http://localhost:8080` で稼働していること
- サービスが停止している場合は「`docker compose up -d` を実行してから再試行してください」と案内する

## 引数

$ARGUMENTS
