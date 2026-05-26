# MCP ツール仕様書（owasp-rag-mcp）

## 概要

- **トランスポート**: HTTP/SSE（Streamable HTTP）
- **エンドポイント**: `.env` の設定に従う（ポート番号は環境変数で変更可能）
- **対応標準**: ASVS v5.0-RC1、AISVS v1.0

## ツール一覧

| ツール名 | 概要 |
|---|---|
| `search_requirements` | 自然言語クエリで関連要件をセマンティック検索（日本語可） |
| `get_requirement` | 要件 ID を指定して詳細を取得 |
| `list_categories` | 標準のカテゴリ・章一覧を返す |
| `check_coverage` | 機能説明から関連要件群を返す（仕様レビュー向け） |

---

## search_requirements

### 入力パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|---|---|---|---|---|
| `query` | string | ✅ | — | 検索クエリ（自然言語・日本語可） |
| `standard` | string | — | null（全標準） | `"ASVS"` / `"AISVS"` |
| `level` | integer | — | null（全レベル） | `1` / `2` / `3` |
| `top_k` | integer | — | 5 | 返却件数（1〜20） |

### 出力スキーマ

```json
{
  "results": [
    {
      "req_id": "V3.2.1",
      "standard": "ASVS",
      "version": "5.0.0",
      "level": 1,
      "chapter_id": "V3",
      "chapter_name": "Session Management",
      "section_id": "V3.2",
      "section_name": "Session Binding",
      "description": "Verify the application generates a new session token on user authentication.",
      "score": 0.923
    }
  ],
  "total": 5,
  "query": "セッション管理の要件"
}
```

### 使用例

```
search_requirements(query="セッション管理の要件")
search_requirements(query="input validation", standard="ASVS", level=1, top_k=10)
search_requirements(query="prompt injection", standard="AISVS")
```

---

## get_requirement

### 入力パラメータ

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `req_id` | string | ✅ | 例: `"V1.1.1"`, `"C1.1.1"` |
| `standard` | string | ✅ | `"ASVS"` / `"AISVS"` |

### 出力スキーマ

```json
{
  "req_id": "V1.1.1",
  "standard": "ASVS",
  "version": "5.0.0",
  "level": 2,
  "chapter_id": "V1",
  "chapter_name": "Encoding and Sanitization",
  "section_id": "V1.1",
  "section_name": "Encoding and Sanitization Architecture",
  "description": "Verify that input is decoded or unescaped into a canonical form only once..."
}
```

### 使用例

```
get_requirement(req_id="V1.1.1", standard="ASVS")
get_requirement(req_id="C1.1.1", standard="AISVS")
```

---

## list_categories

### 入力パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|---|---|---|---|---|
| `standard` | string | — | null（全標準） | `"ASVS"` / `"AISVS"` |

### 出力スキーマ

```json
{
  "standards": [
    {
      "standard": "ASVS",
      "version": "5.0.0",
      "total_requirements": 345,
      "chapters": [
        {
          "chapter_id": "V1",
          "chapter_name": "Encoding and Sanitization",
          "sections": [
            {
              "section_id": "V1.1",
              "section_name": "Encoding and Sanitization Architecture",
              "count": 3
            }
          ]
        }
      ]
    }
  ]
}
```

### 使用例

```
list_categories()
list_categories(standard="ASVS")
```

---

## check_coverage

### 入力パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|---|---|---|---|---|
| `feature` | string | ✅ | — | 機能・仕様の説明文（自然言語・日本語可） |
| `standard` | string | — | null（全標準） | `"ASVS"` / `"AISVS"` |
| `top_k` | integer | — | 10 | 返却件数（1〜50） |

### 出力スキーマ

```json
{
  "feature": "ユーザー認証機能。パスワードとMFAを組み合わせた認証を提供する。",
  "results": [
    {
      "req_id": "V2.1.1",
      "standard": "ASVS",
      "version": "5.0.0",
      "level": 1,
      "chapter_id": "V2",
      "chapter_name": "Authentication",
      "section_id": "V2.1",
      "section_name": "Password Security",
      "description": "Verify that user set passwords are at least 8 characters in length.",
      "score": 0.881
    }
  ],
  "total": 10
}
```

### 使用例

```
check_coverage(feature="ユーザー認証機能。パスワードとMFAを組み合わせた認証を提供する。")
check_coverage(
  feature="ユーザー入力をサニタイズし、プロンプトインジェクションを防ぐ機能",
  standard="AISVS",
  top_k=15
)
```

---

## エラーレスポンス

| エラーコード | 意味 | 発生例 |
|---|---|---|
| `-32602` | 不正なパラメータ | 未知の `standard` 値、範囲外の `level` |
| `-32603` | 内部エラー | RAG API 接続失敗、Qdrant 接続失敗 |

---

## ツール選択ガイド

| やりたいこと | 使うツール |
|---|---|
| キーワードや概念で要件を探したい | `search_requirements` |
| 要件 ID が分かっていて詳細を確認したい | `get_requirement` |
| どんな章・カテゴリがあるか確認したい | `list_categories` |
| 設計・実装した機能が要件を満たしているか確認したい | `check_coverage` |
| 特定レベル（例: L1のみ）の要件に絞り込みたい | `search_requirements`（`level` パラメータ） |
| 特定標準（例: AISVSのみ）に絞り込みたい | `search_requirements`（`standard` パラメータ） |