from unittest.mock import MagicMock, call, patch
import pytest
from src.upserter import (
    EmbeddedChunk,
    PAYLOAD_INDEXES,
    UPSERT_BATCH_SIZE,
    ensure_collection,
    upsert,
)


def _make_chunk(req_id: str = "V1.1.1") -> EmbeddedChunk:
    return EmbeddedChunk(
        point_id=f"uuid-{req_id}",
        vector=[0.1] * 1024,
        payload={"req_id": req_id, "standard": "ASVS"},
    )


class TestEnsureCollection:
    def test_creates_new_collection(self) -> None:
        client = MagicMock()
        client.collection_exists.return_value = False

        ensure_collection(client, "asvs_requirements", 1024)

        client.create_collection.assert_called_once()
        call_kwargs = client.create_collection.call_args
        assert call_kwargs.kwargs["collection_name"] == "asvs_requirements"

    def test_creates_payload_indexes(self) -> None:
        client = MagicMock()
        client.collection_exists.return_value = False

        ensure_collection(client, "asvs_requirements", 1024)

        assert client.create_payload_index.call_count == len(PAYLOAD_INDEXES)
        indexed_fields = {
            c.args[1] for c in client.create_payload_index.call_args_list
        }
        assert indexed_fields == set(PAYLOAD_INDEXES.keys())

    def test_skips_existing_collection(self) -> None:
        client = MagicMock()
        client.collection_exists.return_value = True

        ensure_collection(client, "asvs_requirements", 1024)

        client.create_collection.assert_not_called()
        client.create_payload_index.assert_not_called()


class TestUpsert:
    def test_calls_qdrant_upsert(self) -> None:
        client = MagicMock()
        chunks = [_make_chunk()]

        upsert(client, "asvs_requirements", chunks)

        client.upsert.assert_called_once()
        call_kwargs = client.upsert.call_args
        assert call_kwargs.kwargs["collection_name"] == "asvs_requirements"

    def test_batching(self) -> None:
        client = MagicMock()
        total = UPSERT_BATCH_SIZE + 1
        chunks = [_make_chunk(f"V1.1.{i}") for i in range(total)]

        upsert(client, "asvs_requirements", chunks)

        assert client.upsert.call_count == 2

    def test_single_batch_when_within_limit(self) -> None:
        client = MagicMock()
        chunks = [_make_chunk(f"V1.1.{i}") for i in range(UPSERT_BATCH_SIZE)]

        upsert(client, "asvs_requirements", chunks)

        client.upsert.assert_called_once()

    def test_empty_chunks(self) -> None:
        client = MagicMock()
        upsert(client, "asvs_requirements", [])
        client.upsert.assert_not_called()
