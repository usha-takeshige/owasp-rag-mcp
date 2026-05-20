# データスキーマ仕様書

## 1. 概要

本ドキュメントでは、以下のデータスキーマを定義する。

1. **ソースデータスキーマ** — GitHub から取得する生データの構造（ASVS / AISVS）
2. **正規化レコードスキーマ** — パース後・Embedding 前の統一フォーマット
3. **Qdrant スキーマ** — Vector DB のコレクション定義とポイント構造
4. **MCP レスポンススキーマ** — MCP ツールが返却する JSON 構造

---

## 2. ソースデータスキーマ

### 2-1. ASVS（flat JSON）

ASVS は公式ビルド済みの flat JSON を使用する。

- **ファイル**: `5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.flat.json`
- **リポジトリ**: `OWASP/ASVS`（ブランチ: `master`）
- **件数**: 345 件（v5.0.0 時点）

#### フィールド定義

| フィールド名 | 型 | 例 | 説明 |
|---|---|---|---|
| `chapter_id` | string | `"V1"` | 章 ID |
| `chapter_name` | string | `"Encoding and Sanitization"` | 章名 |
| `section_id` | string | `"V1.1"` | セクション ID |
| `section_name` | string | `"Encoding and Sanitization Architecture"` | セクション名 |
| `req_id` | string | `"V1.1.1"` | 要件 ID（一意） |
| `req_description` | string | `"Verify that input is decoded..."` | 要件本文 |
| `L` | string | `"2"` | 検証レベル（`"1"` / `"2"` / `"3"`） |

#### JSON 構造例

```json
{
  "requirements": [
    {
      "chapter_id": "V1",
      "chapter_name": "Encoding and Sanitization",
      "section_id": "V1.1",
      "section_name": "Encoding and Sanitization Architecture",
      "req_id": "V1.1.1",
      "req_description": "Verify that input is decoded or unescaped into a canonical form only once...",
      "L": "2"
    }
  ]
}
```

---

### 2-2. AISVS（Markdown）

AISVS は章ごとの Markdown ファイルをパースして使用する。

- **ディレクトリ**: `1.0/en/*.md`（`0x10-C*.md` を対象とし、前書き・付録は除外）
- **リポジトリ**: `OWASP/AISVS`（ブランチ: `main`）
- **章数**: 14 章（C1〜C14）

#### Markdown 構造

```markdown
# C1 Training Data Integrity & Traceability      ← 章見出し（章 ID・章名）

## C1.1 Training Data Origin & Traceability      ← セクション見出し（セクション ID・セクション名）

| # | Description | Level |
| :--------: | --- | :---: |
| **1.1.1** | **Verify that** an up-to-date inventory... | 1 |
| **1.1.2** | **Verify that** training data processes... | 1 |
```

#### パース規則

| 要素 | 抽出方法 | 例 |
|---|---|---|
| 章 ID | `# C{n}` の `C{n}` 部分 | `C1` |
| 章名 | `# C{n}` の見出しテキスト（`C{n}` 以降） | `Training Data Integrity & Traceability` |
| セクション ID | `## C{n}.{m}` の `C{n}.{m}` 部分 | `C1.1` |
| セクション名 | `## C{n}.{m}` の見出しテキスト（`C{n}.{m}` 以降） | `Training Data Origin & Traceability` |
| 要件 ID | テーブル第1列の太字内容（`**1.1.1**` → `1.1.1`）を章 ID と結合 | `C1.1.1` |
| 要件本文 | テーブル第2列のテキスト（Markdown 書式を除去） | `Verify that an up-to-date inventory...` |
| レベル | テーブル第3列の数値 | `1` |

---

## 3. 正規化レコードスキーマ

パース完了後、Embedding 前の統一フォーマット。ASVS・AISVS 問わず同一構造に変換する。

### フィールド定義

