# Ingest パイプライン仕様書

## 1. 概要

Ingest パイプラインは、OWASP ASVS / AISVS のドキュメントを GitHub から取得し、Qdrant へ投入するバッチ処理である。初回セットアップ時および標準文書の更新時に実行する。

```
sources.yml → fetcher → parser → chunker → embedder → upserter → qdrant
```

- **実行方式**: `docker compose run --rm ingest`（コンテナ起動後に処理を実行し停止）
- **冪等性**: 同一ドキュメントを再実行しても重複が生じない（upsert による上書き）
- **設定ファイル**: `ingest/data/sources.yml`

---

## 2. ソース設定（sources.yml）

### フォーマット

```yaml
sources:
  - standard: ASVS
    version: "5.0.0"
    repo: OWASP/ASVS
    branch: master
    format: json_flat
    path: 5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.flat.json

  - standard: AISVS
    version: "1.0"
    repo: OWASP/AISVS
    branch: main
    format: markdown
    paths:
      - 1.0/en/
    path_pattern: "0x10-C*.md"
```

### フィールド定義

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `standard` | string | ✅ | 標準名（コレクション名・メタデータに使用） |
| `version` | string | ✅ | バージョン番号（メタデータに使用） |
| `repo` | string | ✅ | GitHub リポジトリ（`{owner}/{repo}` 形式） |
| `branch` | string | ✅ | 取得対象ブランチ |
| `format` | string | ✅ | ソースフォーマット（`json_flat` / `markdown`） |
| `path` | string | `json_flat` 時必須 | ファイルの相対パス |
| `paths` | list | `markdown` 時必須 | 対象ディレクトリのリスト |
| `path_pattern` | string | — | ファイル名フィルタ（glob パターン） |

---

## 3. 各コンポーネント仕様

### 3-1. fetcher（GitHub からの取得）

GitHub API を使用してソースファイルを取得する。

#### 動作

| フォーマット | 取得方法 |
|---|---|
| `json_flat` | `path` で指定した単一ファイルを取得 |
| `markdown` | `paths` で指定したディレクトリ内のファイルを `path_pattern` でフィルタして全件取得 |

#### GitHub API

```
GET https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}
```

- レート制限に対応するため、`GITHUB_TOKEN` が設定されている場合は認証ヘッダーを付与する
- `GITHUB_TOKEN` が未設定の場合は未認証リクエスト（60 req/h の制限あり）でも動作する

#### 出力

```python
@dataclass
class FetchedSource:
    standard: str          # 標準名（"ASVS" / "AISVS"）
    version: str           # バージョン
    format: str            # "json_flat" / "markdown"
    content: str           # ファイルの生テキスト
    filename: str          # ファイル名（ログ用）
```

---

### 3-2. parser（要件単位への正規化）

フォーマットごとに異なる解析処理で、正規化レコードのリストを生成する。

#### ASVS パーサー（json_flat）

flat JSON の `requirements` 配列をそのまま正規化レコードへ変換する。

```python
record = NormalizedRecord(
    standard="ASVS",
    version=source.version,
    req_id=item["req_id"],           # 例: "V1.1.1"
    chapter_id=item["chapter_id"],   # 例: "V1"
    chapter_name=item["chapter_name"],
    section_id=item["section_id"],   # 例: "V1.1"
    section_name=item["section_name"],
    description=item["req_description"],
    level=int(item["L"]),
)
```

#### AISVS パーサー（markdown）

Markdown の見出しとテーブルを正規表現で解析する。

**解析フロー:**

```
1. `# C{n} {章名}` にマッチ → chapter_id, chapter_name を更新
2. `## C{n}.{m} {セクション名}` にマッチ → section_id, section_name を更新
3. テーブル行（`| **{n.m.k}** | {説明} | {レベル} |`）にマッチ → レコード生成
```

**正規表現パターン:**

```python
CHAPTER_PATTERN  = re.compile(r"^# (C\d+)\s+(.+)$", re.MULTILINE)
SECTION_PATTERN  = re.compile(r"^## (C\d+\.\d+)\s+(.+)$", re.MULTILINE)
REQ_ROW_PATTERN  = re.compile(
    r"^\|\s*\*\*(\d+\.\d+\.\d+)\*\*\s*\|(.+?)\|(\d)\s*\|",
    re.MULTILINE
)
```

**req_id の生成:**

テーブルの `#` 列は `1.1.1` 形式で記載されるため、章 ID を付与する。

```python
# テーブルの `#` 列: "1.1.1"
# 章 ID: "C1"
req_id = f"C{table_req_number}"  # → "C1.1.1"
```

#### 出力（共通）

```python
@dataclass
class NormalizedRecord:
    standard: str
    version: str
    req_id: str
    chapter_id: str
    chapter_name: str
    section_id: str
    section_name: str
    description: str
    level: int
```

---

### 3-3. chunker（チャンク生成）

要件 1 件 = チャンク 1 件として分割する。各チャンクに Embedding 対象テキストとメタデータを付与する。

#### Embedding 対象テキストの生成

`multilingual-e5-large` の推奨形式に従い、`"passage: "` プレフィックスを付与する。

```python
embedding_text = f"passage: {record.req_id}: {record.description}"
```

例:
```
passage: V1.1.1: Verify that input is decoded or unescaped into a canonical form only once...
```

#### ポイント ID の生成

UUID v5（SHA-1 ベース）を使用し、同一要件への再実行で同じ ID が生成されるよう冪等性を担保する。

```python
import uuid

NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # URL namespace

def generate_point_id(standard: str, req_id: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{standard}:{req_id}"))
```

#### 出力

```python
@dataclass
class Chunk:
    point_id: str           # UUID v5
    embedding_text: str     # "passage: {req_id}: {description}"
    payload: dict           # Qdrant ペイロード（正規化レコードの全フィールド）
```

---

### 3-4. embedder（ベクトル化）

チャンクの `embedding_text` をベクトルに変換する。バッチ処理で効率化する。

#### モデル優先順位

| 優先度 | モデル | 次元数 | 実行方式 |
|---|---|---|---|
| 1（メイン） | `intfloat/multilingual-e5-large` | 1024 | ローカル（HuggingFace） |
| 2（フォールバック） | `nomic-embed-text` | 768 | Ollama API |

起動時にメインモデルのロードを試み、失敗した場合はフォールバックモデルを使用する。

> **注意**: メインとフォールバックでは次元数が異なるため、モデルを切り替える場合は Qdrant コレクションを再作成する必要がある。

#### バッチ処理

メモリ効率のため、チャンクを分割してバッチ処理する。

```python
BATCH_SIZE = 32  # デフォルト（環境変数 EMBED_BATCH_SIZE で変更可）

for batch in chunks_in_batches(chunks, BATCH_SIZE):
    texts = [chunk.embedding_text for chunk in batch]
    vectors = model.encode(texts)
```

#### 出力

```python
@dataclass
class EmbeddedChunk:
    point_id: str
    vector: list[float]    # 1024 次元（メイン）または 768 次元（フォールバック）
    payload: dict
```

---

### 3-5. upserter（Qdrant への投入）

埋め込み済みチャンクを Qdrant へ投入する。

#### コレクションの初期化

コレクションが存在しない場合は自動作成する。既存コレクションはそのまま使用する。

```python
def ensure_collection(client, collection_name: str, vector_size: int):
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        # ペイロードインデックスの作成
        for field, schema in PAYLOAD_INDEXES.items():
            client.create_payload_index(collection_name, field, schema)
```

#### ペイロードインデックス

```python
PAYLOAD_INDEXES = {
    "standard":   PayloadSchemaType.KEYWORD,
    "req_id":     PayloadSchemaType.KEYWORD,
    "chapter_id": PayloadSchemaType.KEYWORD,
    "section_id": PayloadSchemaType.KEYWORD,
    "level":      PayloadSchemaType.INTEGER,
}
```

#### Upsert

同一 `point_id` のデータは上書き更新される（冪等性の担保）。

```python
UPSERT_BATCH_SIZE = 100

def upsert_batch(client, collection_name: str, chunks: list[EmbeddedChunk]):
    points = [
        PointStruct(id=chunk.point_id, vector=chunk.vector, payload=chunk.payload)
        for chunk in chunks
    ]
    client.upsert(collection_name=collection_name, points=points)
```

#### コレクション選択ルール

| `standard` の値 | 投入先コレクション |
|---|---|
| `"ASVS"` | `asvs_requirements` |
| `"AISVS"` | `aisvs_requirements` |

---

## 4. 実行フロー（main.py）

```python
def main():
    sources = load_sources("ingest/data/sources.yml")
    embedder = Embedder()  # モデルロード（起動時に1回）

    for source_config in sources:
        # 1. 取得
        fetched = fetch(source_config)

        # 2. パース
        records = parse(fetched)

        # 3. チャンク生成
        chunks = chunk(records)

        # 4. Embedding（バッチ処理）
        embedded = embedder.embed(chunks)

        # 5. Qdrant 投入
        collection = f"{source_config.standard.lower()}_requirements"
        upsert(embedded, collection)

        log(f"[{source_config.standard}] {len(embedded)} 件投入完了")
```

---

## 5. エラーハンドリング

| エラー種別 | 対処 |
|---|---|
| GitHub API 接続失敗 | 最大3回リトライ（指数バックオフ） |
| GitHub API レート制限 | `Retry-After` ヘッダーに従って待機 |
| Markdown パース失敗（行単位） | 警告ログを出力してスキップ、処理継続 |
| Embedding 失敗 | フォールバックモデルへ切り替えてリトライ |
| Qdrant 接続失敗 | 最大3回リトライ後に例外を送出してプロセス終了 |

---

## 6. 環境変数

| 変数名 | デフォルト | 説明 |
|---|---|---|
| `GITHUB_TOKEN` | （未設定） | GitHub API トークン（レート制限緩和用・任意） |
| `QDRANT_HOST` | `qdrant` | Qdrant ホスト名 |
| `QDRANT_PORT` | `6333` | Qdrant ポート |
| `EMBED_BATCH_SIZE` | `32` | Embedding のバッチサイズ |
| `UPSERT_BATCH_SIZE` | `100` | Qdrant upsert のバッチサイズ |
| `EMBED_MODEL` | `intfloat/multilingual-e5-large` | メイン Embedding モデル |
| `FALLBACK_OLLAMA_URL` | `http://ollama:11434` | Ollama の URL（フォールバック用） |

---

## 7. 実行コマンド

```bash
# 通常実行（全ソース）
docker compose run --rm ingest

# Makefile ショートカット
make ingest
```
