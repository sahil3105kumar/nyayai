"""
chunks a Section by legal structure, not token count: the main operative
text becomes one Passage, and each Explanation/Illustration/Exception
becomes its own Passage. this keeps every chunk semantically whole (an
Explanation is a complete thought) instead of an arbitrary word-count
window that might cut a sentence in half.
"""

import re

from corpus.schemas import Section, Passage

# matches "Explanation.—", "Explanation 1.—", "Illustration (a).—" style
# markers that start a new structural part within a section body
STRUCTURAL_MARKER = re.compile(
    r'\n\s*(Explanation|Illustration|Exception)\s*(\d*)\s*\.\s*[-—–]\s*',
    re.IGNORECASE,
)


def chunk_section(section: Section) -> list[Passage]:
    matches = list(STRUCTURAL_MARKER.finditer(section.body))

    if not matches:
        return [_make_passage(section, section.body, "body")]

    passages = []

    # everything before the first marker is the main operative text
    main_text = section.body[:matches[0].start()].strip()
    if main_text:
        passages.append(_make_passage(section, main_text, "body"))

    for i, match in enumerate(matches):
        label = match.group(1).lower()
        number = match.group(2)
        part = f"{label}_{number}" if number else label

        text_start = match.end()
        text_end = matches[i + 1].start() if i + 1 < len(matches) else len(section.body)
        text = section.body[text_start:text_end].strip()

        if text:
            passages.append(_make_passage(section, text, part))

    return passages


def _make_passage(section: Section, text: str, part: str) -> Passage:
    metadata = dict(section.metadata)
    metadata["part"] = part

    return Passage(
        act=section.act,
        unit_type=section.unit_type,
        number=section.number,
        title=section.title,
        status=section.status,
        text=text,
        metadata=metadata,
    )


def chunk_sections(sections: list[Section]) -> list[Passage]:
    passages = []
    for section in sections:
        passages.extend(chunk_section(section))
    return passages