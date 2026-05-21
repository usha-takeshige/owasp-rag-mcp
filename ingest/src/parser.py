import json
import re
from dataclasses import dataclass

from src.fetcher import FetchedSource

CHAPTER_PATTERN = re.compile(r"^# (C\d+)\s+(.+)$", re.MULTILINE)
SECTION_PATTERN = re.compile(r"^## (C\d+\.\d+)\s+(.+)$", re.MULTILINE)
REQ_ROW_PATTERN = re.compile(
    r"^\|\s*\*\*(\d+\.\d+\.\d+)\*\*\s*\|\s*(.+?)\s*\|\s*(\d)\s*\|",
    re.MULTILINE,
)


@dataclass
class NormalizedRecord:
    standard: str
    version: str
    req_id: str
    chapter_id: str
    chapter_name: str
    section_id: str
    section_name: str
    description: str
    level: int


def _strip_md(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    return text.strip()


def parse_asvs(source: FetchedSource) -> list[NormalizedRecord]:
    data = json.loads(source.content)
    records = []
    for item in data["requirements"]:
        records.append(NormalizedRecord(
            standard="ASVS",
            version=source.version,
            req_id=item["req_id"],
            chapter_id=item["chapter_id"],
            chapter_name=item["chapter_name"],
            section_id=item["section_id"],
            section_name=item["section_name"],
            description=item["req_description"],
            level=int(item["L"]),
        ))
    return records


def parse_aisvs(source: FetchedSource) -> list[NormalizedRecord]:
    text = source.content
    chapters = {m.start(): (m.group(1), m.group(2).strip()) for m in CHAPTER_PATTERN.finditer(text)}
    sections = {m.start(): (m.group(1), m.group(2).strip()) for m in SECTION_PATTERN.finditer(text)}

    chapter_positions = sorted(chapters)
    section_positions = sorted(sections)

    records = []
    for req_match in REQ_ROW_PATTERN.finditer(text):
        pos = req_match.start()

        ch_pos = max((p for p in chapter_positions if p < pos), default=None)
        sec_pos = max((p for p in section_positions if p < pos), default=None)

        if ch_pos is None or sec_pos is None:
            continue

        chapter_id, chapter_name = chapters[ch_pos]
        section_id, section_name = sections[sec_pos]

        raw_num = req_match.group(1)
        req_id = f"C{raw_num}"
        description = _strip_md(req_match.group(2))
        level = int(req_match.group(3))

        records.append(NormalizedRecord(
            standard="AISVS",
            version=source.version,
            req_id=req_id,
            chapter_id=chapter_id,
            chapter_name=chapter_name,
            section_id=section_id,
            section_name=section_name,
            description=description,
            level=level,
        ))
    return records


def parse(source: FetchedSource) -> list[NormalizedRecord]:
    if source.format == "json_flat":
        return parse_asvs(source)
    elif source.format == "markdown":
        return parse_aisvs(source)
    raise ValueError(f"Unknown format: {source.format}")
