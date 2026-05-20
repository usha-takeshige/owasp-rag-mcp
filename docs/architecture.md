# アーキテクチャ設計書

## 1. システム概要

本システムは、OWASP ASVS および AISVS の要件を LLM クライアントから自然言語で検索できるようにするための、ローカル完結型 RAG システムと MCP サーバーで構成される。

外部 API に依存せず、すべてのコンポーネントを Docker 上でローカル動作させる。

---

## 2. 全体アーキテクチャ

```
┌────────────────────────────────────────────────────────┐
│              LLM クライアント                            │
│  （Claude Desktop / Cursor / ChatGPT など）             │
└───────────────────────┬────────────────────────────────┘
                        │ MCP protocol
                        │ HTTP/SSE（Streamable HTTP）
                        │ port 8080
┌───────────────────────▼────────────────────────────────┐
│                   Docker ネットワーク                    │
│                                                        │
│  ┌─────────────────┐       ┌────────────────────────┐  │
│  │   mcp-server    │──────▶│       rag-api          │  │
│  │   :8080         │ HTTP  │       :8000            │  │
│  │                 │       │                        │  │
│  │  MCP ツール定義  │       │  ┌──────────────────┐  │  │
│  │  ・search       │       │  │ multilingual-    │  │  │
│  │  ・get          │       │  │ e5-large         │  │  │
│  │  ・list         │       │  │ (Embedding)      │  │  │
│  │  ・check        │       │  └──────────────────┘  │  │
│  └─────────────────┘       │                        │  │
│                            │  ┌──────────────────┐  │  │
│                            │  │     qdrant       │  │  │
│  ┌─────────────────┐       │  │     :6333        │  │  │
│  │     ingest      │──────▶│  │  (Vector DB)     │  │  │
│  │  （バッチ実行）  │       │  └──────────────────┘  │  │
│  │                 │       └────────────────────────┘  │
│  │  GitHub         │                                   │
│  │  → parse        │                                   │
│  │  → chunk        │                                   │
│  │  → embed        │                                   │
│  │  → upsert       │                                   │
│  └─────────────────┘                                   │
└────────────────────────────────────────────────────────┘
```

---

## 3. サービス構成

| サービス名 | 役割 | ポート | 外部公開 |
|---|---|---|---|
| `mcp-server` | MCP プロトコルサーバー | 8080 | ✅ |
| `rag-api` | セマンティック検索 API | 8000 | ❌（内部のみ） |
| `qdrant` | ベクトルデータベース | 6333 | ❌（内部のみ） |
| `ingest` | ドキュメント取り込みバッチ | — | ❌（起動後停止） |

外部に公開するのは `mcp-server`（ポート 8080）のみ。その他は Docker 内部ネットワークに閉じる。

### 3-1. mcp-server

LLM クライアントからの MCP リクエストを受け付け、`rag-api` に転送するゲートウェイ。

- **transport**: HTTP/SSE（Streamable HTTP）
- **依存先**: `rag-api`
- **主要ファイル**: `mcp-server/src/server.py`、`tools.py`、`rag_client.py`

### 3-2. rag-api

セマンティック検索を担う内部 API サービス。クエリをベクトル化し、Qdrant を検索して結果を返す。

- **フレームワーク**: FastAPI + uvicorn
- **Embedding モデル**: `intfloat/multilingual-e5-large`（ローカル実行）
- **フォールバック**: `nomic-embed-text`（Ollama 経由）
- **依存先**: `qdrant`
- **主要ファイル**: `rag-api/src/main.py`、`search.py`、`embedder.py`

### 3-3. qdrant

ベクトルデータベース。要件ドキュメントの Embedding とメタデータを保持する。

- **コレクション**: `asvs_requirements`、`aisvs_requirements`
- **イメージ**: Docker 公式イメージ（`qdrant/qdrant`）
- **永続化**: `qdrant_storage/`（gitignore 対象）

### 3-4. ingest

初回セットアップ時および標準文書の更新時に実行するバッチサービス。起動後にパイプラインを実行し、完了後に停止する。

- **処理**: GitHub から Markdown 取得 → パース → チャンキング → Embedding → Qdrant 投入
- **設定ファイル**: `ingest/data/sources.yml`
- **主要ファイル**: `ingest/src/main.py`、`fetcher.py`、`parser.py`、`chunker.py`、`embedder.py`、`upserter.py`

---

## 4. データフロー

### 4-1. 検索フロー（通常利用時）

```
LLM クライアント
    │
    │ ① MCP ツール呼び出し（例: search_requirements）
    │   クエリ例: "セッション管理の要件"
    ▼
mcp-server
    │
    │ ② HTTP POST /search
    │   { query, standard?, level?, top_k? }
    ▼
rag-api
    │
    │ ③ クエリを Embedding（multilingual-e5-large）
    │   日本語クエリ → ベクトル（1024 次元）
    │
    │ ④ Qdrant へベクトル検索
    │   メタデータフィルタ（standard / level / category）を適用
    ▼
qdrant
    │
    │ ⑤ 類似度スコア上位 k 件を返却
    ▼
rag-api
    │
    │ ⑥ 検索結果を JSON に整形して返却
    ▼
mcp-server
    │
    │ ⑦ MCP レスポンスとして返却
    │   構造化 JSON（生テキストのまま）
    ▼
LLM クライアント
    │
    └─ ⑧ クライアント側（LLM のシステムプロンプト）で整形・要約
```

