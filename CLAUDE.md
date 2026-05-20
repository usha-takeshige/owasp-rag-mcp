# CLAUDE.md — owasp-rag-mcp

## プロジェクト目標

OWASP ASVS（Application Security Verification Standard v5.0-RC1）および AISVS（Artificial Intelligence Security Verification Standard v1.0）を、仕様作成・開発時に手軽に参照できるようにするための**ローカル完結型 RAG システムと MCP サーバー**を構築する。

- LLM クライアント（Claude / Cursor / ChatGPT など）から MCP ツールとして呼び出せる
- 日本語クエリで英語ドキュメントを横断検索できる（クロスリンガル検索）
- すべてのコンポーネントをローカル Docker で完結させ、外部 API に依存しない

---

## ディレクトリ構成

```
owasp-rag-mcp/
├── docker-compose.yml
├── docker-compose.override.yml     # 開発用（ホットリロードなど）
├── .env.example                    # 環境変数テンプレート（コミット対象）
├── .env                            # 実値（gitignore 必須）
├── .gitignore
├── README.md
├── CLAUDE.md
├── Makefile
│
├── mcp-server/                     # MCP プロトコルサーバー（:8080 外部公開）
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── uv.lock
│   └── src/
│       ├── server.py               # エントリポイント
│       ├── tools.py                # MCP ツール定義
│       ├── rag_client.py           # RAG API クライアント
│       └── schemas.py
│
├── rag-api/                        # セマンティック検索 API（内部 :8000）
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── uv.lock
│   └── src/
│       ├── main.py
│       ├── search.py
│       ├── embedder.py
│       ├── qdrant_client.py
│       └── schemas.py
│
├── ingest/                         # ドキュメント取り込みバッチ（起動後停止）
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── src/
│       ├── main.py
│       ├── fetcher.py              # GitHub から Markdown 取得
│       ├── parser.py               # ASVS / AISVS 構造パース
│       ├── chunker.py
│       ├── embedder.py
│       └── upserter.py             # Qdrant へ投入
│   └── data/
│       └── sources.yml             # 取得元 URL・バージョン定義
│
├── .github/
│   └── workflows/
│       ├── ci.yml                  # lint + test（push / PR 時）
│       └── ingest.yml              # 標準更新時の手動トリガー
│
└── docs/
    ├── requirements/
    │   └── requirements.md
    ├── architecture.md
    ├── mcp-tools.md
    └── client-setup.md
```

---

## 技術スタック

| 層 | 採用技術 | 備考 |
|---|---|---|
| MCP サーバー | Python + MCP SDK | HTTP/SSE（Streamable HTTP）transport |
| RAG API | Python + FastAPI + uvicorn | 内部サービス |
| Embedding モデル | `intfloat/multilingual-e5-large` | ローカル実行・日英クロスリンガル |
| Embedding フォールバック | `nomic-embed-text`（Ollama 経由） | 英語特化・高速 |
| Vector DB | Qdrant | Docker 公式イメージ |
| Ingest | Python スクリプト | バッチ実行 |
| パッケージ管理 | uv | 各サービスで独立管理 |
| コンテナ管理 | Docker Compose | |

### Docker サービス構成

| サービス名 | 役割 | 外部公開ポート |
|---|---|---|
| `mcp-server` | MCP プロトコルサーバー | **8080**（外部公開） |
| `rag-api` | セマンティック検索 API | 内部のみ（8000） |
| `qdrant` | ベクトルデータベース | 内部のみ（6333） |
| `ingest` | ドキュメント取り込みバッチ | なし（起動後停止） |

---

## 起動コマンド

> **前提**: Docker / Docker Compose と uv がインストールされていること。`.env` が `.env.example` をもとに作成済みであること。

### 初回セットアップ

```bash
# 環境変数ファイルを作成
cp .env.example .env

# ドキュメントの取り込み（Qdrant へのインデックス構築）
docker compose run --rm ingest
```

### 通常起動

```bash
# すべてのサービスを起動
docker compose up -d

# ログ確認
docker compose logs -f

# 停止
docker compose down
```

### 開発時（ホットリロード）

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml up
```

### Makefile ショートカット（実装後）

```bash
make up       # docker compose up -d
make down     # docker compose down
make ingest   # ドキュメント再取り込み
make logs     # ログ表示
make test     # テスト実行
make lint     # lint 実行
```

---

## MCP ツール一覧

| ツール名 | 概要 |
|---|---|
| `search_requirements` | 自然言語クエリで関連要件を検索（主力） |
| `get_requirement` | 要件 ID を指定して詳細を取得 |
| `list_categories` | 標準のカテゴリ・章一覧を返す |
| `check_coverage` | 機能説明から関連要件群を返す（仕様レビュー向け） |

---

## 実装フェーズ

1. Docker Compose 骨格
2. Ingest Pipeline（ドキュメント取得・パース・チャンキング・Qdrant 投入）
3. RAG API（FastAPI）
4. MCP Server（HTTP/SSE transport）
5. 結合テスト
6. CI 設定（GitHub Actions）

## バージョン管理
git/githubを使用する

プルリクエスト作成時には以下のファイルテンプレートとする
@.github/PRTEMPLATE.md