| フィールド名 | 型 | ASVS マッピング | AISVS マッピング | 説明 |
|---|---|---|---|---|
| `standard` | string | `"ASVS"` | `"AISVS"` | 標準名 |
| `version` | string | `"5.0.0"` | `"1.0"` | バージョン（`sources.yml` から取得） |
| `req_id` | string | `req_id`（例: `V1.1.1`） | 章 ID + 要件番号（例: `C1.1.1`） | 要件 ID（標準内で一意） |
| `chapter_id` | string | `chapter_id`（例: `V1`） | 章 ID（例: `C1`） | 章 ID |
| `chapter_name` | string | `chapter_name` | 章名 | 章名 |
| `section_id` | string | `section_id`（例: `V1.1`） | セクション ID（例: `C1.1`） | セクション ID |
| `section_name` | string | `section_name` | セクション名 | セクション名 |
| `description` | string | `req_description` | 要件本文 | 要件の説明文（Embedding 対象） |
| `level` | integer | `int(L)`（例: `2`） | `int(Level)`（例: `1`） | 検証レベル（1 / 2 / 3） |

### 正規化レコード例（ASVS）

```json
{
  "standard": "ASVS",
  "version": "5.0.0",
  "req_id": "V1.1.1",
  "chapter_id": "V1",
  "chapter_name": "Encoding and Sanitization",
  "section_id": "V1.1",
  "section_name": "Encoding and Sanitization Architecture",
  "description": "Verify that input is decoded or unescaped into a canonical form only once...",
  "level": 2
}
```

### 正規化レコード例（AISVS）

```json
{
  "standard": "AISVS",
  "version": "1.0",
  "req_id": "C1.1.1",
  "chapter_id": "C1",
  "chapter_name": "Training Data Integrity & Traceability",
  "section_id": "C1.1",
  "section_name": "Training Data Origin & Traceability",
  "description": "Verify that an up-to-date inventory of every training-data source...",
  "level": 1
}
```

---

## 4. Qdrant スキーマ

### 4-1. コレクション定義

標準ごとに独立したコレクションを持つ。

| コレクション名 | 対象標準 | ベクトル次元数 | 距離関数 |
|---|---|---|---|
| `asvs_requirements` | ASVS | 1024 | Cosine |
| `aisvs_requirements` | AISVS | 1024 | Cosine |

> **フォールバック時の注意**: `nomic-embed-text`（768 次元）に切り替わった場合、次元数が異なるためコレクションを再作成する必要がある。メインモデルとフォールバックモデルの混在は不可。

#### コレクション作成パラメータ（Qdrant API）

```json
{
  "vectors": {
    "size": 1024,
    "distance": "Cosine"
  }
}
```

---

### 4-2. ポイントスキーマ

Qdrant に格納する 1 件のポイント（= 要件 1 件）の構造。

#### ポイント ID の生成規則

UUID v5（SHA-1 ベース）を使用し、同一要件の再投入時に同じ ID が生成されることで冪等性を担保する。

```
namespace = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # UUID namespace (URL)
point_id  = UUID5(namespace, "{standard}:{req_id}")
```

例:
- ASVS の `V1.1.1` → `UUID5(ns, "ASVS:V1.1.1")`
- AISVS の `C1.1.1` → `UUID5(ns, "AISVS:C1.1.1")`

#### ベクトル化対象テキスト

`multilingual-e5-large` の推奨形式に従い、ドキュメント投入時は `"passage: "` プレフィックスを付与する。

```
embedding_input = "passage: {req_id}: {description}"
```

例:
```
"passage: V1.1.1: Verify that input is decoded or unescaped into a canonical form only once..."
```

#### ペイロード（メタデータ）フィールド