### 4-2. Ingest フロー（初回・更新時）

ASVS と AISVS でソースのフォーマットが異なるため、fetcher と parser の処理が分岐する。

```
ingest/data/sources.yml
    │
    │ ① ソース定義の読み込み
    │   { standard, version, repo, branch, format, path }
    ▼
fetcher
    │
    │ ② GitHub API からソースファイルを取得
    │
    ├─ ASVS の場合  ─────────────────────────────────────────┐
    │   フォーマット: JSON（flat）                            │
    │   取得先: OWASP/ASVS master                           │
    │   ファイル: 5.0/docs_en/                              │
    │     OWASP_Application_Security_Verification_Standard  │
    │     _5.0.0_en.flat.json                               │
    │   ※ 要件単位にフラット展開済みの公式ビルド成果物           │
    │                                                       │
    └─ AISVS の場合 ─────────────────────────────────────────┤
        フォーマット: Markdown                               │
        取得先: OWASP/AISVS main                           │
        ファイル: 1.0/en/*.md （章ごとのファイル）            │
        ※ JSON 形式が存在しないため Markdown をパース          │
                                                           │
    ◀──────────────────────────────────────────────────────┘
    ▼
parser
    │
    │ ③ 要件単位のレコードに正規化
    │
    ├─ ASVS: flat.json をそのまま読み込み
    │   req_id / level / chapter_id / section_id / description フィールドを抽出
    │
    └─ AISVS: Markdown をパース
        章・セクション・要件 ID・レベルを抽出して構造化
    │
    ▼
chunker
    │
    │ ④ 要件 1 件 = 1 チャンク に分割
    │   メタデータ（req_id / standard / level / chapter_id / section_id）を付与
    ▼
embedder
    │
    │ ⑤ 各チャンクを Embedding（multilingual-e5-large）
    │   バッチ処理でベクトル化
    ▼
upserter
    │
    │ ⑥ Qdrant へ投入（upsert）
    │   既存データは更新、冪等性を担保
    ▼
qdrant
    └─ ⑦ コレクションにベクトル＋メタデータを保存
```

---

## 5. ネットワーク構成

```
┌─────────────────────────────────────────────────┐
│               ホストマシン（ローカル）              │
│                                                 │
│  ポート 8080 ─────────────────────────────────┐  │
│                                               │  │
│  ┌────────────────────────────────────────┐   │  │
│  │          Docker ネットワーク            │   │  │
│  │                                        │   │  │
│  │  mcp-server:8080  ◀──────── 外部 ─────┘  │  │
│  │       │                                  │  │
│  │       │ 内部通信                          │  │
│  │       ▼                                  │  │
│  │  rag-api:8000                            │  │
│  │       │                                  │  │
│  │       │ 内部通信                          │  │
│  │       ▼                                  │  │
│  │  qdrant:6333                             │  │
│  │                                          │  │
│  │  ingest ──────────────────▶ qdrant      │  │
│  │  （バッチ実行・完了後停止）                │  │
│  └────────────────────────────────────────┘   │  │
└─────────────────────────────────────────────────┘
```

- `mcp-server` のみホストマシンのポート 8080 にバインドし外部（LLM クライアント）からアクセス可能
- `rag-api`、`qdrant` は Docker 内部ネットワークのみで通信
- `ingest` は `qdrant` に直接接続してデータ投入後、コンテナが停止

---

## 6. Embedding モデル

| モデル | 用途 | 次元数 | 備考 |
|---|---|---|---|
| `intfloat/multilingual-e5-large` | メイン | 1024 | 日英クロスリンガル対応、ローカル実行 |
| `nomic-embed-text`（Ollama 経由） | フォールバック | 768 | 英語特化・高速 |

`multilingual-e5-large` を使用することで、日本語クエリと英語ドキュメントを同一ベクトル空間にマッピングし、クロスリンガル検索を実現する。

---

## 7. クロスリンガル検索の仕組み

```
日本語クエリ         英語ドキュメント（Qdrant に保存済み）
"セッション管理"  →  "Session Management"
      │                        │
      ▼                        ▼
 [0.12, -0.34, ...]      [0.11, -0.36, ...]
      │                        │
      └────── cos 類似度 ───────┘
                  ↓
              高スコア（マッチ）
```

multilingual-e5-large は多言語テキストを言語に依存しないベクトル空間に変換するため、日本語クエリでも英語ドキュメントを精度よく検索できる。

---

## 8. 拡張性

ドキュメントソースは `ingest/data/sources.yml` で管理する。将来的に MASVS・WSTG などの標準を追加する場合は、このファイルにエントリを追加するだけでよい。

```yaml
sources:
  - standard: ASVS
    version: "5.0.0"
    repo: OWASP/ASVS
    branch: master
    format: json_flat          # 公式ビルド済み flat JSON を使用
    path: 5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.flat.json
  - standard: AISVS
    version: "1.0"
    repo: OWASP/AISVS
    branch: main
    format: markdown           # JSON が存在しないため Markdown をパース
    paths:
      - 1.0/en/
    path_pattern: "0x10-C*.md"
  # 将来追加例
  # - standard: MASVS
  #   version: "2.0"
  #   repo: OWASP/owasp-masvs
  #   branch: main
  #   format: markdown
  #   paths:
  #     - Document/
```
