import os
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

QDRANT_HOST = os.environ.get("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
UPSERT_BATCH_SIZE = int(os.environ.get("UPSERT_BATCH_SIZE", "100"))

PAYLOAD_INDEXES: dict[str, PayloadSchemaType] = {
    "standard": PayloadSchemaType.KEYWORD,
    "req_id": PayloadSchemaType.KEYWORD,
    "chapter_id": PayloadSchemaType.KEYWORD,
    "section_id": PayloadSchemaType.KEYWORD,
    "level": PayloadSchemaType.INTEGER,
}

COLLECTION_MAP = {
    "ASVS": "asvs_requirements",
    "AISVS": "aisvs_requirements",
}


@dataclass
class EmbeddedChunk:
    point_id: str
    vector: list[float]
    payload: dict


def get_client() -> QdrantClient:
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def ensure_collection(client: QdrantClient, collection_name: str, vector_size: int) -> None:
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        for field, schema in PAYLOAD_INDEXES.items():
            client.create_payload_index(collection_name, field, schema)


def upsert(client: QdrantClient, collection_name: str, chunks: list[EmbeddedChunk]) -> None:
    for i in range(0, len(chunks), UPSERT_BATCH_SIZE):
        batch = chunks[i:i + UPSERT_BATCH_SIZE]
        points = [
            PointStruct(id=c.point_id, vector=c.vector, payload=c.payload)
            for c in batch
        ]
        client.upsert(collection_name=collection_name, points=points)
