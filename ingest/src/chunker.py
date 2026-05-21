import uuid
from dataclasses import dataclass

from src.parser import NormalizedRecord

NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


@dataclass
class Chunk:
    point_id: str
    embedding_text: str
    payload: dict


def generate_point_id(standard: str, req_id: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{standard}:{req_id}"))


def chunk(records: list[NormalizedRecord]) -> list[Chunk]:
    chunks = []
    for record in records:
        chunks.append(Chunk(
            point_id=generate_point_id(record.standard, record.req_id),
            embedding_text=f"passage: {record.req_id}: {record.description}",
            payload={
                "standard": record.standard,
                "version": record.version,
                "req_id": record.req_id,
                "chapter_id": record.chapter_id,
                "chapter_name": record.chapter_name,
                "section_id": record.section_id,
                "section_name": record.section_name,
                "description": record.description,
                "level": record.level,
            },
        ))
    return chunks
