import httpx

from src.schemas import RAG_API_TIMEOUT, RAG_API_URL


class RagApiError(Exception):
    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class RagClient:
    def __init__(self, base_url: str = RAG_API_URL, timeout: int = RAG_API_TIMEOUT) -> None:
        self._base_url = base_url
        self._timeout = timeout

    def _handle_error(self, resp: httpx.Response) -> None:
        if resp.status_code in (400, 404):
            detail = resp.json().get("detail", resp.text)
            raise RagApiError(-32602, f"Invalid params: {detail}")
        if resp.status_code >= 500:
            raise RagApiError(-32603, f"Internal error: {resp.text}")

    def search(
        self,
        query: str,
        standard: str | None,
        level: int | None,
        top_k: int,
    ) -> dict:
        try:
            body: dict = {"query": query, "top_k": top_k}
            if standard is not None:
                body["standard"] = standard
            if level is not None:
                body["level"] = level
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(f"{self._base_url}/search", json=body)
            self._handle_error(resp)
            resp.raise_for_status()
            return resp.json()
        except RagApiError:
            raise
        except Exception as e:
            raise RagApiError(-32603, f"RAG API unavailable: {e}") from e

    def get_requirement(self, standard: str, req_id: str) -> dict:
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(f"{self._base_url}/requirement/{standard}/{req_id}")
            self._handle_error(resp)
            resp.raise_for_status()
            return resp.json()
        except RagApiError:
            raise
        except Exception as e:
            raise RagApiError(-32603, f"RAG API unavailable: {e}") from e

    def get_categories(self, standard: str | None) -> dict:
        try:
            params: dict = {}
            if standard is not None:
                params["standard"] = standard
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(f"{self._base_url}/categories", params=params)
            self._handle_error(resp)
            resp.raise_for_status()
            return resp.json()
        except RagApiError:
            raise
        except Exception as e:
            raise RagApiError(-32603, f"RAG API unavailable: {e}") from e
