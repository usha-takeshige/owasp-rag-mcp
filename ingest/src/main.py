import os

import yaml

from src.chunker import chunk
from src.embedder import Embedder
from src.fetcher import fetch
from src.parser import parse
from src.upserter import COLLECTION_MAP, ensure_collection, get_client, upsert

SOURCES_PATH = os.environ.get("SOURCES_PATH", "data/sources.yml")


def load_sources(path: str) -> list[dict]:
    with open(path) as f:
        return yaml.safe_load(f)["sources"]


def main() -> None:
    sources = load_sources(SOURCES_PATH)
    embedder = Embedder()
    client = get_client()

    for source_config in sources:
        standard = source_config["standard"]
        collection_name = COLLECTION_MAP[standard]

        fetched_list = fetch(source_config)
        all_records = []
        for fetched in fetched_list:
            records = parse(fetched)
            all_records.extend(records)

        chunks = chunk(all_records)
        embedded = embedder.embed(chunks)

        ensure_collection(client, collection_name, embedder.vector_size)
        upsert(client, collection_name, embedded)

        print(f"[{standard}] {len(embedded)} 件投入完了")


if __name__ == "__main__":
    main()
