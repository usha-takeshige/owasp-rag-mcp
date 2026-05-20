# owasp-rag-mcp 要件定義

## 1. プロジェクト概要

OWASP ASVS および AISVS をソフトウェアの仕様作成段階・開発途中に参照しやすくするための、ローカル完結型 RAG システムと MCP サーバーを構築する。

### 対象標準文書

| 標準 | 正式名称 | バージョン | 用途 |
|---|---|---|---|
| ASVS | OWASP Application Security Verification Standard | 5.0-RC1 | Web アプリケーションのセキュリティ要件 |
| AISVS | OWASP Artificial Intelligence Security Verification Standard | 1.0 | AI システムのセキュリティ要件 |

---

## 2. システム構成

### 全体アーキテクチャ

```
LLM クライアント（Claude / Cursor / ChatGPT など）
        │
        │  MCP protocol（HTTP/SSE transport）
        ▼
┌─────────────────────────────────────────────────┐
│               Docker（ローカル）                  │
│                                                  │
│  ┌─────────────┐      ┌──────────────────────┐  │
│  │ MCP Server  │─────▶│      RAG API         │  │
│  │  :8080      │      │  FastAPI  :8000       │  │
│  └─────────────┘      │  ┌────────────────┐  │  │
│                        │  │ Embedding モデル│  │  │
│                        │  │ multilingual-  │  │  │
│                        │  │ e5-large       │  │  │
│                        │  └────────────────┘  │  │
│                        │  ┌────────────────┐  │  │
│                        │  │   Qdrant       │  │  │
│                        │  │  Vector DB     │  │  │
│                        │  │  :6333         │  │  │
│                        │  └────────────────┘  │  │
│                        └──────────────────────┘  │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │  Ingest Pipeline（初回・更新時バッチ実行）  │   │
│  │  GitHub → parse → chunk → embed → Qdrant │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### Docker サービス構成

| サービス名 | 役割 | 外部公開ポート |
|---|---|---|
| `mcp-server` | MCP プロトコルサーバー | 8080 |
| `rag-api` | セマンティック検索 API | 内部のみ（8000） |
| `qdrant` | ベクトルデータベース | 内部のみ（6333） |
| `ingest` | ドキュメント取り込みバッチ | なし（起動後停止） |

外部に公開するのは `mcp-server`（ポート 8080）のみ。その他は Docker 内部ネットワークに閉じる。

---

## 3. 機能要件

### 3-1. MCP ツール仕様

#### `search_requirements`（主力ツール）

自然言語クエリで関連する要件を検索し、上位 k 件を返す。

```json
// リクエスト
{
  "query": "セッション管理の要件",
  "standard": "ASVS",      // 省略可（両標準を横断検索）
  "level": 1,              // 省略可（1 / 2 / 3）
  "top_k": 5               // 省略可（デフォルト 5）
}

