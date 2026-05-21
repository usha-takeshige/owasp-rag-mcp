import os
import subprocess
import time
from pathlib import Path

import httpx
import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
RAG_API_URL = os.environ.get("RAG_API_URL", "http://localhost:8000")
STARTUP_TIMEOUT = int(os.environ.get("INTEGRATION_STARTUP_TIMEOUT", "180"))
SKIP_DOCKER = os.environ.get("INTEGRATION_NO_DOCKER", "").lower() in ("1", "true", "yes")


def _wait_for_rag_api(timeout: int = STARTUP_TIMEOUT) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = httpx.get(f"{RAG_API_URL}/health", timeout=5)
            data = resp.json()
            if resp.status_code == 200 and data.get("status") == "ok":
                return
        except Exception:
            pass
        time.sleep(3)
    raise TimeoutError(f"RAG API did not become healthy within {timeout}s")


@pytest.fixture(scope="session", autouse=True)
def docker_services():
    if SKIP_DOCKER:
        _wait_for_rag_api()
        yield
        return

    compose_cmd = [
        "docker", "compose",
        "-f", "docker-compose.yml",
        "-f", "docker-compose.test.yml",
    ]

    subprocess.run(
        [*compose_cmd, "up", "-d", "qdrant", "rag-api"],
        cwd=PROJECT_ROOT,
        check=True,
    )

    try:
        _wait_for_rag_api()
        yield
    finally:
        subprocess.run(
            [*compose_cmd, "down"],
            cwd=PROJECT_ROOT,
            check=False,
        )


@pytest.fixture(scope="session")
def ingest_data(docker_services):  # noqa: ARG001
    if SKIP_DOCKER:
        return

    subprocess.run(
        [
            "docker", "compose",
            "-f", "docker-compose.yml",
            "-f", "docker-compose.test.yml",
            "run", "--rm", "ingest",
        ],
        cwd=PROJECT_ROOT,
        check=True,
        timeout=600,
    )


@pytest.fixture(scope="session")
def rag_client(docker_services):  # noqa: ARG001
    with httpx.Client(base_url=RAG_API_URL, timeout=30) as client:
        yield client
