"""
the Constitution's grammar is Part -> Chapter -> Article, not Chapter ->
Section like the other acts - kept fully separate from ChapterSectionParser
rather than forcing it into that shape.
"""

import re
from pathlib import Path

from corpus.parsers.base import BaseParser
from corpus.schemas import Section

PART_START = re.compile(r'(?:^|\n)\s*PART\s+([IVXLC]+)\s*\n\s*([^\n]*)', re.MULTILINE)
CHAPTER_START = re.compile(r'(?:^|\n)\s*CHAPTER\s+([IVXLC\d]+)\s*\n\s*([^\n]*)', re.MULTILINE)
ARTICLE_START = re.compile(
    r'(?:^|\n)\s*(\d{1,3}[A-Z]{0,2})\.\s+([A-Z][^.\n]*?)\.\s*[-—–]\s*',
    re.MULTILINE,
)


class ConstitutionParser(BaseParser):
    act = "Constitution"

    def parse(self, pdf_path: Path) -> list[Section]:
        raw_text = self.extract_raw_text(pdf_path)
        return self._split_into_articles(raw_text)

    def _split_into_articles(self, raw_text: str) -> list[Section]:
        parts = list(PART_START.finditer(raw_text))
        chapters = list(CHAPTER_START.finditer(raw_text))
        matches = list(ARTICLE_START.finditer(raw_text))
        sections = []

        for i, match in enumerate(matches):
            number = match.group(1)
            title = match.group(2).strip()

            body_start = match.end()
            body_end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
            body = raw_text[body_start:body_end].strip()

            if not body:
                continue

            sections.append(Section(
                act=self.act,
                unit_type="article",
                number=number,
                title=title,
                body=body,
                status="active",
                metadata={
                    "part": self._label_for_position(parts, match.start(), "Part"),
                    "chapter": self._label_for_position(chapters, match.start(), "Chapter"),
                    "effective_date": "1950-01-26",
                },
            ))

        return sections

    @staticmethod
    def _label_for_position(headers, position: int, label: str) -> str:
        current = ""
        for header_match in headers:
            if header_match.start() > position:
                break
            number, title = header_match.group(1), header_match.group(2).strip()
            current = f"{label} {number}: {title}" if title else f"{label} {number}"
        return current