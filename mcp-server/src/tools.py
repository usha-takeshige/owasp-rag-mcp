from mcp.shared.exceptions import McpError
from mcp.types import ErrorData

from src.rag_client import RagApiError, RagClient
from src.schemas import COVERAGE_TOP_K_MAX, SEARCH_TOP_K_MAX, VALID_LEVELS, VALID_STANDARDS

_client = RagClient()


def _validate_standard(standard: str | None) -> None:
    if standard is not None and standard not in VALID_STANDARDS:
        raise McpError(ErrorData(code=-32602, message=f"Invalid standard: {standard}"))


def _validate_level(level: int | None) -> None:
    if level is not None and level not in VALID_LEVELS:
        raise McpError(ErrorData(code=-32602, message=f"Invalid level: {level}"))


def _convert_rag_error(e: RagApiError) -> McpError:
    return McpError(ErrorData(code=e.code, message=e.message))


async def search_requirements(
    query: str,
    standard: str | None = None,
    level: int | None = None,
    top_k: int = 5,
) -> dict:
    _validate_standard(standard)
    _validate_level(level)
    if not (1 <= top_k <= SEARCH_TOP_K_MAX):
        raise McpError(
            ErrorData(code=-32602, message=f"top_k must be between 1 and {SEARCH_TOP_K_MAX}")
        )
    try:
        return _client.search(query, standard, level, top_k)
    except RagApiError as e:
        raise _convert_rag_error(e) from e


async def get_requirement(req_id: str, standard: str) -> dict:
    _validate_standard(standard)
    try:
        return _client.get_requirement(standard, req_id)
    except RagApiError as e:
        raise _convert_rag_error(e) from e


async def list_categories(standard: str | None = None) -> dict:
    _validate_standard(standard)
    try:
        return _client.get_categories(standard)
    except RagApiError as e:
        raise _convert_rag_error(e) from e


async def check_coverage(
    feature: str,
    standard: str | None = None,
    top_k: int = 10,
) -> dict:
    _validate_standard(standard)
    if not (1 <= top_k <= COVERAGE_TOP_K_MAX):
        raise McpError(
            ErrorData(code=-32602, message=f"top_k must be between 1 and {COVERAGE_TOP_K_MAX}")
        )
    try:
        result = _client.search(feature, standard, None, top_k)
        result["feature"] = result.pop("query")
        return result
    except RagApiError as e:
        raise _convert_rag_error(e) from e