| フィールド名 | 型 | 例 | Qdrant インデックス | 説明 |
|---|---|---|---|---|
| `standard` | string | `"ASVS"` | ✅ keyword | 標準名（フィルタ用） |
| `version` | string | `"5.0.0"` | — | バージョン |
| `req_id` | string | `"V1.1.1"` | ✅ keyword | 要件 ID（完全一致検索用） |
| `chapter_id` | string | `"V1"` | ✅ keyword | 章 ID（フィルタ用） |
| `chapter_name` | string | `"Encoding and Sanitization"` | — | 章名 |
| `section_id` | string | `"V1.1"` | ✅ keyword | セクション ID（フィルタ用） |
| `section_name` | string | `"Encoding and Sanitization Architecture"` | — | セクション名 |
| `description` | string | `"Verify that input is decoded..."` | — | 要件本文 |
| `level` | integer | `2` | ✅ integer | 検証レベル（フィルタ用） |

> ✅ は Qdrant のペイロードインデックスを作成するフィールド。フィルタ検索の高速化のために必要。

#### ポイント構造例

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "vector": [0.012, -0.034, 0.091, ...],
  "payload": {
    "standard": "ASVS",
    "version": "5.0.0",
    "req_id": "V1.1.1",
    "chapter_id": "V1",
    "chapter_name": "Encoding and Sanitization",
    "section_id": "V1.1",
    "section_name": "Encoding and Sanitization Architecture",
    "description": "Verify that input is decoded or unescaped into a canonical form only once...",
    "level": 2
  }
}
```

---

### 4-3. ペイロードインデックス定義

検索時のフィルタリングに使用するインデックスを以下のとおり作成する。

```json
{
  "field_name": "standard",
  "field_schema": "keyword"
}
{
  "field_name": "req_id",
  "field_schema": "keyword"
}
{
  "field_name": "chapter_id",
  "field_schema": "keyword"
}
{
  "field_name": "section_id",
  "field_schema": "keyword"
}
{
  "field_name": "level",
  "field_schema": "integer"
}
```

---

## 5. MCP レスポンススキーマ

`mcp-server` → LLM クライアントへ返却する JSON 構造。

### 5-1. search_requirements レスポンス

```json
{
  "results": [
    {
      "req_id": "V1.1.1",
      "standard": "ASVS",
      "version": "5.0.0",
      "level": 2,
      "chapter_id": "V1",
      "chapter_name": "Encoding and Sanitization",
      "section_id": "V1.1",
      "section_name": "Encoding and Sanitization Architecture",
      "description": "Verify that input is decoded or unescaped into a canonical form only once...",
      "score": 0.923
    }
  ],
  "total": 5,
  "query": "入力値のサニタイズ"
}
```

### 5-2. get_requirement レスポンス

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

### 5-3. list_categories レスポンス

```json
{
  "standard": "ASVS",
  "version": "5.0.0",
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
```

### 5-4. check_coverage レスポンス

```json
{
  "feature": "セッション管理機能",
  "results": [
    {
      "req_id": "V3.1.1",
      "standard": "ASVS",
      "level": 1,
      "description": "Verify the application never reveals session tokens...",
      "score": 0.891
    }
  ],
  "total": 8
}
```

---

## 6. フィールド対応表（横断）

各レイヤー間のフィールド対応をまとめる。

| 正規化レコード | Qdrant ペイロード | MCP レスポンス | 備考 |
|---|---|---|---|
| `standard` | `standard` | `standard` | — |
| `version` | `version` | `version` | — |
| `req_id` | `req_id` | `req_id` | — |
| `chapter_id` | `chapter_id` | `chapter_id` | — |
| `chapter_name` | `chapter_name` | `chapter_name` | — |
| `section_id` | `section_id` | `section_id` | — |
| `section_name` | `section_name` | `section_name` | — |
| `description` | `description` | `description` | — |
| `level` | `level` | `level` | — |
| —（生成） | —（UUID） | — | Point ID はレスポンスに含まない |
| —（生成） | — | `score` | Qdrant の類似度スコア（0〜1） |
| —（生成） | — | `total` | 検索結果の件数 |
