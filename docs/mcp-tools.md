# MCP ツール仕様書

## 1. 概要

本システムが提供する MCP（Model Context Protocol）ツールの仕様を定義する。

- **トランスポート**: HTTP/SSE（Streamable HTTP）
- **エンドポイント**: `http://localhost:8080`（デフォルト）
- **プロトコル**: MCP 仕様に準拠

### ツール一覧

| ツール名 | 概要 | 用途 |
|---|---|---|
| `search_requirements` | 自然言語クエリで関連要件を検索 | 要件の横断検索（主力） |
| `get_requirement` | 要件 ID を指定して詳細を取得 | 特定要件の参照 |
| `list_categories` | 標準のカテゴリ・章一覧を取得 | 構造の把握・フィルタ条件確認 |
| `check_coverage` | 機能説明から関連要件群を取得 | 仕様レビュー・カバレッジ確認 |

---

## 2. 共通仕様

### エラーレスポンス

いずれのツールも、エラー発生時は MCP 標準のエラー形式で返却する。

```json
{
  "error": {
    "code": -32602,
    "message": "Invalid params: unknown standard 'MASVS'"
  }
}
```

| エラーコード | 意味 | 発生例 |
|---|---|---|
| `-32602` | 不正なパラメータ | 未知の `standard` 値、範囲外の `level` |
| `-32603` | 内部エラー | RAG API 接続失敗、Qdrant 接続失敗 |

### 列挙型の有効値

| パラメータ | 有効値 |
|---|---|
| `standard` | `"ASVS"`, `"AISVS"` |
| `level` | `1`, `2`, `3` |

---

## 3. ツール詳細仕様

### 3-1. search_requirements

自然言語クエリをベクトル化し、意味的に近い要件を検索して返す。日本語クエリでの英語ドキュメント検索（クロスリンガル検索）に対応する。

#### 入力パラメータ

| パラメータ名 | 型 | 必須 | デフォルト | 説明 |
|---|---|---|---|---|
| `query` | string | ✅ | — | 検索クエリ（自然言語・日本語可） |
| `standard` | string | — | `null`（全標準） | 絞り込む標準名（`"ASVS"` / `"AISVS"`） |
| `level` | integer | — | `null`（全レベル） | 絞り込むレベル（`1` / `2` / `3`） |
| `top_k` | integer | — | `5` | 返却件数（1〜20） |

#### 出力スキーマ

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

| フィールド | 型 | 説明 |
|---|---|---|
| `results` | array | 検索結果の配列（スコア降順） |
| `results[].req_id` | string | 要件 ID |
| `results[].standard` | string | 標準名 |
| `results[].version` | string | バージョン |
| `results[].level` | integer | 検証レベル |
| `results[].chapter_id` | string | 章 ID |
| `results[].chapter_name` | string | 章名 |
| `results[].section_id` | string | セクション ID |
| `results[].section_name` | string | セクション名 |
| `results[].description` | string | 要件本文 |
| `results[].score` | float | コサイン類似度（0〜1） |
| `total` | integer | 返却件数 |
| `query` | string | 受け取ったクエリ（確認用） |

#### 使用例

```
# 全標準を横断してセッション管理の要件を検索
search_requirements(query="セッション管理の要件")

# ASVS のレベル1要件のみに絞り込んで検索
search_requirements(query="input validation", standard="ASVS", level=1, top_k=10)

# AI システムのプロンプトインジェクション対策要件を検索
search_requirements(query="prompt injection", standard="AISVS")
```

---

### 3-2. get_requirement

要件 ID を指定して、その要件の詳細情報を取得する。

#### 入力パラメータ

| パラメータ名 | 型 | 必須 | 説明 |
|---|---|---|---|
| `req_id` | string | ✅ | 要件 ID（例: `"V1.1.1"`, `"C1.1.1"`） |
| `standard` | string | ✅ | 標準名（`"ASVS"` / `"AISVS"`） |

> `req_id` は標準ごとに独立した ID 体系を持つため、`standard` による明示が必須。

#### 出力スキーマ

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

要件が見つからない場合はエラーコード `-32602` を返す。

#### 使用例

```
get_requirement(req_id="V1.1.1", standard="ASVS")
get_requirement(req_id="C1.1.1", standard="AISVS")
```

---

### 3-3. list_categories

指定した標準の章・セクション一覧と、各セクションの要件数を返す。検索前のフィルタ条件の確認や、標準の全体構造把握に使用する。

#### 入力パラメータ

| パラメータ名 | 型 | 必須 | デフォルト | 説明 |
|---|---|---|---|---|
| `standard` | string | — | `null`（全標準） | 絞り込む標準名 |

#### 出力スキーマ

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
    },
    {
      "standard": "AISVS",
      "version": "1.0",
      "total_requirements": 120,
      "chapters": [
        {
          "chapter_id": "C1",
          "chapter_name": "Training Data Integrity & Traceability",
          "sections": [
            {
              "section_id": "C1.1",
              "section_name": "Training Data Origin & Traceability",
              "count": 4
            }
          ]
        }
      ]
    }
  ]
}
```

#### 使用例

```
# 全標準の章一覧を取得
list_categories()

# ASVS の章一覧のみ取得
list_categories(standard="ASVS")
```

---

### 3-4. check_coverage

機能や仕様の説明文を受け取り、それに関連する要件群を返す。設計・実装した機能が ASVS / AISVS のどの要件をカバーしているかを確認する用途に使用する。

`search_requirements` との違いは、返却件数が多め（デフォルト 10 件）で、複数標準にまたがる結果を常に返す点にある。

#### 入力パラメータ

| パラメータ名 | 型 | 必須 | デフォルト | 説明 |
|---|---|---|---|---|
| `feature` | string | ✅ | — | 機能・仕様の説明文（自然言語・日本語可） |
| `standard` | string | — | `null`（全標準） | 絞り込む標準名 |
| `top_k` | integer | — | `10` | 返却件数（1〜50） |

#### 出力スキーマ

```json
{
  "feature": "ユーザー認証機能。パスワードと MFA を組み合わせた認証を提供する。",
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

| フィールド | 型 | 説明 |
|---|---|---|
| `feature` | string | 受け取った機能説明（確認用） |
| `results` | array | 関連要件の配列（スコア降順） |
| `total` | integer | 返却件数 |

#### 使用例

```
# 認証機能のカバレッジを確認
check_coverage(feature="ユーザー認証機能。パスワードと MFA を組み合わせた認証を提供する。")

# AI モデルの入力バリデーション機能のカバレッジを AISVS で確認
check_coverage(
  feature="ユーザー入力をサニタイズし、プロンプトインジェクションを防ぐ機能",
  standard="AISVS",
  top_k=15
)
```

---

## 4. ツール選択ガイド

| やりたいこと | 使うツール |
|---|---|
| キーワードや概念で要件を探したい | `search_requirements` |
| 要件 ID が分かっていて詳細を確認したい | `get_requirement` |
| どんな章・カテゴリがあるか確認したい | `list_categories` |
| 設計・実装した機能が要件を満たしているか確認したい | `check_coverage` |
| 特定レベル（例: L1 のみ）の要件に絞り込みたい | `search_requirements`（`level` パラメータ） |
| 特定標準（例: AISVS のみ）に絞り込みたい | `search_requirements`（`standard` パラメータ） |
