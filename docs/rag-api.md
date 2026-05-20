# RAG API 仕様書

## 1. 概要

RAG API は、セマンティック検索を担う内部 FastAPI サービスである。`mcp-server` からのリクエストを受け取り、クエリをベクトル化して Qdrant を検索し、結果を返す。

- **フレームワーク**: FastAPI + uvicorn
- **ポート**: `8000`（Docker 内部ネットワークのみ・外部非公開）
- **Embedding モデル**: `intfloat/multilingual-e5-large`（ローカル実行）
- **フォールバック**: `nomic-embed-text`（Ollama 経由）
- **依存先**: `qdrant:6333`

---

## 2. エンドポイント一覧

| メソッド | パス | 概要 |
|---|---|---|
| `POST` | `/search` | クエリによるセマンティック検索 |
| `GET` | `/requirement/{standard}/{req_id}` | 要件 ID による詳細取得 |
| `GET` | `/categories` | 章・セクション一覧取得 |
| `GET` | `/health` | ヘルスチェック |

---

## 3. エンドポイント詳細

### 3-1. POST /search

自然言語クエリをベクトル化し、Qdrant でセマンティック検索を行う。

#### リクエスト

```http
POST /search
Content-Type: application/json
```

```json
{
  "query": "セッション管理の要件",
  "standard": "ASVS",
  "level": null,
  "top_k": 5
}
```

| フィールド | 型 | 必須 | デフォルト | 説明 |
|---|---|---|---|---|
| `query` | string | ✅ | — | 検索クエリ（日本語可） |
| `standard` | string \| null | — | `null` | 絞り込む標準名（`"ASVS"` / `"AISVS"`） |
| `level` | integer \| null | — | `null` | 絞り込むレベル（`1` / `2` / `3`） |
| `top_k` | integer | — | `5` | 返却件数（1〜20） |

#### 内部処理フロー

```
1. クエリを Embedding
   embedding_input = "query: {query}"
   vector = embedder.encode(embedding_input)

2. Qdrant で検索
   - standard が指定された場合: 対象コレクションのみ検索
   - standard が null の場合: 全コレクションを検索してスコア順にマージ

3. メタデータフィルタを適用
   - level が指定された場合: { "level": { "match": { "value": level } } }

4. 結果を JSON に整形して返却
```

#### クエリの Embedding プレフィックス

`multilingual-e5-large` の推奨形式に従い、クエリには `"query: "` プレフィックスを付与する（ドキュメント側は `"passage: "` ）。

```python
query_vector = model.encode(f"query: {query}")
```

#### Qdrant 検索パラメータ

```python
client.search(
    collection_name=collection_name,
    query_vector=query_vector,
    query_filter=build_filter(level=level),
    limit=top_k,
    with_payload=True,
)
```

#### フィルタ構造

```python
def build_filter(level: int | None) -> Filter | None:
    if level is None:
        return None
    return Filter(
        must=[FieldCondition(key="level", match=MatchValue(value=level))]
    )
```

#### 全標準検索時のマージ

`standard=null` の場合、全コレクションを個別に検索して結果をスコア降順にマージする。

```python
all_results = []
for collection in ["asvs_requirements", "aisvs_requirements"]:
    results = client.search(collection, ...)
    all_results.extend(results)

all_results.sort(key=lambda r: r.score, reverse=True)
return all_results[:top_k]
```

#### レスポンス

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

---

### 3-2. GET /requirement/{standard}/{req_id}

要件 ID を指定して 1 件の詳細を取得する。Qdrant のペイロードインデックス（`req_id` フィールド）を使ったフィルタ検索で取得する。

#### リクエスト

```http
GET /requirement/ASVS/V1.1.1
```

| パスパラメータ | 型 | 説明 |
|---|---|---|
| `standard` | string | 標準名（`ASVS` / `AISVS`） |
| `req_id` | string | 要件 ID（例: `V1.1.1`, `C1.1.1`） |

#### 内部処理

```python
collection = f"{standard.lower()}_requirements"
results = client.scroll(
    collection_name=collection,
    scroll_filter=Filter(
        must=[FieldCondition(key="req_id", match=MatchValue(value=req_id))]
    ),
    limit=1,
    with_payload=True,
)
```

#### レスポンス（200 OK）

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

#### レスポンス（404 Not Found）

```json
{
  "detail": "Requirement 'V9.9.9' not found in ASVS"
}
```

---

### 3-3. GET /categories

指定した標準の章・セクション一覧と要件数を返す。Qdrant のペイロードをスキャンして集計する。

#### リクエスト

```http
GET /categories?standard=ASVS
```

| クエリパラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `standard` | string | — | 絞り込む標準名（省略時は全標準） |

#### レスポンス

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

---

### 3-4. GET /health

サービスの稼働状態と依存コンポーネントの状態を返す。

#### リクエスト

```http
GET /health
```

#### レスポンス（200 OK — 正常）

```json
{
  "status": "ok",
  "embedder": "multilingual-e5-large",
  "qdrant": "ok"
}
```

#### レスポンス（503 Service Unavailable — 異常）

```json
{
  "status": "degraded",
  "embedder": "nomic-embed-text (fallback)",
  "qdrant": "error: connection refused"
}
```

---

## 4. Embedder 仕様

### モデル選択ロジック

起動時にメインモデルのロードを試み、失敗した場合はフォールバックモデルを使用する。

```python
class Embedder:
    def __init__(self):
        try:
            self.model = SentenceTransformer("intfloat/multilingual-e5-large")
            self.model_name = "multilingual-e5-large"
            self.vector_size = 1024
        except Exception:
            self.model = OllamaEmbedder(model="nomic-embed-text")
            self.model_name = "nomic-embed-text (fallback)"
            self.vector_size = 768

    def encode(self, text: str) -> list[float]:
        return self.model.encode(text).tolist()
```

### プレフィックス規則

| 用途 | プレフィックス | 例 |
|---|---|---|
| 検索クエリ | `"query: "` | `"query: セッション管理の要件"` |
| ドキュメント（Ingest 時） | `"passage: "` | `"passage: V1.1.1: Verify that..."` |

---

## 5. 環境変数

| 変数名 | デフォルト | 説明 |
|---|---|---|
| `QDRANT_HOST` | `qdrant` | Qdrant ホスト名 |
| `QDRANT_PORT` | `6333` | Qdrant ポート |
| `EMBED_MODEL` | `intfloat/multilingual-e5-large` | メイン Embedding モデル |
| `FALLBACK_OLLAMA_URL` | `http://ollama:11434` | Ollama の URL（フォールバック用） |
| `LOG_LEVEL` | `info` | ログレベル（`debug` / `info` / `warning`） |

---

## 6. エラーレスポンス

| HTTP ステータス | 発生条件 | レスポンス例 |
|---|---|---|
| `400 Bad Request` | 不正なパラメータ（未知の `standard`、範囲外の `level` など） | `{"detail": "Invalid standard: MASVS"}` |
| `404 Not Found` | 要件 ID が存在しない | `{"detail": "Requirement 'V9.9.9' not found in ASVS"}` |
| `503 Service Unavailable` | Qdrant 接続失敗 | `{"detail": "Qdrant is unavailable"}` |

---

## 7. ファイル構成

```
rag-api/
└── src/
    ├── main.py          # FastAPI アプリ定義・エンドポイント登録
    ├── search.py        # 検索ロジック（Qdrant 検索・マージ）
    ├── embedder.py      # Embedding モデルのラッパー
    ├── qdrant_client.py # Qdrant クライアントの初期化・操作
    └── schemas.py       # リクエスト・レスポンスの Pydantic モデル
```
