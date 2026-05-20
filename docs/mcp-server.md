# MCP サーバー実装仕様書

## 1. 概要

`mcp-server` は、LLM クライアントからの MCP リクエストを受け付け、`rag-api` に転送するゲートウェイサービスである。

- **ライブラリ**: `mcp`（公式 Python SDK）
- **トランスポート**: Streamable HTTP（HTTP/SSE）
- **ポート**: `8080`（外部公開）
- **依存先**: `rag-api:8000`（内部ネットワーク）

---

## 2. ファイル構成

```
mcp-server/
├── Dockerfile
├── pyproject.toml
└── src/
    ├── server.py       # エントリポイント・サーバー起動
    ├── tools.py        # MCP ツールハンドラ実装
    ├── rag_client.py   # RAG API HTTP クライアント
    └── schemas.py      # ツール入力パラメータの Pydantic モデル
```

---

## 3. ツール → RAG API マッピング

| MCP ツール | RAG API | メソッド | パラメータ変換 |
|---|---|---|---|
| `search_requirements` | `/search` | `POST` | 直接マッピング |
| `get_requirement` | `/requirement/{standard}/{req_id}` | `GET` | 直接マッピング |
| `list_categories` | `/categories` | `GET` | 直接マッピング |
| `check_coverage` | `/search` | `POST` | `feature` → `query`、`top_k` デフォルト `10` |

### check_coverage の変換詳細

`check_coverage` は `search_requirements` と同じ `/search` エンドポイントを使用し、MCP サーバー層でパラメータを変換する。

```python
# check_coverage(feature, standard, top_k) → POST /search
{
    "query": feature,        # feature → query にリネーム
    "standard": standard,    # そのまま渡す（null で全標準）
    "level": None,           # check_coverage はレベルフィルタなし
    "top_k": top_k,          # デフォルト 10、最大 50
}
```

---

## 4. 各ファイルの責務と実装方針

### 4-1. server.py

MCP サーバーの初期化、ツール登録、Streamable HTTP transport の起動を行う。

```python
from mcp.server.fastmcp import FastMCP
from .tools import search_requirements, get_requirement, list_categories, check_coverage

mcp = FastMCP("owasp-rag")

# ツールを登録
mcp.tool()(search_requirements)
mcp.tool()(get_requirement)
mcp.tool()(list_categories)
mcp.tool()(check_coverage)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

### 4-2. tools.py

各ツールのハンドラ関数を定義する。入力バリデーションと `rag_client` の呼び出し、レスポンス整形を担う。

```python
from .rag_client import RagClient
from .schemas import SearchInput, GetRequirementInput, ListCategoriesInput, CheckCoverageInput

client = RagClient()

async def search_requirements(
    query: str,
    standard: str | None = None,
    level: int | None = None,
    top_k: int = 5,
) -> dict:
    return await client.search(query=query, standard=standard, level=level, top_k=top_k)

async def get_requirement(req_id: str, standard: str) -> dict:
    return await client.get_requirement(standard=standard, req_id=req_id)

async def list_categories(standard: str | None = None) -> dict:
    return await client.list_categories(standard=standard)

async def check_coverage(
    feature: str,
    standard: str | None = None,
    top_k: int = 10,
) -> dict:
    result = await client.search(query=feature, standard=standard, level=None, top_k=top_k)
    # レスポンスの "query" フィールドを "feature" に差し替える
    result["feature"] = result.pop("query")
    result.pop("total", None)
    result["total"] = len(result["results"])
    return result
```

### 4-3. rag_client.py

`rag-api` への HTTP リクエストを集約する。タイムアウト・エラーハンドリングはここで一元管理する。

```python
import httpx
from mcp.types import McpError, ErrorCode

class RagClient:
    def __init__(self):
        base_url = os.getenv("RAG_API_URL", "http://rag-api:8000")
        timeout = float(os.getenv("RAG_API_TIMEOUT", "30"))
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def search(self, query: str, standard: str | None, level: int | None, top_k: int) -> dict:
        response = await self._request("POST", "/search", json={
            "query": query,
            "standard": standard,
            "level": level,
            "top_k": top_k,
        })
        return response

    async def get_requirement(self, standard: str, req_id: str) -> dict:
        return await self._request("GET", f"/requirement/{standard}/{req_id}")

    async def list_categories(self, standard: str | None) -> dict:
        params = {"standard": standard} if standard else {}
        return await self._request("GET", "/categories", params=params)

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            response = await self._client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise _to_mcp_error(e) from e
        except httpx.RequestError as e:
            raise McpError(ErrorCode.INTERNAL_ERROR, f"RAG API unreachable: {e}") from e
```

#### HTTP ステータス → MCP エラーコード変換

| RAG API HTTP ステータス | MCP エラーコード | 意味 |
|---|---|---|
| `400 Bad Request` | `-32602` (Invalid params) | 不正なパラメータ |
| `404 Not Found` | `-32602` (Invalid params) | 要件 ID が存在しない |
| `503 Service Unavailable` | `-32603` (Internal error) | Qdrant 接続失敗 |
| その他 5xx | `-32603` (Internal error) | 内部エラー |

```python
def _to_mcp_error(e: httpx.HTTPStatusError) -> McpError:
    status = e.response.status_code
    detail = e.response.json().get("detail", str(e))
    if status in (400, 404):
        return McpError(ErrorCode.INVALID_PARAMS, detail)
    return McpError(ErrorCode.INTERNAL_ERROR, detail)
```

### 4-4. schemas.py

FastMCP はツール関数のシグネチャからスキーマを自動生成するため、`schemas.py` は補助的な定数定義にとどめる。

```python
VALID_STANDARDS = {"ASVS", "AISVS"}
VALID_LEVELS = {1, 2, 3}
TOP_K_MAX_SEARCH = 20
TOP_K_MAX_COVERAGE = 50
```

入力バリデーション（`standard` の有効値チェック、`level` の範囲チェック）は `tools.py` のハンドラ内で行い、不正値の場合は `McpError(ErrorCode.INVALID_PARAMS, ...)` を送出する。

---

## 5. 入力バリデーション

ツールハンドラ内で以下を検証する。RAG API に到達する前に弾く。

| パラメータ | バリデーション |
|---|---|
| `standard` | `ASVS` / `AISVS` のいずれか（それ以外は `-32602`） |
| `level` | `1` / `2` / `3` のいずれか（それ以外は `-32602`） |
| `top_k`（search） | `1` 〜 `20`（範囲外は `-32602`） |
| `top_k`（coverage） | `1` 〜 `50`（範囲外は `-32602`） |
| `req_id` | 空文字列不可（それ以外は RAG API に委譲） |

---

## 6. 環境変数

| 変数名 | デフォルト | 説明 |
|---|---|---|
| `RAG_API_URL` | `http://rag-api:8000` | RAG API のベース URL |
| `RAG_API_TIMEOUT` | `30` | RAG API へのリクエストタイムアウト（秒） |
| `MCP_PORT` | `8080` | リスニングポート |
| `LOG_LEVEL` | `info` | ログレベル（`debug` / `info` / `warning`） |

---

## 7. 依存パッケージ（pyproject.toml）

```toml
[project]
name = "mcp-server"
requires-python = ">=3.11"
dependencies = [
    "mcp[cli]",
    "httpx",
]
```

---

## 8. Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install uv && uv pip install --system -e .

COPY src/ ./src/

EXPOSE 8080
CMD ["python", "-m", "src.server"]
```