// レスポンス
{
  "query": "セッション管理の要件",
  "results": [
    {
      "id": "ASVS-3.2.1",
      "standard": "ASVS",
      "version": "5.0",
      "level": 1,
      "category": "Session Management",
      "title": "Verify that the application generates a new session token on user authentication.",
      "description": "...",
      "score": 0.91
    }
  ],
  "total": 5
}
```

#### `get_requirement`（詳細参照）

要件 ID を指定して詳細を直接取得する。

```json
// リクエスト
{ "id": "ASVS-3.2.1" }
```

#### `list_categories`（ナビゲーション）

標準名を指定してカテゴリ・章一覧を返す。

```json
// リクエスト
{ "standard": "ASVS" }
```

#### `check_coverage`（仕様レビュー向け・上位機能）

機能説明テキストを渡すと、関連する要件群を返す。仕様書作成時のチェックリスト生成などに利用する。

```json
// リクエスト
{ "feature_description": "ユーザーがパスワードでログインする機能" }
```

### 3-2. 検索仕様

- **日本語クエリ → 英語ドキュメント検索**に対応する
- Embedding モデルとして `multilingual-e5-large` を採用し、日英を同一ベクトル空間にマッピングすることでクロスリンガル検索を実現する
- メタデータフィルタリング（`standard` / `level` / `category`）をサポートする

### 3-3. 検索結果の返却方針

- MCP ツールは**構造化 JSON で要件の生テキストをそのまま返す**
- 結果の整形・要約はクライアント側（LLM のシステムプロンプト）で行う
- これにより、Claude / Cursor / ChatGPT など異なるクライアントそれぞれのプロンプト設計に対応できる

---

## 4. 非機能要件

### 4-1. クライアント非依存

- MCP transport は **HTTP/SSE（Streamable HTTP）** を採用する
- stdio transport は使用しない（特定クライアントへの依存を避けるため）
- Claude Desktop、Cursor、ChatGPT（MCP 対応クライアント）、独自アプリから接続可能

### 4-2. ローカル完結

- すべてのコンポーネントをローカル Docker で稼働させる
- 外部 API（OpenAI Embeddings など）は使用しない
- ドキュメントの取得元は OWASP の公開 GitHub リポジトリのみ

### 4-3. 拡張性

- `ingest/data/sources.yml` でドキュメントソースを管理し、将来的な標準追加（MASVS、WSTG など）に対応できる構造にする

---

## 5. 技術スタック

| 層 | 採用技術 | 備考 |
|---|---|---|
| MCP サーバー | Python + MCP SDK | HTTP/SSE transport |
| RAG API | Python + FastAPI + uvicorn | 内部サービス |
| Embedding モデル | `intfloat/multilingual-e5-large` | ローカル実行 |
| Embedding フォールバック | `nomic-embed-text`（Ollama 経由） | 英語特化・高速 |
| Vector DB | Qdrant | Docker 公式イメージ |
| Ingest | Python スクリプト | バッチ実行 |
| パッケージ管理 | uv | 各サービスで独立管理 |
| コンテナ管理 | Docker Compose | |
| ソース管理 | GitHub（private リポジトリ） | `usha-takeshige/owasp-rag-mcp` |

---

## 6. リポジトリ構成

```
owasp-rag-mcp/
├── docker-compose.yml
├── docker-compose.override.yml     # 開発用（ホットリロードなど）
├── .env.example                    # 環境変数テンプレート（コミット対象）
├── .env                            # 実値（gitignore 必須）
├── .gitignore
├── README.md
├── Makefile                        # よく使うコマンドのショートカット
│
├── mcp-server/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── uv.lock
│   └── src/
│       ├── server.py               # エントリポイント
│       ├── tools.py                # ツール定義
│       ├── rag_client.py           # RAG API クライアント
│       └── schemas.py              # Pydantic モデル
│
├── rag-api/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── uv.lock
│   └── src/
│       ├── main.py                 # FastAPI アプリ
│       ├── search.py               # セマンティック検索
│       ├── embedder.py             # Embedding ラッパー
│       ├── qdrant_client.py        # Qdrant 接続
│       └── schemas.py
│
├── ingest/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── src/
│       ├── main.py                 # エントリポイント
│       ├── fetcher.py              # GitHub から Markdown 取得
│       ├── parser.py               # ASVS / AISVS 構造パース
│       ├── chunker.py              # 要件単位チャンキング
│       ├── embedder.py
│       └── upserter.py             # Qdrant へ投入
│   └── data/
│       └── sources.yml             # 取得元 URL・バージョン定義（コミット対象）
│
├── shared/                         # 全サービス共通（任意）
│   ├── models.py
│   └── constants.py
│
├── .github/
│   └── workflows/
│       ├── ci.yml                  # lint + test（push / PR 時）
│       └── ingest.yml              # 標準更新時の手動トリガー
│
└── docs/
    ├── architecture.md
    ├── mcp-tools.md                # ツール API 仕様・使用例
    └── client-setup.md             # 各クライアントからの接続設定
```

### gitignore 対象

| パス | 理由 |
|---|---|
| `.env` | シークレット漏洩防止 |
| `qdrant_storage/` | バイナリ・大容量 |
| `ingest/data/raw/` | 生成物・大容量 |
| `models/` `.cache/huggingface/` | 数 GB・再取得可能 |
| `__pycache__/` `.venv/` | Python 生成物 |

---

## 7. 環境変数（`.env.example`）

```dotenv
# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION_ASVS=asvs_requirements
QDRANT_COLLECTION_AISVS=aisvs_requirements

# RAG API
RAG_API_URL=http://rag-api:8000
EMBEDDING_MODEL=intfloat/multilingual-e5-large

# MCP Server
MCP_PORT=8080

# Ingest
GITHUB_TOKEN=           # レートリミット回避用（任意）
INGEST_SOURCES_FILE=./data/sources.yml
```

---

## 8. ドキュメントソース定義（`ingest/data/sources.yml`）

```yaml
sources:
  - standard: ASVS
    version: "5.0-rc1"
    repo: OWASP/ASVS
    branch: v5.0.be
    paths:
      - 5.0/en/
  - standard: AISVS
    version: "1.0"
    repo: OWASP/AISVS
    branch: main
    paths:
      - 1.0/en/
```

---

## 9. 実装フェーズ（想定順序）

1. **Docker Compose 骨格** — 全サービスが起動する構成ファイルとディレクトリ構造
2. **Ingest Pipeline** — ドキュメント取得・パース・チャンキング・Qdrant 投入
3. **RAG API** — セマンティック検索エンドポイント（FastAPI）
4. **MCP Server** — ツール定義・HTTP/SSE transport
5. **結合テスト** — 各クライアントからの接続確認
6. **CI 設定** — GitHub Actions（lint / test / 手動 ingest）
