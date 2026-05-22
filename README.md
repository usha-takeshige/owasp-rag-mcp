# owasp-rag-mcp

OWASP ASVS（Application Security Verification Standard v5.0-RC1）および AISVS（Artificial Intelligence Security Verification Standard v1.0）を、仕様作成・開発時に手軽に参照できる**ローカル完結型 RAG システムと MCP サーバー**です。

- Claude Desktop / Cursor / VS Code などの LLM クライアントから MCP ツールとして呼び出せます
- 日本語クエリで英語ドキュメントを横断検索できます（クロスリンガル検索）
- すべてのコンポーネントをローカル Docker で完結し、外部 API に依存しません

## 必要環境

- Docker / Docker Compose
- uv（テスト・Lint を手元で実行する場合）

## セットアップ

```bash
# 1. 環境変数ファイルを作成
cp .env.example .env

# 2. ドキュメントを Qdrant へ取り込む（初回のみ）
#    multilingual-e5-large（約 2.2 GB）を初回ダウンロードするため時間がかかります
make ingest

# 3. サービスを起動
make up
```

`make up` 後、`http://localhost:8080` で MCP サーバーが利用可能になります。
port番号は`.env`で設定したものにしてください。

## 使い方

### LLM クライアントへの接続

#### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json`（Windows は `%APPDATA%\Claude\claude_desktop_config.json`）に以下を追加してください：

```json
{
  "mcpServers": {
    "owasp-rag": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://localhost:8080/mcp"
      ]
    }
  }
}
```

Claude Desktop を再起動すると、チャット画面のツールメニューに `owasp-rag` が表示されます。

#### Cursor

プロジェクトルートの `.cursor/mcp.json`、またはグローバル設定 `~/.cursor/mcp.json` に追加します：

```json
{
  "mcpServers": {
    "owasp-rag": {
      "type": "http",
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

### クエリ例

```
# セマンティック検索
ASVS の入力バリデーションに関する Level 1 の要件を検索して

# 要件 ID 直接参照
ASVS の V2.1.1 の要件を教えて

# カテゴリ一覧
AISVS にはどんな章があるか教えて

# カバレッジ確認
JWT を使ったユーザー認証機能を実装する場合、ASVS のどの要件を満たす必要があるか確認して
```

## MCP ツール一覧

| ツール名 | 概要 |
|---|---|
| `search_requirements` | 自然言語クエリで関連要件をセマンティック検索（日本語可） |
| `get_requirement` | 要件 ID を指定して詳細を取得 |
| `list_categories` | 標準のカテゴリ・章一覧を返す |
| `check_coverage` | 機能説明から関連要件群を返す（仕様レビュー向け） |

詳細は [docs/mcp-tools.md](docs/mcp-tools.md) を参照してください。

## よく使うコマンド

```bash
make up              # サービス起動
make down            # サービス停止
make ingest          # ドキュメント再取り込み
make logs            # ログ表示
make test            # ユニットテスト実行
make test-integration # 結合テスト実行
make lint            # Lint 実行
```

## トラブルシューティング

**ツールが認識されない**

```bash
docker compose ps                    # コンテナの起動状態を確認
curl http://localhost:8080/health    # MCP サーバーへの疎通確認
```

**検索結果が返ってこない**

```bash
docker compose logs rag-api          # Embedding モデルのロード状態を確認
make ingest                          # Qdrant へのデータ投入を再実行
```

**Embedding モデルのロードが遅い**

`multilingual-e5-large`（約 2.2 GB）は初回起動時にコンテナ内の `/root/.cache/huggingface/hub/` へダウンロードされます。モデルキャッシュ用のボリュームは定義されていないため、コンテナを削除すると再ダウンロードが必要になります（`docker compose down` のみであれば残ります）。

## ドキュメント

- [アーキテクチャ](docs/architecture.md)
- [MCP ツール仕様](docs/mcp-tools.md)
- [クライアント設定ガイド](docs/client-setup.md)
- [Ingest パイプライン](docs/ingest-pipeline.md)
- [RAG API 仕様](docs/rag-api.md)
