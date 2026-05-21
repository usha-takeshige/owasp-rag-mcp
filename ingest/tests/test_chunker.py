import uuid
from src.parser import NormalizedRecord
from src.chunker import chunk, generate_point_id, NAMESPACE


def _make_record(**kwargs) -> NormalizedRecord:  # type: ignore[no-untyped-def]
    defaults = {
        "standard": "ASVS",
        "version": "5.0.0",
        "req_id": "V1.1.1",
        "chapter_id": "V1",
        "chapter_name": "Encoding",
        "section_id": "V1.1",
        "section_name": "Architecture",
        "description": "Verify that input is decoded only once.",
        "level": 2,
    }
    defaults.update(kwargs)
    return NormalizedRecord(**defaults)


class TestGeneratePointId:
    def test_returns_valid_uuid(self) -> None:
        pid = generate_point_id("ASVS", "V1.1.1")
        uuid.UUID(pid)  # raises if invalid

    def test_is_uuid_v5(self) -> None:
        pid = generate_point_id("ASVS", "V1.1.1")
        assert uuid.UUID(pid).version == 5

    def test_idempotent(self) -> None:
        pid1 = generate_point_id("ASVS", "V1.1.1")
        pid2 = generate_point_id("ASVS", "V1.1.1")
        assert pid1 == pid2

    def test_different_inputs_differ(self) -> None:
        pid1 = generate_point_id("ASVS", "V1.1.1")
        pid2 = generate_point_id("AISVS", "C1.1.1")
        assert pid1 != pid2

    def test_matches_expected_uuid5(self) -> None:
        expected = str(uuid.uuid5(NAMESPACE, "ASVS:V1.1.1"))
        assert generate_point_id("ASVS", "V1.1.1") == expected


class TestChunk:
    def test_embedding_text_format(self) -> None:
        record = _make_record()
        chunks = chunk([record])
        assert chunks[0].embedding_text == "passage: V1.1.1: Verify that input is decoded only once."

    def test_point_id_is_uuid5(self) -> None:
        record = _make_record()
        chunks = chunk([record])
        assert uuid.UUID(chunks[0].point_id).version == 5

    def test_payload_has_all_fields(self) -> None:
        record = _make_record()
        chunks = chunk([record])
        payload = chunks[0].payload
        for field in ["standard", "version", "req_id", "chapter_id", "chapter_name",
                       "section_id", "section_name", "description", "level"]:
            assert field in payload

    def test_chunk_count_matches_records(self) -> None:
        records = [_make_record(req_id=f"V1.1.{i}") for i in range(5)]
        chunks = chunk(records)
        assert len(chunks) == 5

    def test_idempotent_point_id(self) -> None:
        record = _make_record()
        chunks1 = chunk([record])
        chunks2 = chunk([record])
        assert chunks1[0].point_id == chunks2[0].point_id
