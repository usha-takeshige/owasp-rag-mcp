import base64
import fnmatch
import os
import time
from dataclasses import dataclass

import httpx

GITHUB_API = "https://api.github.com"


@dataclass
class FetchedSource:
    standard: str
    version: str
    format: str
    content: str
    filename: str


def _headers() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _get_file(client: httpx.Client, repo: str, path: str, branch: str) -> str:
    url = f"{GITHUB_API}/repos/{repo}/contents/{path}"
    for attempt in range(3):
        resp = client.get(url, params={"ref": branch}, headers=_headers())
        if resp.status_code == 200:
            data = resp.json()
            return base64.b64decode(data["content"]).decode("utf-8")
        if resp.status_code == 403 and "X-RateLimit-Reset" in resp.headers:
            wait = int(resp.headers["X-RateLimit-Reset"]) - int(time.time()) + 1
            time.sleep(max(wait, 1))
        elif attempt < 2:
            time.sleep(2 ** attempt)
        else:
            resp.raise_for_status()
    raise RuntimeError(f"Failed to fetch {path} after retries")


def _list_dir(client: httpx.Client, repo: str, path: str, branch: str) -> list[dict]:
    url = f"{GITHUB_API}/repos/{repo}/contents/{path}"
    resp = client.get(url, params={"ref": branch}, headers=_headers())
    resp.raise_for_status()
    return resp.json()  # type: ignore[no-any-return]


def fetch(source: dict) -> list[FetchedSource]:
    results: list[FetchedSource] = []
    with httpx.Client(timeout=30) as client:
        if source["format"] == "json_flat":
            content = _get_file(client, source["repo"], source["path"], source["branch"])
            results.append(FetchedSource(
                standard=source["standard"],
                version=source["version"],
                format=source["format"],
                content=content,
                filename=source["path"].split("/")[-1],
            ))
        elif source["format"] == "markdown":
            pattern = source.get("path_pattern", "*.md")
            for dir_path in source["paths"]:
                entries = _list_dir(
                    client, source["repo"], dir_path.rstrip("/"), source["branch"]
                )
                for entry in entries:
                    if entry["type"] == "file" and fnmatch.fnmatch(entry["name"], pattern):
                        content = _get_file(
                            client, source["repo"], entry["path"], source["branch"]
                        )
                        results.append(FetchedSource(
                            standard=source["standard"],
                            version=source["version"],
                            format=source["format"],
                            content=content,
                            filename=entry["name"],
                        ))
    return results
