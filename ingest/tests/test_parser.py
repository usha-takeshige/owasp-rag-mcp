import json
import pytest
from src.fetcher import FetchedSource
from src.parser import parse, parse_asvs, parse_aisvs


ASVS_JSON = json.dumps({
    "requirements": [
        {
            "chapter_id": "V1",
            "chapter_name": "Encoding and Sanitization",
            "section_id": "V1.1",
            "section_name": "Encoding and Sanitization Architecture",
            "req_id": "V1.1.1",
            "req_description": "Verify that input is decoded only once.",
            "L": "2",
        }
    ]
})

AISVS_MD = """\
# C1 Training Data Integrity & Traceability

## C1.1 Training Data Origin & Traceability

| # | Description | Level |
| :--------: | --- | :---: |
| **1.1.1** | **Verify that** an up-to-date inventory exists. | 1 |
| **1.1.2** | **Verify that** training data processes are documented. | 2 |
"""


def _make_source(fmt: str, content: str, standard: str = "TEST") -> FetchedSource:
    return FetchedSource(
        standard=standard,
        version="1.0",
        format=fmt,
        content=content,
        filename="test.json",
    )


class TestParseAsvs:
    def test_basic_fields(self) -> None:
        source = _make_source("json_flat", ASVS_JSON, "ASVS")
        records = parse_asvs(source)
        assert len(records) == 1
        r = records[0]
        assert r.standard == "ASVS"
        assert r.version == "1.0"
        assert r.req_id == "V1.1.1"
        assert r.chapter_id == "V1"
        assert r.chapter_name == "Encoding and Sanitization"
        assert r.section_id == "V1.1"
        assert r.section_name == "Encoding and Sanitization Architecture"
        assert r.description == "Verify that input is decoded only once."

    def test_level_is_int(self) -> None:
        source = _make_source("json_flat", ASVS_JSON, "ASVS")
        records = parse_asvs(source)
        assert records[0].level == 2
        assert isinstance(records[0].level, int)

    def test_via_dispatch(self) -> None:
        source = _make_source("json_flat", ASVS_JSON, "ASVS")
        records = parse(source)
        assert len(records) == 1


class TestParseAisvs:
    def test_basic_fields(self) -> None:
        source = _make_source("markdown", AISVS_MD, "AISVS")
        records = parse_aisvs(source)
        assert len(records) == 2
        r = records[0]
        assert r.standard == "AISVS"
        assert r.chapter_id == "C1"
        assert r.chapter_name == "Training Data Integrity & Traceability"
        assert r.section_id == "C1.1"
        assert r.section_name == "Training Data Origin & Traceability"

    def test_req_id_prefix(self) -> None:
        source = _make_source("markdown", AISVS_MD, "AISVS")
        records = parse_aisvs(source)
        assert records[0].req_id == "C1.1.1"
        assert records[1].req_id == "C1.1.2"

    def test_level_is_int(self) -> None:
        source = _make_source("markdown", AISVS_MD, "AISVS")
        records = parse_aisvs(source)
        assert records[0].level == 1
        assert records[1].level == 2

    def test_md_stripped_from_description(self) -> None:
        source = _make_source("markdown", AISVS_MD, "AISVS")
        records = parse_aisvs(source)
        assert "**" not in records[0].description

    def test_via_dispatch(self) -> None:
        source = _make_source("markdown", AISVS_MD, "AISVS")
        records = parse(source)
        assert len(records) == 2


def test_unknown_format_raises() -> None:
    source = _make_source("xml", "<data/>")
    with pytest.raises(ValueError, match="Unknown format"):
        parse(source)
