# クライアント設定ガイド

## 1. 概要

本ドキュメントでは、LLM クライアント（Claude Desktop / Cursor / VS Code）から MCP サーバーに接続するための設定手順を説明する。

**前提**: `docker compose up -d` でサービスが起動済みであること。

---

## 2. 接続情報

| 項目 | 値 |
|---|---|
| MCP エンドポイント | `http://localhost:8080` |
| トランスポート | HTTP/SSE（Streamable HTTP） |
| 認証 | なし（ローカル接続のみ想定） |

---

## 3. Claude Desktop

### 設定ファイルの場所

| OS | パス |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

### 設定内容

```json
{
  "mcpServers": {
    "owasp-rag": {
      "type": "http",
      "url": "http://localhost:8080"
    }
  }
}
```

### 確認方法

1. Claude Desktop を再起動する
2. チャット画面の入力欄に `🔨` アイコン（ツールメニュー）が表示されることを確認する
3. 以下のプロンプトで動作確認する：

```
ASVS のセッション管理に関する要件を教えてください。
```

---

## 4. Cursor

### 設定ファイルの場所

プロジェクトルートの `.cursor/mcp.json`、またはグローバル設定 `~/.cursor/mcp.json`。

### 設定内容

```json
{
  "mcpServers": {
    "owasp-rag": {
      "type": "http",
      "url": "http://localhost:8080"
    }
  }
}
```

### 確認方法

Cursor を再起動後、チャットで以下を入力する：

```
@owasp-rag セッション管理の要件を検索して
```

---

## 5. VS Code（GitHub Copilot / Continue）

### Continue 拡張機能

`~/.continue/config.json` に以下を追加する：

```json
{
  "experimental": {
    "modelContextProtocolServers": [
      {
        "transport": {
          "type": "http",
          "url": "http://localhost:8080"
        }
      }
    ]
  }
}
```

---

## 6. 動作確認クエリ例

接続後、以下のプロンプトでツールの動作を確認できる。

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

---

## 7. トラブルシューティング

### ツールが認識されない

- `docker compose ps` でコンテナが起動中か確認する
- `curl http://localhost:8080/health` でサーバーに疎通できるか確認する
- クライアントを再起動する

### 検索結果が返ってこない

- `docker compose logs rag-api` で Embedding モデルのロード状態を確認する
- `docker compose run --rm ingest` を実行して Qdrant にデータが投入されているか確認する

### Embedding モデルのロードに時間がかかる

`multilingual-e5-large`（約 2.2 GB）は初回起動時にダウンロードが発生する。モデルキャッシュは Docker ボリューム `model_cache` に永続化されるため、2 回目以降は高速に起動する。
